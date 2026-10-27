import { router, Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Svg, { Line, Path, Text as SvgText } from 'react-native-svg';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ErrorState, Icon, Loading, Row, Screen, Section, Segmented, T } from '@/ui/core';
import { ORGAN_LABEL, systemOfOrgan, Twin3D } from '@/twin3d/Twin3D';
import type { OrganId } from '@/twin3d/scene';

// Organ labels — flat glass chips flanking the 3D body, left and right, ordered top→bottom at roughly their
// anatomical height. No leader lines or body anchors: the projected organ positions can't be tracked from the
// WebView as the camera moves, so any pointer would be approximate. The chip's status dot carries the system's
// health; tapping a chip flies the camera to that organ (same `selected` state as a mesh tap).
const STAGE_H = 460; // keep in sync with the Twin3D height
const LBL_W = 98;    // fixed label width so the two columns line up
const MARGIN = 8;
const INK = '#F4F4EF';

type Slot = { id: OrganId; label: string; side: 'l' | 'r'; y: number };
const SLOTS: Slot[] = [
  { id: 'brain', label: 'Brain', side: 'l', y: 0.07 },
  { id: 'heart', label: 'Heart', side: 'l', y: 0.24 },
  { id: 'stomach', label: 'Stomach', side: 'l', y: 0.41 },
  { id: 'kidneys', label: 'Kidneys', side: 'l', y: 0.58 },
  { id: 'bladder', label: 'Bladder', side: 'l', y: 0.75 },
  { id: 'skeleton', label: 'Skeleton', side: 'l', y: 0.92 },
  { id: 'vessels', label: 'Vessels', side: 'r', y: 0.12 },
  { id: 'lungs', label: 'Lungs', side: 'r', y: 0.30 },
  { id: 'liver', label: 'Liver', side: 'r', y: 0.48 },
  { id: 'pancreas', label: 'Pancreas', side: 'r', y: 0.66 },
  { id: 'intestines', label: 'Gut', side: 'r', y: 0.84 },
];

function OrganRail({ systems, selected, onSelect }: { systems: any[]; selected: OrganId | null; onSelect: (o: OrganId | null) => void }) {
  const p = usePalette();
  const H = STAGE_H;
  const statusColor = (st?: string) => (st === 'high' ? p.danger : st === 'watch' ? p.warn : st === 'ok' ? p.success : '#8A8A82');
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      {SLOTS.map((s) => {
        const on = selected === s.id;
        const st = systems.find((x) => x.name === systemOfOrgan(s.id))?.status as string | undefined;
        const dot = statusColor(st);
        const flagged = st === 'high' || st === 'watch';
        return (
          <Pressable key={s.id} onPress={() => onSelect(on ? null : s.id)} hitSlop={8} accessibilityRole="button"
            accessibilityLabel={`Focus ${s.label}${st ? `, ${st === 'high' ? 'out of range' : st === 'watch' ? 'watch' : 'in range'}` : ''}`}
            style={{ position: 'absolute', top: s.y * H - 13, width: LBL_W,
              ...(s.side === 'l' ? { left: MARGIN } : { right: MARGIN }),
              flexDirection: s.side === 'l' ? 'row' : 'row-reverse', alignItems: 'center', gap: 6,
              paddingVertical: 5, paddingHorizontal: 9, borderRadius: 9,
              backgroundColor: on ? p.teal : 'rgba(16,18,17,0.55)',
              borderWidth: StyleSheet.hairlineWidth, borderColor: on ? p.teal : 'rgba(255,255,255,0.16)' }}>
            <View style={{ width: flagged ? 7 : 6, height: flagged ? 7 : 6, borderRadius: 4, backgroundColor: on ? INK : dot }} />
            <T numberOfLines={1} style={{ flex: 1, fontFamily: 'Geist_500Medium', fontSize: 10, letterSpacing: 0.4,
              textAlign: s.side === 'l' ? 'left' : 'right', color: on ? p.onAccent : INK }}>{s.label.toUpperCase()}</T>
          </Pressable>
        );
      })}
    </View>
  );
}

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
            <SvgText x={pad.l - 4} y={sy(v) + 3} fontSize={9} fill={p.muted} textAnchor="end" fontFamily="Geist_400Regular">{f(v)}</SvgText>
          </React.Fragment>
        ))}
        <Path d={path(a)} stroke={p.muted} strokeWidth={1.4} fill="none" strokeDasharray={b ? '4,3' : undefined} />
        {b ? <Path d={path(b)} stroke={p.teal} strokeWidth={2} fill="none" /> : null}
        <SvgText x={pad.l} y={height - 4} fontSize={9} fill={p.muted} fontFamily="Geist_400Regular">{xLabel(x0)}</SvgText>
        <SvgText x={w - pad.r} y={height - 4} fontSize={9} fill={p.muted} textAnchor="end" fontFamily="Geist_400Regular">{xLabel(x1)}</SvgText>
      </Svg>
      {b ? <T v="small" color={p.muted}>– – {labels[0]}  ·  ━ {labels[1]} ({unit})</T> : <T v="small" color={p.muted}>{unit}</T>}
    </View>
  );
}

