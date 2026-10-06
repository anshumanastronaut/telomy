import { router, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, statusColor, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ConfBar, Divider, ErrorState, Loading, Row, Screen, Section, StatusChip, T } from '@/ui/core';
import { confLabel } from '@/ui/insight';

export default function InsightDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: i, error, reload, setData } = useApi<any>(`/insights/${id}`, [id]);
  const [note, setNote] = useState('');
  const [err, setErr] = useState<string | null>(null);
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!i) return <Screen edges={[]}><Loading what="Loading…" /></Screen>;
  const r = i.receipts ?? {};

  async function act(action: string, author?: string) {
    setErr(null);
    try {
      setData(await api(`/insights/${id}/review`, { body: { action, note, ...(author ? { author } : {}) } }));
      setNote('');
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Screen edges={[]}>
      <Row style={{ flexWrap: 'wrap' }}>
        {i.medical ? <StatusChip status={i.review_state} /> : null}
        <Chip label={`${confLabel(i.confidence)} · ${Math.round(i.confidence * 100)}%`} fg={p.teal} bg={p.tealSoft} />
      </Row>
      <T v="h1">{i.title}</T>
      <T v="body">{i.body}</T>
      <Row>
        <ConfBar value={i.confidence} width={120} />
        <T v="small" style={{ flex: 1 }}>Confidence grows with evidence; it never claims cause.</T>
      </Row>

      <Section title="Receipts">
        <Card>
          {Object.entries(r)
            .filter(([k, v]) => v != null && v !== '' && !['direction'].includes(k))
            .map(([k, v]) => (
              <Row key={k} style={{ alignItems: 'flex-start' }}>
                <T v="small" style={{ width: 110 }}>{k.replace(/_/g, ' ')}</T>
                <T v="body" style={{ flex: 1, fontSize: 14 }}>{Array.isArray(v) ? v.join(', ') : String(v)}</T>
              </Row>
            ))}
        </Card>
      </Section>

      {i.evidence?.length ? (
        <Section title="Evidence">
          <Card style={{ paddingVertical: 4 }}>
            {i.evidence.map((e: any, k: number) => (
              <Pressable
                key={k}
                onPress={() => (e.type === 'marker' ? router.push(`/marker/${e.marker_id ?? e.id}`) : e.metric ? router.push(`/signal/${e.metric}`) : undefined)}
                style={{ paddingVertical: 10, borderTopWidth: k ? 1 : 0, borderTopColor: p.border }}>
                <Row>
                  <T v="body" style={{ flex: 1 }}>{e.name ?? e.metric ?? e.marker_id}</T>
                  {e.value != null ? (
                    <T v="num" style={{ fontSize: 15 }} color={statusColor(p, e.status).fg}>{String(e.value)} <T v="small">{e.unit}</T></T>
                  ) : e.values ? (
                    <T v="small">{e.values.join(' → ')}</T>
                  ) : e.means ? (
                    <T v="small">{e.means.join(' → ')}</T>
                  ) : null}
                </Row>
                {e.day ? <T v="small">{fmtDate(e.day, true)}</T> : null}
              </Pressable>
            ))}
          </Card>
        </Section>
      ) : null}

      {i.medical || i.thread?.length ? (
        <Section title="Clinician sign-off">
          <Card>
            {(i.thread ?? []).map((t: any, k: number) => (
              <View key={t.id ?? k} style={{ gap: 2 }}>
                {k ? <Divider /> : null}
                <Row>
                  <T v="body" style={{ fontWeight: '600', flex: 1 }}>{t.author}</T>
                  <T v="small">{t.action} · {fmtDate(t.ts)}</T>
                </Row>
                {t.note ? <T v="small">{t.note}</T> : null}
              </View>
            ))}
            {i.review_state !== 'awaiting' && i.review_state !== 'signed' ? (
              <Button title="Ask my clinician to review" icon="stethoscope" onPress={() => act('request')} />
            ) : null}
          </Card>
          {i.review_state === 'awaiting' ? (
            <Card tone="copper">
              <T v="label">Telomy Care · clinician view (demo)</T>
              <TextInput
                value={note}
                onChangeText={setNote}
                placeholder="Note (required to reject)"
                placeholderTextColor={p.faint}
                style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10, color: p.text, fontFamily: 'Inter_400Regular', backgroundColor: p.surface }}
              />
              {err ? <T v="small" color={p.danger}>{err}</T> : null}
              <Row>
                <Button style={{ flex: 1 }} title="Sign off" onPress={() => act('signed')} />
                <Button style={{ flex: 1 }} kind="secondary" title="Modify" onPress={() => act('modified')} />
                <Button style={{ flex: 1 }} kind="danger" title="Reject" onPress={() => act('rejected')} />
              </Row>
            </Card>
          ) : null}
        </Section>
      ) : null}
      <Button
        kind="ghost"
        title="Not useful — hide this"
        onPress={async () => {
          await api(`/insights/${id}/dismiss`, { method: 'POST' });
          router.back();
        }}
      />
    </Screen>
  );
}
