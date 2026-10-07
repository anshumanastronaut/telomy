import { router, Stack, useLocalSearchParams } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ErrorState, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';
import { PhaseLegend, SessionChart, phaseName } from '@/ui/therapy';

const ORDER = ['hr', 'rmssd', 'skin', 'spo2', 'core', 'resp', 'sbp', 'eda', 'perf'];
const KEY_FEATURES: [string, string, string][] = [
  ['hr_peak_delta', 'Heart-rate surge', 'bpm'], ['hrv_suppression_pct', 'HRV during', '%'], ['rebound_pct', 'HRV rebound (15–21 min after)', '%'],
  ['k_recovery', 'Recovery constant k', '/min'], ['half_life_min', 'Recovery half-life', 'min'], ['skin_drop', 'Skin temperature change', '°C'],
  ['rewarm_half_min', 'Rewarming half-time', 'min'], ['tri_min', 'Thermoregulatory recovery (5 °C)', 'min'], ['hr_peak', 'Peak heart rate', 'bpm'],
  ['cardio_load_min', 'Minutes above 100 bpm', 'min'], ['core_rise', 'Core temperature rise', '°C'], ['hr_post_delta', 'Heart rate after vs before', 'bpm'],
  ['hr_stable_delta', 'Heart rate at pressure', 'bpm'], ['rmssd_stable_pct', 'HRV at pressure', '%'], ['spo2_peak', 'Peak SpO₂', '%'],
  ['spo2_min', 'Lowest SpO₂', '%'], ['t_spo2_99_min', 'Time to SpO₂ 99 %', 'min'], ['perf_change_pct', 'Perfusion change', '%'], ['dose_j_cm2', 'Light dose delivered', 'J/cm²'],
];