/** Under the 3D body: what the tapped organ's system shows — status, each problem in plain language, its markers. */
function OrganPanel({ systems, organ, onClear }: { systems: any[]; organ: OrganId | null; onClear: () => void }) {
  const p = usePalette();
  if (!organ) {
    const flagged = systems.filter((s) => s.status !== 'ok');
    return (
      <Row style={{ flexWrap: 'wrap' }} gap={6}>
        <T v="small" color={p.muted}>Tap an organ.</T>
        {flagged.map((s) => <Chip key={s.name} label={s.name} fg={s.status === 'high' ? p.danger : p.warn} bg={s.status === 'high' ? p.dangerSoft : p.warnSoft} />)}
      </Row>
    );
  }
  const sysName = systemOfOrgan(organ);
  const sys = systems.find((s) => s.name === sysName);
  const sc = !sys ? p.muted : sys.status === 'high' ? p.danger : sys.status === 'watch' ? p.warn : p.success;
  return (
    <Card style={{ gap: space[2] }}>
      <Row>
        <View style={{ flex: 1 }}>
          <T v="h2">{ORGAN_LABEL[organ]}</T>
          <T v="small">{sys ? `${sys.name} · ${sys.status === 'high' ? 'out of range' : sys.status === 'watch' ? 'worth watching' : 'in range'}` : 'No markers for this organ in your Vault yet'}</T>
        </View>
        <Button kind="ghost" title="Whole body" onPress={onClear} />
      </Row>
      {sys?.problems?.map((pr: any) => (
        <Row key={pr.key} style={{ alignItems: 'flex-start' }} gap={8}>
          <Icon name={pr.severity === 'high' ? 'exclamationmark.triangle.fill' : 'eye.fill'} size={13} color={pr.severity === 'high' ? p.danger : p.warn} />
          <View style={{ flex: 1 }}>
            <T v="body" style={{ fontWeight: '600' }}>{pr.label} {pr.direction} · {Math.round(pr.value * 10) / 10} {pr.unit}</T>
            <T v="small">{pr.detail}</T>
          </View>
        </Row>
      ))}
      {sys && !sys.problems?.length ? <T v="small" color={sc}>All markers for this system are in range.</T> : null}
      {sys ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', rowGap: 8 }}>
          {sys.variables.map((v: any) => (
            <View key={v.key} style={{ width: '50%' }}><T v="small">{v.label}</T><T v="body" style={{ fontWeight: '600' }}>{Math.round(v.value * 10) / 10} <T v="small">{v.unit}</T></T></View>
          ))}
        </View>
      ) : <T v="small" color={p.muted}>Add a kidney panel (creatinine, eGFR, urine ACR) to your Vault and the twin will map it here.</T>}
    </Card>
  );
}

