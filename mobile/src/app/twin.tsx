import { router, Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';
import Svg, { Line, Path, Text as SvgText } from 'react-native-svg';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, Section, Segmented, T } from '@/ui/core';

function Dual({ a, b, unit, height = 120, labels = ['Current path', 'Scenario'], xLabel = (x: number) => `${Math.round(x / 365 * 10) / 10}y` }:
  { a: [number, number][]; b?: [number, number][]; unit: string; height?: number; labels?: string[]; xLabel?: (x: number) => string }) {
  const p = usePalette();
  const [w, setW] = useState(320);
  const all = [...a, ...(b ?? [])];
  if (all.length < 2) return null;
  const xs = all.map((q) => q[0]), ys = all.map((q) => q[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
  const pad = { l: 36, r: 8, t: 8, b: 18 };
  const sx = (x: number) => pad.l + ((x - x0) / Math.max(1e-9, x1 - x0)) * (w - pad.l - pad.r);
  const sy = (y: number) => pad.t + (1 - (y - lo) / (hi - lo)) * (height - pad.t - pad.b);
  const path = (s: [number, number][]) => s.map((q, i) => `${i ? 'L' : 'M'}${sx(q[0]).toFixed(1)},${sy(q[1]).toFixed(1)}`).join(' ');
  const f = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2));
  return (
    <View onLayout={(e) => setW(e.nativeEvent.layout.width)} style={{ gap: 2 }}>
      <Svg width={w} height={height}>
        {[lo, (lo + hi) / 2, hi].map((v, i) => (
          <React.Fragment key={i}>
            <Line x1={pad.l} x2={w - pad.r} y1={sy(v)} y2={sy(v)} stroke={p.border} opacity={0.5} />
            <SvgText x={pad.l - 4} y={sy(v) + 3} fontSize={9} fill={p.muted} textAnchor="end" fontFamily="Inter_400Regular">{f(v)}</SvgText>
          </React.Fragment>
        ))}
        <Path d={path(a)} stroke={p.muted} strokeWidth={1.4} fill="none" strokeDasharray={b ? '4,3' : undefined} />
        {b ? <Path d={path(b)} stroke={p.teal} strokeWidth={2} fill="none" /> : null}
        <SvgText x={pad.l} y={height - 4} fontSize={9} fill={p.muted} fontFamily="Inter_400Regular">{xLabel(x0)}</SvgText>
        <SvgText x={w - pad.r} y={height - 4} fontSize={9} fill={p.muted} textAnchor="end" fontFamily="Inter_400Regular">{xLabel(x1)}</SvgText>
      </Svg>
      {b ? <T v="small" color={p.muted}>– – {labels[0]}  ·  ━ {labels[1]} ({unit})</T> : <T v="small" color={p.muted}>{unit}</T>}
    </View>
  );
}

