import { router, Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';
import { SafetyChip, inr } from '@/ui/therapy';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function TherapyPlan() {
  const p = usePalette();
  const goals = useApi<any[]>('/therapy/goals');
  const [goal, setGoal] = useState('sleep');
  const [perWeek, setPerWeek] = useState(4);
  const [plan, setPlan] = useState<any>(null);
  const [saved, setSaved] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const { toast, show } = useToast();

  useEffect(() => {
    let live = true;
    setPlan(null);
    api('/therapy/plans/preview', { body: { goal, per_week: perWeek } }).then((r) => live && setPlan(r)).catch((e) => show(e.message, 'alert'));
    return () => { live = false; };
  }, [goal, perWeek]);

  async function submit() {
    setBusy(true);
    try {
      const r = await api('/therapy/plans', { body: { goal, per_week: perWeek } });
      setSaved(r);
      show('Sent to Dr. Meera Rao for sign-off.', 'success');
    } finally { setBusy(false); }
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Build a therapy plan' }} />
        <T v="h1">Build a therapy plan</T>
        <T v="label">Your goal</T>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {(goals.data ?? []).map((g) => (
            <Pressable key={g.id} onPress={() => setGoal(g.id)} accessibilityRole="button" accessibilityState={{ selected: goal === g.id }} testID={`goal-${g.id}`}
              style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.pill, backgroundColor: goal === g.id ? p.teal : p.surface, borderWidth: 1, borderColor: goal === g.id ? p.teal : p.border }}>
              <T v="small" color={goal === g.id ? '#fff' : p.text}>{g.label}</T>
            </Pressable>
          ))}
        </View>
        <T v="label">Sessions per week</T>
        <Row>
          {[2, 3, 4, 5, 6].map((n) => (
            <Pressable key={n} onPress={() => setPerWeek(n)} accessibilityRole="button"
              style={{ flex: 1, height: 40, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', backgroundColor: perWeek === n ? p.teal : p.surface, borderWidth: 1, borderColor: p.border }}>
              <T v="body" color={perWeek === n ? '#fff' : p.text}>{n}</T>
            </Pressable>
          ))}
        </Row>
        {!plan ? <Loading what="Ranking therapies for you…" /> : (
          <>
            <Section title={`${plan.goal_label} · ${inr(plan.monthly_price)} / month`}>
              {plan.items.map((i: any) => (
                <Card key={i.modality} onPress={() => router.push(`/therapy/${i.modality}`)}>
                  <Row><T v="h3" style={{ flex: 1 }}>{i.name}</T><Chip label={`${i.per_week}× / week`} fg={p.teal} bg={p.tealSoft} /></Row>
                  <T v="small">{Object.entries(i.params).filter(([, v]) => typeof v !== 'object').map(([k, v]) => `${k.replace(/_/g, ' ')} ${v}`).join(' · ')} · {i.hour}:00</T>
                  <T v="body">{i.reason}</T>
                  {i.rules.map((r: string) => <T key={r} v="small" color={p.copper}>• {r}</T>)}
                  <Row><SafetyChip status={i.safety.status} /><Chip label={`Evidence ${i.evidence}`} /></Row>
                </Card>
              ))}
            </Section>
            <Card>
              <T v="label">Your week</T>
              {DAYS.map((d) => (
                <Row key={d} style={{ paddingVertical: 4 }}>
                  <T v="body" style={{ width: 44 }}>{d}</T>
                  <T v="small" style={{ flex: 1 }}>{(plan.week[d] ?? []).map((s: any) => `${plan.items.find((i: any) => i.modality === s.modality)?.name.split(' (')[0]} ${s.hour}:00`).join(' · ') || 'Rest'}</T>
                </Row>
              ))}
            </Card>
            {plan.formula_pairing ? <Card tone="copper"><T v="label">Pairs with</T><T v="body">{plan.formula_pairing}</T></Card> : null}
            <Section title="Checkpoints">{plan.checkpoints.map((c: string) => <T key={c} v="small">• {c}</T>)}</Section>
            {plan.excluded.length ? <Section title="Left out for safety">{plan.excluded.map((x: any) => <T key={x.modality} v="small">• {x.name}: {x.why}</T>)}</Section> : null}
            <T v="small">{plan.note}</T>
            {saved ? (
              <Card tone="teal"><T v="h3">Plan #{saved.id} sent</T><T v="small">Status: {saved.state.replace('_', ' ')}. When Dr. Meera Rao signs, the next 4 weeks are booked automatically.</T></Card>
            ) : <Button title="Send to my clinician" icon="paperplane" loading={busy} onPress={submit} disabled={!plan.items.length} testID="send-plan" />}
          </>
        )}
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
