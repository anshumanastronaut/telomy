import { router, Stack, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, statusColor, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ErrorState, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function Review() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: s, error, reload } = useApi<any>(`/reports/${id}/summary`, [id]);
  const [note, setNote] = useState('');
  const { toast, show } = useToast();
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!s) return <Screen edges={[]}><Loading what="Summarising report…" /></Screen>;

  async function act(action: string) {
    await api(`/reports/${id}/review`, { body: { action, note } });
    setNote('');
    show(action === 'signed' ? 'Signed. The patient sees your note on this report.' : 'Saved.', 'success');
    reload();
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: s.panel_title }} />
        <T v="h1">{s.report.title}</T>
        <T v="small">{fmtDate(s.report.collected_on, true)} · {s.report.source}{s.report.is_test_data ? ' · TEST DATA' : ''}</T>
        <Card tone="teal">
          <Row><T v="label" style={{ flex: 1 }}>AI summary · Sinc draft</T><Chip label={s.headline} fg={s.flagged ? p.danger : p.success} bg={p.surface} /></Row>
          <T v="body">{s.summary}</T>
          {s.actions.length ? <T v="small">Suggested next steps: {s.actions.join('; ')}.</T> : null}
          {s.retest_on ? <T v="small">Suggested re-test: {fmtDate(s.retest_on, true)}</T> : null}
          <T v="small" color={p.muted}>{s.drafted_by}. {s.disclaimer}</T>
        </Card>
        <Section title={`Results · ${s.results.length}`}>
          <Card style={{ paddingVertical: 4 }}>
            {s.results.map((r: any, i: number) => {
              const c = statusColor(p, r.status);
              return (
                <View key={r.marker_id} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border, gap: 2 }}>
                  <Row>
                    <T v="body" style={{ flex: 1 }} onPress={() => router.push(`/marker/${r.marker_id}`)}>{r.name}</T>
                    <T v="num" style={{ fontSize: 15 }} color={c.fg}>{String(r.value)} <T v="small">{r.unit}</T></T>
                  </Row>
                  <T v="small">
                    {r.zone ?? r.status.replace('_', ' ')}{r.ref ? ` · lab ${r.ref}` : ''}
                    {r.previous ? ` · was ${r.previous.value} (${fmtDate(r.previous.day, true)})` : ''}{r.evidence ? ` · evidence ${r.evidence}` : ''}
                  </T>
                </View>
              );
            })}
          </Card>
        </Section>
        {s.patterns.length ? (
          <Section title="Connected across the Vault">
            {s.patterns.map((x: any) => <Card key={x.id} onPress={() => router.push(`/insight/${x.id}`)}><T v="body">{x.title}</T><T v="small">confidence {Math.round(x.confidence * 100)}%</T></Card>)}
          </Section>
        ) : null}
        <Section title="Your review">
          {s.reviews.map((r: any) => <T key={r.id} v="small">{r.doctor} · {r.action.replace('_', ' ')} · {fmtDate(r.ts, true)}: {r.note}</T>)}
          <TextInput value={note} onChangeText={setNote} placeholder="Note for the patient (required)" placeholderTextColor={p.faint} multiline
            style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, minHeight: 70, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular' }} />
          <Row>
            <Button kind="secondary" title="Needs follow-up" style={{ flex: 1 }} disabled={!note.trim()} onPress={() => act('needs_followup')} />
            <Button title="Sign" style={{ flex: 1 }} disabled={!note.trim()} onPress={() => act('signed')} testID="sign-report" />
          </Row>
        </Section>
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