export default function Twin() {
  const p = usePalette();
  const o = useApi<any>('/twin');
  const mir = useApi<any>('/twin/mirror');
  const [preset, setPreset] = useState<string>('telomy_plan');
  const [years, setYears] = useState(5);
  const [sim, setSim] = useState<any>(null);
  const [drinking, setDrinking] = useState(false);
  const [dayT, setDayT] = useState<any>(null);
  const [tab, setTab] = useState<'future' | 'today' | 'mirror'>('future');

  useEffect(() => {
    setSim(null);
    api('/twin/simulate', { body: { preset, years } }).then(setSim).catch(() => setSim({ headline: ['The twin could not run this scenario — pull to retry.'], variables: [], risk_baseline: [], risk_scenario: [], disclaimer: '' }));
  }, [preset, years]);
  useEffect(() => { api(`/twin/day?drinking=${drinking}`).then(setDayT).catch(() => setDayT(null)); }, [drinking]);

  if (!o.data) return <Screen edges={[]}><Loading what="Waking your twin…" /></Screen>;
  const d = o.data;
  const rb = sim?.risk_baseline?.at(-1)?.[1], rs = sim?.risk_scenario?.at(-1)?.[1];
  const moved = (sim?.variables ?? []).filter((v: any) => Math.abs(v.difference) / (Math.abs(v.baseline_end) + 1e-6) > 0.015)
    .sort((x: any, y: any) => Math.abs(y.difference) / (Math.abs(y.baseline_end) + 1e-6) - Math.abs(x.difference) / (Math.abs(x.baseline_end) + 1e-6));

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Digital twin' }} />
      <T v="h1">Your digital twin</T>
      <T v="small">{d.about}</T>
      <Row style={{ flexWrap: 'wrap' }}>
        <Chip label={`PhenoAge ${d.risk_now.phenoage} at ${d.risk_now.age}`} fg={p.teal} bg={p.tealSoft} />
        <Chip label={`PREVENT 10-y ${d.risk_now.prevent_10y}% · 30-y ${d.risk_now.prevent_30y}%`} />
        {mir.data ? <Chip label={`Twin fidelity ${Math.round(mir.data.fidelity * 100)}%`} fg={p.copper} bg={p.copperSoft} /> : null}
      </Row>
      <Card tone="copper">
        <T v="label">What your twin learned about you</T>
        <T v="body">{d.calibration.vitd_note}</T>
        <T v="small">Alcohol night → HRV {d.calibration.hrv_alcohol_note}. Each extra hour of sleep ≈ +{d.calibration.hrv_per_sleep_hour} ms HRV.</T>
      </Card>

      <Segmented options={[{ key: 'future', label: 'What if' }, { key: 'today', label: 'Today' }, { key: 'mirror', label: 'Mirror' }]} value={tab} onChange={setTab} />

      {tab === 'future' ? (
        <>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
            {d.presets.map((x: any) => (
              <Pressable key={x.id} onPress={() => setPreset(x.id)} accessibilityRole="button" testID={`preset-${x.id}`}
                style={{ paddingHorizontal: 10, paddingVertical: 7, borderRadius: radius.pill, backgroundColor: preset === x.id ? p.teal : p.surface, borderWidth: 1, borderColor: preset === x.id ? p.teal : p.border }}>
                <T v="small" color={preset === x.id ? '#fff' : p.text}>{x.label.split(' (')[0]}</T>
              </Pressable>
            ))}
          </View>
          <Row>
            {[1, 5, 10].map((y) => (
              <Pressable key={y} onPress={() => setYears(y)} accessibilityRole="button"
                style={{ flex: 1, height: 36, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', backgroundColor: years === y ? p.teal : p.surface, borderWidth: 1, borderColor: p.border }}>
                <T v="body" color={years === y ? '#fff' : p.text}>{y} year{y > 1 ? 's' : ''}</T>
              </Pressable>
            ))}
          </Row>
          {!sim ? <Loading what="Running your twin forward…" /> : (
            <>
              <Card tone="teal">
                {sim.headline.map((h: string) => <T key={h} v="body">{h}</T>)}
                {rb && rs ? (
                  <Row style={{ flexWrap: 'wrap', marginTop: 4 }}>
                    <Chip label={`PhenoAge ${rb.phenoage} → ${rs.phenoage}`} fg={rs.phenoage <= rb.phenoage ? p.success : p.danger} bg={p.surface} />
                    <Chip label={`30-y CVD ${rb.prevent_30y}% → ${rs.prevent_30y}%`} fg={rs.prevent_30y <= rb.prevent_30y ? p.success : p.danger} bg={p.surface} />
                  </Row>
                ) : null}
                <T v="small" color={p.muted}>{sim.disclaimer}</T>
              </Card>
              {moved.slice(0, 8).map((v: any) => (
                <Card key={v.key}>
                  <Row>
                    <T v="h3" style={{ flex: 1 }}>{v.label}</T>
                    <T v="num" style={{ fontSize: 15 }} color={v.better ? p.success : v.better === false ? p.danger : p.text}>
                      {Math.round(v.baseline_end * 10) / 10} → {Math.round(v.scenario_end * 10) / 10} <T v="small">{v.unit}</T>
                    </T>
                  </Row>
                  <Dual a={v.baseline} b={v.scenario} unit={v.unit} />
                  {v.why ? <T v="small">{v.why}</T> : null}
                </Card>
              ))}
              {!moved.length ? <Card><T v="body">This change barely moves your twin over {years} year{years > 1 ? 's' : ''} — you may already be doing it.</T></Card> : null}
            </>
          )}
        </>
      ) : null}

      {tab === 'today' && dayT && !dayT.has_routine ? (
        <Card><T v="body">Your twin needs your routine to simulate a day. Describe it once — typed or spoken.</T><Button title="Add my routine" onPress={() => router.push('/routine')} /></Card>
      ) : null}
      {tab === 'today' && dayT?.has_routine ? (
        <>
          <Row>
            <Pressable onPress={() => setDrinking(false)} style={{ flex: 1 }}><Chip label="Non-drinking day" fg={!drinking ? '#fff' : p.text} bg={!drinking ? p.teal : p.surfaceAlt} /></Pressable>
            <Pressable onPress={() => setDrinking(true)} style={{ flex: 1 }}><Chip label="Drinking day" fg={drinking ? '#fff' : p.text} bg={drinking ? p.copper : p.surfaceAlt} /></Pressable>
          </Row>
          <Card>
            <T v="label">Caffeine in your blood (mg)</T>
            <Dual a={dayT.hours.map((h: number, i: number) => [h, dayT.caffeine_mg[i]])} unit="mg" xLabel={(x) => `${Math.floor(x % 24)}:00`} />
            {dayT.nicotine_mg.some((v: number) => v > 0) ? (<><T v="label">Nicotine (mg)</T>
            <Dual a={dayT.hours.map((h: number, i: number) => [h, dayT.nicotine_mg[i]])} unit="mg" height={90} xLabel={(x) => `${Math.floor(x % 24)}:00`} /></>) : null}
            {drinking ? (<><T v="label">Blood alcohol (%)</T><Dual a={dayT.hours.map((h: number, i: number) => [h, dayT.bac_pct[i]])} unit="% BAC" height={90} xLabel={(x) => `${Math.floor(x % 24)}:00`} /></>) : null}
          </Card>
          <Card tone="teal">
            <T v="label">Tonight, predicted</T>
            <T v="body">HRV {dayT.tonight.hrv} ms (your baseline {dayT.tonight.hrv_baseline}) · sleep {dayT.tonight.sleep_h} h · bedtime {dayT.bedtime}</T>
            {dayT.notes.map((n: string) => <T key={n} v="small">• {n}</T>)}
            <T v="small" color={p.muted}>{dayT.method}</T>
          </Card>
        </>
      ) : null}

      {tab === 'mirror' && mir.data ? (
        <>
          <Card>
            <T v="label">Night HRV — your body vs your twin (last 45 nights)</T>
            <Dual a={mir.data.hrv.series.map((s: any, i: number) => [i, s.actual])} b={mir.data.hrv.series.map((s: any, i: number) => [i, s.twin])} unit="ms"
              labels={['You', 'Twin']} xLabel={(x) => (x === 0 ? '45 nights ago' : 'last night')} />
            <T v="small">The twin explains {Math.round(mir.data.hrv.r2 * 100)}% of your night-to-night HRV from what you logged (error ±{mir.data.hrv.mae_ms} ms).</T>
          </Card>
          <Section title="Labs: did the twin see it coming?">
            {mir.data.labs.map((l: any) => (
              <Card key={l.marker}>
                <Row><T v="h3" style={{ flex: 1 }}>{l.marker}</T><Chip label={l.comment === 'tracked' ? 'Tracked' : 'Unexplained drift'} fg={l.comment === 'tracked' ? p.success : p.copper} bg={l.comment === 'tracked' ? p.successSoft : p.copperSoft} /></Row>
                <T v="small">{l.from} → {l.to} (twin expected {l.twin_expected}; unexplained {l.unexplained > 0 ? '+' : ''}{l.unexplained}, {l.unexplained_pct}%)</T>
                {l.comment !== 'tracked' ? <T v="small">{l.comment}</T> : null}
              </Card>
            ))}
          </Section>
        </>
      ) : null}

      <Section title="Your body, as the twin holds it">
        {d.systems.map((s: any) => (
          <Card key={s.name}>
            <T v="label">{s.name}</T>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', rowGap: 8 }}>
              {s.variables.map((v: any) => (
                <View key={v.key} style={{ width: '50%' }}>
                  <T v="small">{v.label}</T>
                  <T v="body" style={{ fontWeight: '600' }}>{Math.round(v.value * 10) / 10} <T v="small">{v.unit}</T></T>
                </View>
              ))}
            </View>
          </Card>
        ))}
      </Section>
      <View style={{ height: space[2] }} />
    </Screen>
  );
}
