// Your longevity plan — the member-facing view of /me/longevity (evidence-graded interventions) and
// /me/macros (the protein/fibre/fat fix). Framed for a member, not a prescriber: lifestyle first (do these),
// supplements to consider, and anything clinical/experimental is grouped as "talk to your clinician" — never
// presented as something to self-start. Everything is decision-support; nothing here claims to extend lifespan.
import { router, Stack } from 'expo-router';
import React, { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';

import { api } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Card, Chip, Divider, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';

const GRADE_TXT: Record<string, string> = { A: 'strong evidence', B: 'moderate', C: 'limited/mixed', D: 'weak/contested' };

function GradeChip({ grade }: { grade: string }) {
  const p = usePalette();
  const c = grade === 'A' ? p.teal : grade === 'B' ? p.teal : grade === 'C' ? p.copper : p.muted;
  return <Chip label={grade} fg={p.onAccent} bg={c} />;
}

function InterventionRow({ it, member = false }: { it: any; member?: boolean }) {
  const p = usePalette();
  return (
    <View style={{ paddingVertical: 10 }}>
      <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Row style={{ flex: 1, gap: 8, alignItems: 'flex-start' }}>
          <GradeChip grade={it.grade} />
          <View style={{ flex: 1 }}>
            <T v="body" style={{ fontWeight: '600' }}>{it.name}</T>
            <T v="small" color={p.muted}>{it.scope}</T>
          </View>
        </Row>
        {it.doctor_gate ? <Chip label="Rx" fg={p.copper} bg={p.copperSoft} /> : null}
      </Row>
      {!member ? null : <T v="small" style={{ marginTop: 4 }}>{it.effect}</T>}
    </View>
  );
}

export default function PlanScreen() {
  const p = usePalette();
  const [lon, setLon] = useState<any>(null);
  const [mac, setMac] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setErr(null); setLoading(true);
    try {
      const [l, m] = await Promise.all([
        api('/me/longevity', { method: 'POST', body: { goals: ['longevity'], include_experimental: true } }),
        api('/me/macros', { method: 'POST', body: { activity: 'moderate' } }),
      ]);
      setLon(l); setMac(m);
    } catch (e: any) { setErr(e?.message || 'Could not load your plan.'); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  if (err) return <Screen edges={[]}><Stack.Screen options={{ title: 'Your plan' }} /><ErrorState message={err} onRetry={load} /></Screen>;
  if (loading || !lon) return <Screen edges={[]}><Stack.Screen options={{ title: 'Your plan' }} /><Loading what="Building your plan…" /></Screen>;

  const tiers = lon.tiers || {};
  const foundation = tiers.foundation || [];
  const optional = tiers.optional || [];
  const clinical = [...(tiers.clinical || []), ...(tiers.experimental || [])];

  const macroCard = (m: any) => {
    if (!m) return null;
    let target = '';
    if (m.nutrient === 'protein') target = `${m.target_g_per_day[0]}–${m.target_g_per_day[1]} g/day`;
    else if (m.nutrient === 'fibre') target = `${m.target_g_per_day} g/day${m.current_g_per_day != null ? ` (now ~${m.current_g_per_day})` : ''}`;
    else target = `${m.target_pct_kcal[0]}–${m.target_pct_kcal[1]}% of calories`;
    const fixes: string[] = m.fix || m.emphasis || [];
    return (
      <Card key={m.nutrient}>
        <Row style={{ justifyContent: 'space-between' }}>
          <T v="h3" style={{ textTransform: 'capitalize' }}>{m.nutrient}</T>
          <T v="num" style={{ fontSize: 18 }}>{target}</T>
        </Row>
        {m.titration ? <T v="small" color={p.copper}>{m.titration}</T> : null}
        {fixes.slice(0, 4).map((f, i) => <T key={i} v="small">• {f}</T>)}
        {m.sources?.length ? <T v="small" color={p.muted}>Sources: {m.sources.join(', ')}</T> : null}
      </Card>
    );
  };

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Your plan' }} />
      <T v="h1">Your longevity plan</T>
      <T v="small" color={p.muted}>Evidence-graded and grounded in your own numbers. Start with the foundations — they have the best evidence and the lowest risk. Nothing here claims to extend lifespan.</T>

      {/* macro fix */}
      {mac?.protein ? (
        <Section title="Protein · fibre · fat">
          {mac.energy ? <T v="small" color={p.muted}>Around {mac.energy.maintenance_kcal} kcal/day to maintain.</T> : null}
          {macroCard(mac.protein)}
          {macroCard(mac.fibre)}
          {macroCard(mac.fat)}
        </Section>
      ) : null}

      {/* foundation */}
      {foundation.length ? (
        <Section title="Start here — lifestyle">
          <Card style={{ gap: 0 }}>
            {foundation.map((it: any, i: number) => (
              <View key={it.id}>{i ? <Divider /> : null}<InterventionRow it={it} member /></View>
            ))}
          </Card>
        </Section>
      ) : null}

      {/* supplements */}
      {optional.length ? (
        <Section title="Supplements to consider">
          <Card style={{ gap: 0 }}>
            {optional.map((it: any, i: number) => (
              <View key={it.id}>{i ? <Divider /> : null}<InterventionRow it={it} member /></View>
            ))}
          </Card>
          <T v="small" color={p.muted}>Biomarker-driven; mostly a biomarker-level benefit. Check with your clinician before starting any supplement.</T>
        </Section>
      ) : null}

      {/* clinical / experimental — doctor-gated */}
      {clinical.length ? (
        <Section title="Talk to your clinician">
          <Card tone="copper">
            <T v="small">These are prescriber-decisions — approved medications or investigational options a doctor would weigh for you. They are not something to start on your own.</T>
            <View style={{ gap: 0, marginTop: 8 }}>
              {clinical.map((it: any, i: number) => (
                <View key={it.id}>{i ? <Divider /> : null}<InterventionRow it={it} /></View>
              ))}
            </View>
          </Card>
        </Section>
      ) : null}

      <T v="small" color={p.muted} style={{ marginTop: 8 }}>{lon.disclaimer}</T>
      <Card tone="teal" onPress={() => router.push('/overview')}>
        <Row>
          <View style={{ flex: 1 }}><T v="h3">Your health summary</T><T v="small">See the labs and risk behind this plan.</T></View>
        </Row>
      </Card>
      <View style={{ height: 16 }} />
    </Screen>
  );
}
