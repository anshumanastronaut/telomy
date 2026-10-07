import { router, Stack, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, ErrorState, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';
import { InsightCard } from '@/ui/insight';
import { PredictionCards } from '@/ui/predictions';

export default function Patient() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: d, error, reload } = useApi<any>(`/doctor/patients/${id}`, [id]);
  const sum = useApi<any>(`/doctor/patients/${id}/summary`, [id]);
  const reps = useApi<any[]>(`/doctor/patients/${id}/reports`, [id]);
  const ther = useApi<any[]>(`/therapy/working?patient_id=${id}`, [id]);
  const [note, setNote] = useState('');
  const { toast, show } = useToast();
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen edges={[]}><Loading what="Opening patient…" /></Screen>;
  const x = d.inputs;
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: d.name }} />
        <Card>
          <T v="h2">{d.name}</T>
          <T v="small">{d.age} y · {d.sex} · {d.city} · {d.plan}{d.member ? ' · centre member' : ''}</T>
          {d.conditions?.length ? <Row style={{ flexWrap: 'wrap' }}>{d.conditions.map((c: string) => <Chip key={c} label={c} />)}</Row> : null}
          <Row style={{ flexWrap: 'wrap' }}>{d.flags.map((f: string) => <Chip key={f} label={f} fg={p.danger} bg={p.dangerSoft} />)}</Row>
        </Card>
        {sum.data ? (
          <Card tone="teal" testID="ai-summary">
            <Row><T v="label" style={{ flex: 1 }}>AI summary · Sinc draft</T><Chip label="Review" fg={p.teal} bg={p.surface} /></Row>
            <T v="body">{sum.data.summary}</T>
            {sum.data.problems?.length ? <Row style={{ flexWrap: 'wrap' }}>{sum.data.problems.map((x: string) => <Chip key={x} label={x} fg={p.danger} bg={p.dangerSoft} />)}</Row> : null}
            {sum.data.open_items && Object.keys(sum.data.open_items).length ? (
              <T v="small">Open: {sum.data.open_items.insights} drafts · {sum.data.open_items.unreviewed_reports} unreviewed reports · {sum.data.open_items.therapy_plans} therapy plans</T>
            ) : null}
            <T v="small" color={p.muted}>{sum.data.disclaimer}</T>
          </Card>
        ) : null}
        {reps.data?.length ? (
          <Section title={`All reports · ${reps.data.length}`}>
            {reps.data.map((r: any) => (
              <Card key={r.id} onPress={() => router.push(`/review/${r.id}`)}>
                <Row>
                  <T v="h3" style={{ flex: 1 }}>{r.panel_title}</T>
                  {r.reviewed ? <Chip label="Signed" fg={p.success} bg={p.successSoft} /> : r.flagged ? <Chip label={`${r.flagged} flagged`} fg={p.danger} bg={p.dangerSoft} /> : <Chip label="Normal" fg={p.success} bg={p.successSoft} />}
                </Row>
                <T v="small">{fmtDate(r.collected_on, true)} · {r.markers} results{r.is_test_data ? ' · test data' : ''}</T>
                <T v="small" numberOfLines={3}>{r.summary}</T>
              </Card>
            ))}
          </Section>
        ) : null}
        {ther.data?.length ? (
          <Section title="Centre therapies · what's working">
            <Card style={{ paddingVertical: 4 }}>
              {ther.data.map((w: any, i: number) => (
                <Row key={w.modality} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                  <View style={{ flex: 1 }}><T v="body">{w.name}</T><T v="small">{w.sessions} sessions</T></View>
                  <T v="small" color={w.verdict === 'helped' ? p.success : w.verdict === 'promising' ? p.teal : w.verdict === 'possible_negative' ? p.danger : p.muted}>{w.verdict.replace('_', ' ')}</T>
                </Row>
              ))}
            </Card>
          </Section>
        ) : null}
        <Section title="Key values">
          <Card>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', rowGap: 10 }}>
              {[['Total chol.', x.tc, 'mg/dL'], ['HDL', x.hdl, 'mg/dL'], ['ApoB', x.apob, 'mg/dL'], ['SBP', x.sbp != null ? Math.round(x.sbp) : null, 'mmHg'],
                ['HbA1c', x.hba1c, '%'], ['BMI', x.bmi, ''], ['eGFR', x.egfr, ''], ['hs-CRP', x.hscrp, 'mg/L']].map(([l, v, u]) => (
                <View key={l as string} style={{ width: '25%' }}>
                  <T v="small">{l}</T>
                  <T v="body" style={{ fontWeight: '600' }}>{v ?? '—'} <T v="small">{u}</T></T>
                </View>
              ))}
            </View>
            <T v="small">Smoker: {x.smoker ? 'yes' : 'no'} · BP treated: {x.bp_treated ? 'yes' : 'no'} · last report {fmtDate(d.last_report, true)}</T>
          </Card>
        </Section>
        <PredictionCards models={d.predictions.models} />
        {d.full_vault ? (
          <>
            <Section title="Clinician notes · top priorities">
              {d.top.map((t: any) => (
                <Card key={t.id} onPress={() => router.push(`/marker/${t.id}`)}>
                  <Row><T v="h3" style={{ flex: 1 }}>{t.name}</T><T v="num" style={{ fontSize: 16 }} color={p.danger}>{t.value} <T v="small">{t.unit}</T></T></Row>
                  {t.why ? <T v="small">{t.why}</T> : null}
                </Card>
              ))}
            </Section>
            <Section title={`Sinc drafts awaiting you · ${d.awaiting.length}`}>
              {d.awaiting.slice(0, 4).map((i: any) => <InsightCard key={i.id} i={i} compact />)}
            </Section>
            <Button kind="secondary" title="Open full Vault (risk map)" onPress={() => router.push('/risks')} />
          </>
        ) : null}
        <Section title="Clinical notes">
          <Card style={{ paddingVertical: 4 }}>
            {d.notes.length ? d.notes.map((n: any, i: number) => (
              <View key={n.id}>{i ? <Divider /> : null}<View style={{ paddingVertical: 8 }}><T v="small">{n.author} · {fmtDate(n.ts, true)}</T><T v="body">{n.text}</T></View></View>
            )) : <T v="small" style={{ paddingVertical: 8 }}>No notes yet.</T>}
          </Card>
          <TextInput value={note} onChangeText={setNote} placeholder="Add a clinical note" placeholderTextColor={p.faint} multiline testID="note-input"
            style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, minHeight: 70, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular' }} />
          <Button title="Save note" disabled={!note.trim()} onPress={async () => { await api(`/doctor/patients/${id}/notes`, { body: { text: note } }); setNote(''); show('Note saved.', 'success'); reload(); }} />
        </Section>
        {d.bookings?.length ? (
          <Section title="Recent centre visits">
            <Card style={{ paddingVertical: 4 }}>
              {d.bookings.map((b: any, i: number) => (
                <Row key={b.id} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                  <T v="body" style={{ flex: 1 }}>{b.service}</T><T v="small">{fmtDate(b.ts)} · {b.status.replace('_', ' ')}</T>
                </Row>
              ))}
            </Card>
          </Section>
        ) : null}
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
