import { router, useLocalSearchParams } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, Icon, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function Monthly() {
  const p = usePalette();
  const params = useLocalSearchParams<{ period?: string; doctor?: string }>();
  const list = useApi<any[]>('/monthly-reports');
  const [period, setPeriod] = useState<string | undefined>(params.period);
  useEffect(() => {
    if (params.period) setPeriod(params.period);
  }, [params.period]);
  const rep = useApi<any>(period ? `/monthly-reports/${period}` : null, [period]);
  const [note, setNote] = useState('');
  const { toast, show } = useToast();
  const doctor = params.doctor === '1';
  if (!period) {
    return (
      <View style={{ flex: 1 }}>
        <Screen edges={[]}>
          <T v="body" color={p.muted}>A report is generated automatically on the 1st of each month. On Plus and Pro, your doctor reviews and signs it within 72 hours.</T>
          {!list.data ? <Loading what="Loading…" /> : null}
          <Card style={{ paddingVertical: 2 }}>
            {list.data?.map((r, i) => (
              <View key={r.period}>{i ? <Divider /> : null}
                <Pressable onPress={() => setPeriod(r.period)} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 12 }}>
                  <Icon name="doc.text" color={p.teal} />
                  <View style={{ flex: 1 }}><T v="body" style={{ fontWeight: '600' }}>{new Date(r.period + '-01T12:00:00').toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}</T>
                    <T v="small">{r.state === 'signed' ? `Signed by ${r.doctor}` : r.state === 'awaiting_doctor' ? 'With your doctor for review' : 'AI report'}</T></View>
                  <Chip label={r.state === 'signed' ? 'Signed' : r.state === 'awaiting_doctor' ? 'In review' : 'Ready'} fg={r.state === 'signed' ? p.success : p.warn} bg={r.state === 'signed' ? p.successSoft : p.warnSoft} />
                </Pressable>
              </View>
            ))}
          </Card>
          <Button kind="secondary" title="Generate this month's report now" onPress={async () => {
            try { const r = await api('/monthly-reports/2026-10/generate', { method: 'POST' }); setPeriod(r.period); list.reload(); } catch (e: any) { show(e.message, 'alert'); }
          }} />
        </Screen>
        {toast}
      </View>
    );
  }
  const r = rep.data;
  if (!r) return <Screen edges={[]}><Loading what="Opening report…" /></Screen>;
  const d = r.data;
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <T v="h1">{new Date(r.period + '-01T12:00:00').toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}</T>
        <Chip label={r.state === 'signed' ? `Signed by ${r.doctor} · ${fmtDate(r.signed_at, true)}` : r.state === 'awaiting_doctor' ? 'Awaiting doctor review' : 'AI-generated'} fg={r.state === 'signed' ? p.success : p.warn} bg={r.state === 'signed' ? p.successSoft : p.warnSoft} />
        {r.doctor_note ? <Card tone="teal"><T v="label">Note from {r.doctor}</T><T v="body">{r.doctor_note}</T></Card> : null}
        <Card><T v="body">{d.summary}</T></Card>
        <Section title="This month vs last">
          <Card style={{ paddingVertical: 4 }}>
            {d.signals.map((s: any, i: number) => (
              <Row key={s.id} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <T v="body" style={{ flex: 1 }}>{s.label}</T>
                <T v="small">{s.last_month ?? '—'} → </T>
                <T v="body" style={{ fontWeight: '600', width: 64, textAlign: 'right' }} color={s.verdict === 'better' ? p.success : s.verdict === 'worse' ? p.danger : p.text}>{s.this_month} <T v="small">{s.unit}</T></T>
              </Row>
            ))}
          </Card>
        </Section>
        <Section title="Predicted risk">
          <Card>
            {d.predictions.prevent?.ten_year === undefined ? null : null}
            {Object.entries(d.predictions).map(([k, v]: any) => (
              <Row key={k}><T v="body" style={{ flex: 1 }}>{v.model}</T><T v="small">{v.risk != null ? `${v.risk}%` : v.score ?? v.band ?? '—'}</T></Row>
            ))}
          </Card>
        </Section>
        <Section title="Priorities and actions">
          <Card>
            {d.actions.map((a: string) => <Row key={a} style={{ alignItems: 'flex-start' }}><Icon name="arrow.right" size={12} color={p.teal} /><T v="body" style={{ flex: 1 }}>{a}</T></Row>)}
            <T v="small">Protocol adherence {d.protocol_adherence}% · {d.new_reports.length} new report(s) · medications: {d.medications.map((m: any) => `${m.name} ${m.adherence}%`).join(', ')}</T>
          </Card>
        </Section>
        {doctor && r.state === 'awaiting_doctor' ? (
          <Card tone="copper">
            <T v="label">Sign as Dr. Meera Rao</T>
            <TextInput value={note} onChangeText={setNote} placeholder="Note for the patient (required)" placeholderTextColor={p.faint} multiline
              style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10, minHeight: 70, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular' }} />
            <Button title="Sign and send" disabled={!note.trim()} onPress={async () => { await api(`/monthly-reports/${r.period}/sign`, { body: { note } }); show('Signed and sent to the patient.', 'success'); rep.reload(); }} />
          </Card>
        ) : null}
        <Button kind="ghost" title="All monthly reports" onPress={() => (doctor ? router.back() : setPeriod(undefined))} />
      </Screen>
      {toast}
    </View>
  );
}