export default function Twin({ inTab = false }: { inTab?: boolean } = {}) {
  const p = usePalette();
  const o = useApi<any>('/twin');
  const mir = useApi<any>('/twin/mirror');
  const proj = useApi<any>('/twin/projections');
  const organs = useApi<any>('/me/organs');
  const [preset, setPreset] = useState<string>('telomy_plan');
  const [years, setYears] = useState(5);
  const [sim, setSim] = useState<any>(null);
  const [drinking, setDrinking] = useState(false);
  const [dayT, setDayT] = useState<any>(null);
  const [tab, setTab] = useState<'future' | 'today' | 'mirror'>('future');
  const [organSel, setOrganSel] = useState<OrganId | null>(null);
  const [touching3d, setTouching3d] = useState(false);

  useEffect(() => {
    setSim(null);
    api('/twin/simulate', { body: { preset, years } }).then(setSim).catch(() => setSim({ headline: ['The twin could not run this scenario — pull to retry.'], variables: [], risk_baseline: [], risk_scenario: [], disclaimer: '' }));
  }, [preset, years]);
  useEffect(() => { api(`/twin/day?drinking=${drinking}`).then(setDayT).catch(() => setDayT(null)); }, [drinking]);

  // Once the fetch has settled with no data (a timeout on a poor connection, or an empty response), show a retry
  // instead of the loader forever — the loader is gated on data, so without this the screen hangs on "Waking your twin…".
  if (!o.data && !o.loading) return <Screen edges={inTab ? ['top'] : []}><ErrorState message={o.error ?? 'Your twin could not load. Check your connection and retry.'} onRetry={() => { o.reload(); mir.reload(); proj.reload(); organs.reload(); }} /></Screen>;
  if (!o.data) return <Screen edges={inTab ? ['top'] : []}><Loading what="Waking your twin…" /></Screen>;
  const d = o.data;
  const rb = sim?.risk_baseline?.at(-1)?.[1], rs = sim?.risk_scenario?.at(-1)?.[1];
  const moved = (sim?.variables ?? []).filter((v: any) => Math.abs(v.difference) / (Math.abs(v.baseline_end) + 1e-6) > 0.015)
    .sort((x: any, y: any) => Math.abs(y.difference) / (Math.abs(y.baseline_end) + 1e-6) - Math.abs(x.difference) / (Math.abs(x.baseline_end) + 1e-6));

  return (
    <Screen edges={inTab ? ['top'] : []} scrollEnabled={!touching3d}>
      {inTab ? null : <Stack.Screen options={{ title: '' }} />}
      <T v="h1">{inTab ? 'Your twin' : 'Your digital twin'}</T>
      <View style={{ position: 'relative' }}>
        <Twin3D systems={d.systems} selected={organSel} onSelect={setOrganSel} onInteract={setTouching3d} height={STAGE_H} />
        <OrganRail systems={d.systems} selected={organSel} onSelect={setOrganSel} />
      </View>
      <Row gap={14} style={{ justifyContent: 'center', flexWrap: 'wrap' }}>
        {[['In range', p.success], ['Watch', p.warn], ['Out of range', p.danger]].map(([t, c]) => (
          <Row key={t as string} gap={5}>
            <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: c as string }} />
            <T v="small" color={p.muted} style={{ fontSize: 11 }}>{t as string}</T>
          </Row>
        ))}
      </Row>
      <OrganPanel systems={d.systems} organ={organSel} onClear={() => setOrganSel(null)} />
      {organs.data?.organs?.length ? (
        <Section title="How each system is aging">
          <Card style={{ paddingVertical: 4 }}>
            {organs.data.organs.map((o: any, i: number) => {
              const accel = o.age_acceleration_years;
              const c = accel > 2 ? p.danger : accel < -2 ? p.success : p.muted;
              return (
                <Row key={o.organ} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                  <T v="body" style={{ flex: 1 }}>{o.label}</T>
                  <T v="small" style={{ width: 70, textAlign: 'right' }}>age {o.organ_age}</T>
                  <T v="num" style={{ fontSize: 14, width: 52, textAlign: 'right' }} color={c}>{accel > 0 ? '+' : ''}{accel}y</T>
                </Row>
              );
            })}
          </Card>
          <T v="small">Each system's age vs your real age, from your blood panel. A relative signal (which system ages faster), not a precise number.</T>
        </Section>
      ) : null}
      <T v="small">{d.about}</T>
      <Row style={{ flexWrap: 'wrap' }}>
        <Chip label={`PhenoAge ${d.risk_now.phenoage} at ${d.risk_now.age}`} fg={p.teal} bg={p.tealSoft} />
        <Chip label={`PREVENT 10-y ${d.risk_now.prevent_10y}% · 30-y ${d.risk_now.prevent_30y}%`} />
        {mir.data && mir.data.ok !== false ? <Chip label={`Twin fidelity ${Math.round(mir.data.fidelity * 100)}%`} fg={p.copper} bg={p.copperSoft} /> : null}
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
                <T v="small" color={preset === x.id ? p.onAccent : p.text}>{x.label.split(' (')[0]}</T>
              </Pressable>
            ))}
          </View>
          <Row>
            {[1, 5, 10].map((y) => (
              <Pressable key={y} onPress={() => setYears(y)} accessibilityRole="button"
                style={{ flex: 1, height: 36, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', backgroundColor: years === y ? p.teal : p.surface }}>
                <T v="body" color={years === y ? p.onAccent : p.text}>{y} year{y > 1 ? 's' : ''}</T>
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
            <Pressable onPress={() => setDrinking(false)} style={{ flex: 1 }}><Chip label="Non-drinking day" fg={!drinking ? p.onAccent : p.text} bg={!drinking ? p.teal : p.surfaceAlt} /></Pressable>
            <Pressable onPress={() => setDrinking(true)} style={{ flex: 1 }}><Chip label="Drinking day" fg={drinking ? p.onAccent : p.text} bg={drinking ? p.copper : p.surfaceAlt} /></Pressable>
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

      {tab === 'mirror' && mir.data?.ok === false ? (
        <Card><T v="small">{mir.data.reason}</T></Card>
      ) : null}
      {tab === 'mirror' && mir.data && mir.data.ok !== false ? (
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

      {proj.data ? (
        <Section title="Projected labs · next 90 days">
          <Card style={{ gap: space[2] }}>
            <T v="small">Your twin's projection from your latest real measurements and current routine, every 10 days. These are projections, not lab results; your next real report scores them and recalibrates the twin.</T>
            {proj.data.markers.map((m: any) => (
              <View key={m.key} style={{ gap: 2 }}>
                <Row>
                  <T v="label" style={{ flex: 1 }}>{m.label}</T>
                  <T v="small" color={p.faint}>now {m.anchor.value} {m.unit} · {m.anchor.source}, {m.anchor.date}</T>
                </Row>
                <T v="small">{m.points.filter((_: any, i: number) => i % 3 === 2).map((x: any) => `+${x.in_days} d: ${x.value} (${x.lo}–${x.hi})`).join('   ')}</T>
              </View>
            ))}
            {proj.data.needs_test?.length ? (
              <T v="small" color={p.faint}>Not projected until measured: {proj.data.needs_test.map((x: any) => x.label).join(', ')}.</T>
            ) : null}
          </Card>
        </Section>
      ) : null}
      <Section title={d.problem_count ? `Your body, system by system — ${d.problem_count} thing${d.problem_count === 1 ? '' : 's'} to watch` : 'Your body, system by system'}>
        <T v="small" color={p.muted}>Each system below is flagged against healthy reference ranges — green is in range, amber worth watching, red out of range. Wellness screening, not a diagnosis.</T>
        {d.systems.map((s: any) => {
          const sc = s.status === 'high' ? p.danger : s.status === 'watch' ? p.warn : p.success;
          const sbg = s.status === 'high' ? p.dangerSoft : s.status === 'watch' ? p.warnSoft : p.successSoft;
          const slabel = s.status === 'high' ? 'Out of range' : s.status === 'watch' ? 'Watch' : 'In range';
          return (
            <Card key={s.name} tone={s.status === 'high' ? 'copper' : undefined} style={{ gap: space[2] }}>
              <Row>
                <Icon name={s.icon ?? 'circle'} color={sc} />
                <T v="h3" style={{ flex: 1 }}>{s.name}</T>
                <Chip label={slabel} fg={sc} bg={sbg} />
              </Row>
              {s.problems.map((pr: any) => (
                <Row key={pr.key} style={{ alignItems: 'flex-start' }} gap={6}>
                  <Icon name={pr.severity === 'high' ? 'exclamationmark.triangle.fill' : 'eye.fill'} size={13} color={pr.severity === 'high' ? p.danger : p.warn} />
                  <View style={{ flex: 1 }}>
                    <T v="body" style={{ fontWeight: '600' }}>{pr.label} {pr.direction === 'low' ? 'low' : 'high'} · {Math.round(pr.value * 10) / 10} {pr.unit}</T>
                    <T v="small" color={p.muted}>{pr.detail}</T>
                  </View>
                </Row>
              ))}
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', rowGap: 8 }}>
                {s.variables.map((v: any) => (
                  <View key={v.key} style={{ width: '50%' }}>
                    <T v="small">{v.label}</T>
                    <T v="body" style={{ fontWeight: '600' }}>{Math.round(v.value * 10) / 10} <T v="small">{v.unit}</T></T>
                  </View>
                ))}
              </View>
            </Card>
          );
        })}
      </Section>
      <View style={{ height: space[2] }} />
    </Screen>
  );
}
