import { router } from 'expo-router';
import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Empty, Loading, Row, Screen, Section, Segmented, T, useToast } from '@/ui/core';
import { InsightCard } from '@/ui/insight';

export default function Work() {
  const p = usePalette();
  const [tab, setTab] = useState<'reports' | 'drafts' | 'consults'>('reports');
  const w = useApi<any>('/doctor/work');
  const q = useApi<any[]>('/care/queue');
  const [note, setNote] = useState<Record<string, string>>({});
  const { toast, show } = useToast();
  return (
    <View style={{ flex: 1 }}>
      <Screen onRefresh={() => { w.reload(); q.reload(); }} refreshing={w.loading}>
        <T v="h1">Work queue</T>
        <Segmented options={[
          { key: 'reports', label: `Reports · ${w.data?.monthly_reports.length ?? 0}` },
          { key: 'drafts', label: `Drafts · ${q.data?.length ?? 0}` },
          { key: 'consults', label: `Consults · ${w.data?.consults.length ?? 0}` }]} value={tab} onChange={setTab} />
        {!w.data ? <Loading what="Loading…" /> : null}
        {tab === 'reports' && (w.data?.monthly_reports.length ? w.data.monthly_reports.map((r: any) => (
          <Card key={r.period}>
            <Row><T v="h3" style={{ flex: 1 }}>Monthly report · {r.period}</T><Chip label="Awaiting signature" fg={p.warn} bg={p.warnSoft} /></Row>
            <T v="small">Aarav (Test User) · auto-generated {fmtDate(r.created_at)}</T>
            <Button kind="secondary" title="Open report" onPress={() => router.push(`/monthly?period=${r.period}&doctor=1`)} />
          </Card>
        )) : <Empty title="All reports signed" body="New monthly reports arrive on the 1st of each month." />)}
        {tab === 'drafts' && (q.data?.length ? q.data.map((i) => <InsightCard key={i.id} i={i} />) : <Empty title="No drafts waiting" body="Sinc's medical drafts appear here." />)}
        {tab === 'consults' && (w.data?.consults.length ? w.data.consults.map((c: any) => (
          <Card key={c.id}>
            <Row><T v="h3" style={{ flex: 1 }}>{c.kind === 'gp' ? 'GP' : c.kind} · {c.mode}</T><Chip label={c.covered ? 'Covered by plan' : `₹${c.price}`} /></Row>
            <T v="small">{c.scheduled_at.replace('T', ' ')} · {c.reason || 'No reason given'}</T>
            <Button kind="ghost" title="Open pre-clinic brief" onPress={() => router.push('/brief')} />
            <TextInput value={note[c.id] ?? ''} onChangeText={(v) => setNote({ ...note, [c.id]: v })} placeholder="Consult notes (required)" placeholderTextColor={p.faint} multiline
              style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10, minHeight: 60, color: p.text, fontFamily: 'Inter_400Regular' }} />
            <Button title="Complete consult" disabled={!note[c.id]?.trim()} onPress={async () => { await api(`/consults/${c.id}/complete`, { body: { notes: note[c.id] } }); show('Completed. Notes shared with the patient.', 'success'); w.reload(); }} />
          </Card>
        )) : <Empty title="No consults scheduled" body="On-demand consults booked by patients appear here." />)}
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