export default function Session() {
  const { id, live } = useLocalSearchParams<{ id: string; live?: string }>();
  const p = usePalette();
  const { data: s, error, reload } = useApi<any>(`/therapy/sessions/${id}`, [id]);
  const [elapsed, setElapsed] = useState(0);
  const [pre, setPre] = useState({ energy: 5, calm: 5, pain: 2 });
  const [post, setPost] = useState({ energy: 5, calm: 5, pain: 2 });
  const { toast, show } = useToast();
  const inProgress = s?.status === 'in_progress';
  const total = s?.trace?.t?.length ? s.trace.t[s.trace.t.length - 1] : 0;

  useEffect(() => {
    if (!inProgress || !live) return;
    const h = setInterval(() => setElapsed((e) => Math.min(total, e + 60)), 250); // replay: 1 min every 0.25 s
    return () => clearInterval(h);
  }, [inProgress, live, total]);

  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!s) return <Screen edges={[]}><Loading what="Opening session…" /></Screen>;
  const tr = s.trace;
  const cut = inProgress && live ? tr.t.findIndex((t: number) => t > elapsed) : -1;
  const n = cut === -1 ? tr.t.length : Math.max(2, cut);
  const t = tr.t.slice(0, n);
  const phaseNow = tr.phases.find((ph: any) => elapsed >= ph.start && elapsed < ph.end)?.phase;
  const f = s.features || {};
  const lit: Record<string, any> = Object.fromEntries((f.vs_literature || []).map((c: any) => [c.metric, c]));
  const sig = ORDER.filter((k) => tr.signals[k]?.length);

  async function finish() {
    const r = await api(`/therapy/sessions/${id}/finish`, { body: { subjective: { pre, post } } });
    show('Session saved. Telomy will check tonight\'s sleep and HRV.', 'success');
    reload();
    return r;
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: s.name }} />
        <T v="h1">{s.name}</T>
        <T v="small">{fmtDate(s.ts)} · {s.ts.slice(11, 16)} · {s.device?.name ?? 'Centre device'}</T>
        <Row style={{ flexWrap: 'wrap' }}>
          <Chip label={s.source} fg={s.source.startsWith('simulated') ? p.warn : p.teal} bg={s.source.startsWith('simulated') ? p.warnSoft : p.tealSoft} />
          {Object.entries(s.params).filter(([, v]) => typeof v !== 'object').map(([k, v]) => <Chip key={k} label={`${k.replace(/_/g, ' ')}: ${v}`} />)}
          {f.safety ? <Chip label={`Safety: ${f.safety.label}`} fg={f.safety.tier ? p.danger : p.success} bg={f.safety.tier ? p.dangerSoft : p.successSoft} /> : null}
        </Row>
        {s.source.startsWith('simulated') ? (
          <T v="small">This trace is your personal ODE prior — the response Telomy expects from your θ (resting HR, HRV, fitness, metabolic and vascular markers). Pair a chest strap, the Telomy patch or the machine's telemetry and real data replaces it.</T>
        ) : null}

        {inProgress && live ? (
          <Card tone="copper">
            <Row><T v="h3" style={{ flex: 1 }}>{phaseNow ? phaseName(phaseNow) : 'Complete'}</T><T v="num" style={{ fontSize: 18 }}>{Math.floor(elapsed / 60)}′</T></Row>
            <T v="small">{s.inside.find(([w]: [string]) => true)?.[1]}</T>
          </Card>
        ) : null}

        <Card>
          <PhaseLegend phases={tr.phases} />
          {sig.map((k) => (
            <SessionChart key={k} t={t} y={tr.signals[k].slice(0, n)} phases={tr.phases} unit={s.labels[k][1]} label={s.labels[k][0]}
              decimals={['skin', 'core', 'eda', 'perf'].includes(k) ? 1 : 0} height={k === 'hr' || k === 'rmssd' ? 150 : 110} color={k === 'skin' || k === 'core' ? p.copper : undefined} />
          ))}
          <T v="small">Copper shading = in session; teal = recovery. Tap a chart to read a moment.</T>
        </Card>

        {!inProgress ? (
          <Section title="What happened inside">
            <Card style={{ paddingVertical: 4 }}>
              {KEY_FEATURES.filter(([k]) => f[k] != null).map(([k, label, unit], i) => (
                <View key={k} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                  <Row>
                    <T v="body" style={{ flex: 1 }}>{label}</T>
                    <T v="num" style={{ fontSize: 16 }}>{typeof f[k] === 'number' && f[k] > 0 && unit === '%' ? '+' : ''}{f[k]} <T v="small">{unit}</T></T>
                  </Row>
                  {lit[k] ? <T v="small" color={lit[k].verdict === 'typical' ? p.success : p.warn}>Literature {lit[k].range[0]} to {lit[k].range[1]} · {lit[k].source} · {lit[k].verdict}</T> : null}
                </View>
              ))}
            </Card>
            {f.safety?.reasons?.length ? <Card tone="copper">{f.safety.reasons.map((r: string) => <T key={r} v="body">⚠︎ {r}</T>)}</Card> : null}
            {s.subjective?.post ? (
              <T v="small">You felt: {Object.keys(s.subjective.post).map((k) => `${k} ${s.subjective.pre?.[k]} → ${s.subjective.post[k]}`).join(' · ')}</T>
            ) : null}
            {s.adverse ? <T v="small" color={p.danger}>Reported: {s.adverse}</T> : null}
          </Section>
        ) : (
          <Section title="Quick check-in">
            {(['energy', 'calm', 'pain'] as const).map((k) => (
              <View key={k} style={{ gap: 6 }}>
                <T v="label">{k} before → after (0–10)</T>
                <Row>
                  <Scale value={pre[k]} onChange={(v) => setPre({ ...pre, [k]: v })} />
                  <T v="small">→</T>
                  <Scale value={post[k]} onChange={(v) => setPost({ ...post, [k]: v })} />
                </Row>
              </View>
            ))}
            <Button title="Finish session" icon="checkmark.circle" onPress={finish} testID="finish-session" />
          </Section>
        )}

        <Section title="The science">
          {s.inside.map(([w, what]: [string, string]) => <T key={w} v="small"><T v="small" color={p.copper}>{w}: </T>{what}</T>)}
          {s.refs.map((r: string) => <T key={r} v="small">• {r}</T>)}
        </Section>
        <Button kind="ghost" title={`All ${s.name} sessions`} onPress={() => router.push(`/therapy/${s.modality}`)} />
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}

function Scale({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const p = usePalette();
  return (
    <Row gap={2} style={{ flex: 1 }}>
      {[0, 2, 4, 6, 8, 10].map((v) => (
        <Pressable key={v} onPress={() => onChange(v)} accessibilityRole="button" accessibilityLabel={`${v}`}
          style={{ flex: 1, height: 30, borderRadius: radius.sm, alignItems: 'center', justifyContent: 'center',
            backgroundColor: value === v ? p.teal : p.surfaceAlt }}>
          <T v="small" color={value === v ? '#fff' : p.text}>{v}</T>
        </Pressable>
      ))}
    </Row>
  );
}
