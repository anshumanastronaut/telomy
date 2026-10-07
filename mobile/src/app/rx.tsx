import { Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Linking, Pressable, View } from 'react-native';

import { API, api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, Section, Segmented, T, useToast } from '@/ui/core';
import { inr } from '@/ui/therapy';

const STATUS: Record<string, string> = { recommended: 'Recommended', adjust_dose: 'Adjust your dose', discuss: 'Discuss with doctor', optional: 'Optional', blocked: 'Blocked' };

export default function Rx() {
  const p = usePalette();
  const goals = useApi<any[]>('/rx/goals');
  const plans = useApi<any[]>('/rx/plans');
  const track = useApi<any[]>('/rx/tracking');
  const [tab, setTab] = useState<'build' | 'plans' | 'tracking'>('build');
  const [goal, setGoal] = useState('heart');
  const [r, setR] = useState<any>(null);
  const [chosen, setChosen] = useState<Record<string, boolean>>({});
  const { toast, show } = useToast();

  useEffect(() => {
    setR(null);
    api(`/rx/recommend?goal=${goal}`).then((x) => {
      setR(x);
      setChosen(Object.fromEntries([...x.supplements, ...x.medicines].map((i: any) => [i.id, i.status !== 'optional'])));
    });
  }, [goal]);

  async function submit() {
    const items = Object.keys(chosen).filter((k) => chosen[k]);
    const pl = await api('/rx/plans', { body: { goal, items } });
    show(`Plan #${pl.id} sent to Dr. Meera Rao for review.`, 'success');
    plans.reload();
    setTab('plans');
  }
  async function order(id: number) {
    try { show((await api(`/rx/plans/${id}/order`, { method: 'POST' })).message, 'success'); plans.reload(); track.reload(); } catch (e: any) { show(e.message, 'alert'); }
  }

  const Item = ({ i }: { i: any }) => (
    <Card>
      <Row>
        <Pressable onPress={() => setChosen({ ...chosen, [i.id]: !chosen[i.id] })} accessibilityRole="checkbox" accessibilityState={{ checked: !!chosen[i.id] }}
          style={{ width: 24, height: 24, borderRadius: 6, borderWidth: 1.5, borderColor: p.teal, backgroundColor: chosen[i.id] ? p.teal : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
          {chosen[i.id] ? <T v="small" color="#fff">✓</T> : null}
        </Pressable>
        <T v="h3" style={{ flex: 1 }}>{i.name}</T>
        <Chip label={STATUS[i.status] ?? i.status} fg={i.rx ? p.copper : p.teal} bg={i.rx ? p.copperSoft : p.tealSoft} />
      </Row>
      <T v="body">{i.why}</T>
      <T v="small">Dose: {i.dose} · {i.contains}</T>
      <T v="small">Expected: {i.expected}{i.retest_on ? ` · re-test ${fmtDate(i.retest_on, true)}` : ''}</T>
      {i.overlaps?.map((o: string) => <T key={o} v="small" color={p.warn}>• {o}</T>)}
      {i.interactions.map((x: any) => <T key={x.with} v="small" color={x.severity === 'major' ? p.danger : p.warn}>⚠︎ {x.with}: {x.note} ({x.severity}, {x.source})</T>)}
      <Row style={{ flexWrap: 'wrap' }}><Chip label={`Evidence ${i.evidence}`} /><Chip label={`${inr(i.price)}${i.kind === 'iv' ? '' : ' / month'}`} />{i.rx ? <Chip label="Prescription only" fg={p.copper} bg={p.copperSoft} /> : null}</Row>
    </Card>
  );

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Supplements & Rx' }} />
        <T v="h1">Your personal stack</T>
        <Segmented options={[{ key: 'build', label: 'Build' }, { key: 'plans', label: `Plans · ${plans.data?.length ?? 0}` }, { key: 'tracking', label: 'Is it working?' }]} value={tab} onChange={setTab} />
        {tab === 'build' ? (
          <>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {(goals.data ?? []).map((g) => (
                <Pressable key={g.id} onPress={() => setGoal(g.id)} accessibilityRole="button"
                  style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.pill, backgroundColor: goal === g.id ? p.teal : p.surface, borderWidth: 1, borderColor: goal === g.id ? p.teal : p.border }}>
                  <T v="small" color={goal === g.id ? '#fff' : p.text}>{g.label}</T>
                </Pressable>
              ))}
            </View>
            {!r ? <Loading what="Reading your Vault…" /> : (
              <>
                <T v="small">{r.note}</T>
                <Section title="Supplements & Telomy Formulas">{r.supplements.map((i: any) => <Item key={i.id} i={i} />)}</Section>
                {r.medicines.length ? <Section title="Medicines to discuss with your doctor">{r.medicines.map((i: any) => <Item key={i.id} i={i} />)}</Section> : null}
                {r.already_taking.length ? <Section title="You already take">{r.already_taking.map((i: any) => <T key={i.id} v="small">• {i.name} — {i.why}</T>)}</Section> : null}
                {r.blocked.length ? <Section title="Blocked for your safety">{r.blocked.map((i: any) => <T key={i.id} v="small" color={p.danger}>• {i.name}: {i.interactions.map((x: any) => x.note).join('; ')}</T>)}</Section> : null}
                <Section title="Not offered, and why">{r.excluded.map((x: any) => <T key={x.name} v="small">• {x.name} — {x.why}</T>)}</Section>
                <Button title="Send to my doctor for sign-off" icon="signature" onPress={submit} disabled={!Object.values(chosen).some(Boolean)} testID="rx-submit" />
              </>
            )}
          </>
        ) : null}
        {tab === 'plans' ? (plans.data ?? []).map((pl) => (
          <Card key={pl.id}>
            <Row><T v="h3" style={{ flex: 1 }}>Plan #{pl.id} · {pl.plan.goal_label}</T>
              <Chip label={pl.state.replace('_', ' ')} fg={pl.state === 'approved' ? p.success : pl.state === 'rejected' ? p.danger : p.warn}
                bg={pl.state === 'approved' ? p.successSoft : pl.state === 'rejected' ? p.dangerSoft : p.warnSoft} /></Row>
            {pl.plan.items.map((i: any) => <T key={i.id} v="small">• {i.name} — {i.dose}{i.dose_edited_by_doctor ? ' (set by doctor)' : ''}</T>)}
            {pl.note ? <T v="body">{pl.doctor}: “{pl.note}”</T> : <T v="small">Waiting for Dr. Meera Rao.</T>}
            {pl.state === 'approved' ? (
              <Row>
                <Button title={pl.orders.length ? 'Order again' : 'Order (test mode)'} style={{ flex: 1 }} onPress={() => order(pl.id)} />
                <Button kind="secondary" title="e-Prescription" style={{ flex: 1 }} onPress={() => Linking.openURL(`${API}/rx/plans/${pl.id}/prescription.pdf`)} />
              </Row>
            ) : null}
            {pl.orders.map((o: any) => <T key={o.id} v="small" color={p.success}>Order #{o.id} · {inr(o.total)} · {o.status} · {o.channel}</T>)}
          </Card>
        )) : null}
        {tab === 'tracking' ? (track.data ?? []).map((t) => (
          <Card key={t.name}><T v="h3">{t.name}</T><T v="small">Since {fmtDate(t.since, true)}</T><T v="body">{t.message}</T></Card>
        )) : null}
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
