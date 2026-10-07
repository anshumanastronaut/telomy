import { router } from 'expo-router';
import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Empty, Loading, Row, Screen, Section, Segmented, T, useToast } from '@/ui/core';
import { InsightCard } from '@/ui/insight';

export default function Work() {
  const p = usePalette();
  const [tab, setTab] = useState<'reports' | 'drafts' | 'consults' | 'therapy' | 'rx'>('reports');
  const [keep, setKeep] = useState<Record<string, boolean>>({});
  const [dose, setDose] = useState<Record<string, string>>({});
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
        <Segmented options={[
          { key: 'therapy', label: `Therapy plans · ${w.data?.therapy_plans?.length ?? 0}` },
          { key: 'rx', label: `Rx & supplements · ${w.data?.rx_plans?.length ?? 0}` }]} value={tab as any} onChange={setTab as any} />
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
        {tab === 'therapy' && (w.data?.therapy_plans?.length ? w.data.therapy_plans.map((pl: any) => (
          <Card key={pl.id}>
            <Row><T v="h3" style={{ flex: 1 }}>{pl.patient} · {pl.plan.goal_label}</T><Chip label="Awaiting signature" fg={p.warn} bg={p.warnSoft} /></Row>
            {pl.plan.items.map((i: any) => (
              <View key={i.modality} style={{ gap: 2 }}>
                <T v="body">• {i.name} — {i.per_week}×/week, {i.hour}:00</T>
                <T v="small">{i.reason}</T>
                {i.safety.status !== 'ok' ? <T v="small" color={p.warn}>{i.safety.summary}</T> : null}
              </View>
            ))}
            <T v="small">₹{pl.plan.monthly_price.toLocaleString('en-IN')} / month · {pl.plan.formula_pairing ?? ''}</T>
            <Button kind="ghost" title="Open patient" onPress={() => router.push(`/patient/${pl.patient_id}`)} />
            <TextInput value={note[`t${pl.id}`] ?? ''} onChangeText={(v) => setNote({ ...note, [`t${pl.id}`]: v })} placeholder="Note to patient (required)" placeholderTextColor={p.faint} multiline
              style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10, minHeight: 60, color: p.text, fontFamily: 'Inter_400Regular' }} />
            <Row>
              <Button kind="danger" title="Decline" style={{ flex: 1 }} disabled={!note[`t${pl.id}`]?.trim()} onPress={async () => { await api(`/therapy/plans/${pl.id}/decide`, { body: { approve: false, note: note[`t${pl.id}`] } }); show('Declined; the patient sees your note.', 'success'); w.reload(); }} />
              <Button title="Sign & book" style={{ flex: 1 }} disabled={!note[`t${pl.id}`]?.trim()} testID={`sign-plan-${pl.id}`} onPress={async () => { const r = await api(`/therapy/plans/${pl.id}/decide`, { body: { approve: true, note: note[`t${pl.id}`] } }); show(`Signed — ${r.booked} sessions booked over 4 weeks.`, 'success'); w.reload(); }} />
            </Row>
          </Card>
        )) : <Empty title="No therapy plans waiting" body="Plans patients build in the Therapy tab arrive here." />)}
        {tab === 'rx' && (w.data?.rx_plans?.length ? w.data.rx_plans.map((pl: any) => (
          <Card key={pl.id}>
            <Row><T v="h3" style={{ flex: 1 }}>{pl.patient} · {pl.plan.goal_label}</T><Chip label="Awaiting signature" fg={p.warn} bg={p.warnSoft} /></Row>
            {pl.plan.items.map((i: any) => {
              const k = `${pl.id}:${i.id}`;
              const on = keep[k] ?? true;
              return (
                <View key={i.id} style={{ gap: 4, paddingVertical: 6, borderTopWidth: 1, borderTopColor: p.border, opacity: on ? 1 : 0.45 }}>
                  <Row>
                    <T v="body" style={{ flex: 1, fontWeight: '600' }}>{i.name}</T>
                    {i.rx ? <Chip label="Rx" fg={p.copper} bg={p.copperSoft} /> : null}
                    <Button kind="ghost" title={on ? 'Remove' : 'Keep'} onPress={() => setKeep({ ...keep, [k]: !on })} />
                  </Row>
                  <T v="small">{i.why}</T>
                  {i.interactions.map((x: any) => <T key={x.with} v="small" color={x.severity === 'major' ? p.danger : p.warn}>⚠︎ {x.with}: {x.note}</T>)}
                  <TextInput value={dose[k] ?? i.dose} onChangeText={(v) => setDose({ ...dose, [k]: v })} accessibilityLabel={`Dose for ${i.name}`}
                    style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.sm, paddingHorizontal: 8, paddingVertical: 6, color: p.text, fontFamily: 'Inter_400Regular' }} />
                </View>
              );
            })}
            <TextInput value={note[`r${pl.id}`] ?? ''} onChangeText={(v) => setNote({ ...note, [`r${pl.id}`]: v })} placeholder="Clinical note (required to sign)" placeholderTextColor={p.faint} multiline
              style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10, minHeight: 60, color: p.text, fontFamily: 'Inter_400Regular' }} />
            <Row>
              <Button kind="danger" title="Reject" style={{ flex: 1 }} disabled={!note[`r${pl.id}`]?.trim()} onPress={async () => { await api(`/rx/plans/${pl.id}/decide`, { body: { approve: false, note: note[`r${pl.id}`] } }); show('Rejected.', 'success'); w.reload(); }} />
              <Button title="Sign e-prescription" style={{ flex: 1 }} disabled={!note[`r${pl.id}`]?.trim()} testID={`sign-rx-${pl.id}`} onPress={async () => {
                const kept = pl.plan.items.filter((i: any) => keep[`${pl.id}:${i.id}`] ?? true).map((i: any) => i.id);
                const doses = Object.fromEntries(pl.plan.items.filter((i: any) => dose[`${pl.id}:${i.id}`] && dose[`${pl.id}:${i.id}`] !== i.dose).map((i: any) => [i.id, dose[`${pl.id}:${i.id}`]]));
                try { await api(`/rx/plans/${pl.id}/decide`, { body: { approve: true, note: note[`r${pl.id}`], keep: kept, doses } }); show('Signed. The patient can order now.', 'success'); w.reload(); } catch (e: any) { show(e.message, 'alert'); }
              }} />
            </Row>
          </Card>
        )) : <Empty title="No Rx plans waiting" body="Supplement, medicine and IV plans patients send arrive here." />)}
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
