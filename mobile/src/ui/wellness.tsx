// Wellness visuals: hero score rings, last-night card, overnight HR chart, zones, stress strip, contributors.
import { checkArchitecture } from '@/lib/sleeppatterns';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Path, Rect, Text as SvgText } from 'react-native-svg';
import { useReducedMotion } from 'react-native-reanimated';

import { radius, space, type, usePalette, type Palette, data, onInk } from '@/lib/theme';
import { coachLine, fmtClock, fmtDur, hrMax, useWellness, type Contributor, type MinuteRec, type Night, type Score, type Wellness } from '@/lib/wellness';
import { useBand } from '@/lib/band';
import { BeatHeart } from '@/ui/ecg';
import { Card, Icon, Row, T } from '@/ui/core';

const ACircle = Animated.createAnimatedComponent(Circle);

export function recoveryColor(p: Palette, v: number | null) {
  return v == null ? p.faint : v >= 67 ? p.success : v >= 34 ? p.warn : p.danger;
}

/** Ring that sweeps to its value on mount. `max` defaults to 100 (strain uses 21). */
export function ScoreRing({ value, max = 100, size = 96, stroke = 9, color, track, center, sub, onPress, label }: {
  value: number | null; max?: number; size?: number; stroke?: number; color: string; track: string; center: string; sub?: string; onPress?: () => void; label?: string;
}) {
  const r = (size - stroke) / 2, circ = 2 * Math.PI * r;
  const anim = useRef(new Animated.Value(0)).current;
  const reduced = useReducedMotion();
  useEffect(() => {
    const to = value == null ? 0 : Math.max(0, Math.min(1, value / max));
    if (reduced) { anim.setValue(to); return; }
    Animated.timing(anim, { toValue: to, duration: 700, easing: Easing.bezier(0.23, 1, 0.32, 1), useNativeDriver: false }).start();
  }, [value, max]);
  const offset = anim.interpolate({ inputRange: [0, 1], outputRange: [circ, 0] });
  return (
    <Pressable onPress={() => onPress?.()} accessibilityRole="button" accessibilityLabel={`${label ?? ''} ${center}`} style={{ alignItems: 'center', gap: 6 }}>
      <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
        <Svg width={size} height={size} style={{ position: 'absolute' }}>
          <Circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
          <ACircle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
            strokeDasharray={`${circ} ${circ}`} strokeDashoffset={offset as any} rotation={-90} origin={`${size / 2}, ${size / 2}`} />
        </Svg>
        <T v="num" color="#fff" style={{ fontSize: size > 140 ? 52 : size > 90 ? 28 : 22, lineHeight: size > 140 ? 60 : undefined }}>{center}</T>
        {sub ? <T v="small" color={onInk.secondary} style={{ fontSize: 11, marginTop: -2 }}>{sub}</T> : null}
      </View>
      {label ? <T v="small" color={onInk.primary} style={{ fontWeight: '600', letterSpacing: 0.5 }}>{label.toUpperCase()}</T> : null}
    </Pressable>
  );
}

/** Stage colours (one colour = one meaning, same on every screen). */
export const STAGE = [
  { k: 'Awake', c: data.temp }, { k: 'Light', c: data.sleep }, { k: 'Deep', c: '#4B5FD1' }, { k: 'REM', c: '#4FC8E3' },
];
const LANE = [0, 3, 1, 2]; // top → bottom: Awake, REM, Light, Deep (Oura/Apple order)

/** Hypnogram: 4 lanes (Awake · REM · Light · Deep) when the stage model ran, else asleep/awake. Hour ticks below. */
export function Hypnogram({ n, height }: { n: Night; height?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  const staged = !!n.stages?.length;
  const seq = staged ? n.stages! : n.hypnogram.map((v) => (v ? 1 : 0));   // -1 = no ECG (band disconnected): drawn as a gap
  const lanes = staged ? 4 : 2;
  const H = height ?? (staged ? 96 : 46), laneH = H / lanes, labelW = staged ? 44 : 0;
  const N = seq.length || 1;
  const runs: { v: number; a: number; b: number }[] = [];
  seq.forEach((v, i) => { const r = runs[runs.length - 1]; if (r && r.v === v) r.b = i + 1; else runs.push({ v, a: i, b: i + 1 }); });
  const plotW = Math.max(0, w - labelW);
  const X = (i: number) => labelW + (i / N) * plotW;
  const laneOf = (v: number) => (staged ? LANE.indexOf(v) : v ? 1 : 0);
  const col = (v: number) => (staged ? STAGE[v].c : v ? '#6F8CF0' : data.temp);
  const Y = (v: number) => laneOf(v) * laneH + laneH * 0.18;
  const hours: number[] = [];
  for (let t = Math.ceil(n.start / 3600) * 3600; t < n.start + N * n.epochSec; t += 3600) hours.push(t);
  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)} style={{ gap: 4 }}
      accessible accessibilityLabel={staged ? `Sleep stages: deep ${Math.round(n.deepMin ?? 0)} min, REM ${Math.round(n.remMin ?? 0)} min, light ${Math.round(n.lightMin ?? 0)} min` : 'Asleep and awake timeline'}>
      {w ? (
        <Svg width={w} height={H + 16}>
          {staged ? LANE.map((v, li) => (
            <SvgText key={v} x={0} y={li * laneH + laneH * 0.62} fontSize={11} fill={p.muted}>{STAGE[v].k}</SvgText>
          )) : null}
          {hours.map((t) => { const x = X((t - n.start) / n.epochSec); return <Line key={t} x1={x} x2={x} y1={0} y2={H} stroke={p.border} strokeWidth={1} />; })}
          {/* thin connectors between stages, like a step plot */}
          {runs.slice(1).map((r, k) => {
            const prev = runs[k];
            if (r.v < 0 || prev.v < 0) return null;
            return <Line key={'c' + k} x1={X(r.a)} x2={X(r.a)} y1={Y(prev.v) + laneH * 0.32} y2={Y(r.v) + laneH * 0.32} stroke={p.borderStrong} strokeWidth={1} />;
          })}
          {runs.map((r, k) => (r.v < 0
            ? <Rect key={k} x={X(r.a)} width={Math.max(2, X(r.b) - X(r.a))} y={0} height={H} fill={p.surfaceAlt} opacity={0.5} />
            : <Rect key={k} x={X(r.a)} width={Math.max(2, X(r.b) - X(r.a) - 0.5)} rx={3} y={Y(r.v)} height={laneH * 0.64} fill={col(r.v)} />
          ))}
          {hours.map((t) => { const x = X((t - n.start) / n.epochSec); return x > labelW + 10 && x < w - 10 ? <SvgText key={'l' + t} x={x} y={H + 13} fontSize={11} fill={p.muted} textAnchor="middle">{new Date(t * 1000).getHours()}</SvgText> : null; })}
        </Svg>
      ) : <View style={{ height: H + 16 }} />}
      {!staged ? (
        <Row gap={14}>
          <Row gap={5}><View style={{ width: 10, height: 6, borderRadius: 3, backgroundColor: '#6F8CF0' }} /><T v="small">Asleep</T></Row>
          <Row gap={5}><View style={{ width: 10, height: 6, borderRadius: 3, backgroundColor: data.temp }} /><T v="small">Awake</T></Row>
        </Row>
      ) : null}
    </View>
  );
}

/** Stage breakdown with typical adult ranges (Ohayon et al. 2004 normative sleep architecture). */
export function StageBreakdown({ n }: { n: Night }) {
  const p = usePalette();
  if (n.deepMin == null || n.remMin == null || n.lightMin == null) return null;
  const awake = n.wasoMin ?? 0;
  const tot = n.deepMin + n.remMin + n.lightMin + awake || 1;
  const rows = [
    { i: 0, min: awake, typical: '' },
    { i: 3, min: n.remMin, typical: '20–25 %' },
    { i: 1, min: n.lightMin, typical: '50–60 %' },
    { i: 2, min: n.deepMin, typical: '13–23 %' },
  ];
  const arch = checkArchitecture(n);
  return (
    <View style={{ gap: space[3] }}>
      {arch && !arch.ok ? (
        <T v="small" color={p.warn}>Stage minutes are uncertain tonight: {arch.flags.join('; ')}. Total sleep and timing are unaffected.</T>
      ) : null}
      <View style={{ flexDirection: 'row', height: 10, borderRadius: 5, overflow: 'hidden', gap: 2 }}>
        {rows.map((r) => (r.min > 0 ? <View key={r.i} style={{ flex: r.min, backgroundColor: STAGE[r.i].c }} /> : null))}
      </View>
      {rows.map((r) => (
        <Row key={r.i}>
          <View style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: STAGE[r.i].c }} />
          <T v="body" style={{ flex: 1 }}>{STAGE[r.i].k}</T>
          <T v="body" style={{ fontVariant: ['tabular-nums'] }}>{fmtDur(r.min)}</T>
          <T v="small" style={{ width: 92, textAlign: 'right' }}>{r.i === 0 ? '' : `${Math.round((100 * r.min) / Math.max(1, n.tstMin))}% · ${r.typical}`}</T>
        </Row>
      ))}
      <T v="small">
        {n.remLatencyMin != null ? `First REM ${Math.round(n.remLatencyMin)} min after falling asleep · ` : ''}{n.remCycles ? `${n.remCycles} sleep cycles · ` : ''}
        % of time asleep; typical ranges for adults. Estimated from heart rhythm, not a sleep study.
      </T>
    </View>
  );
}

/** Overnight 5-min heart rate with the lowest point marked. */
export function NightHrChart({ n, height = 120, kind = 'hr' }: { n: Night; height?: number; kind?: 'hr' | 'hrv' }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  const pts = kind === 'hr' ? n.hr5 : n.hrv5;
  if (pts.length < 3) return null;
  const ys = pts.map((q) => q[1]), lo = Math.min(...ys), hi = Math.max(...ys);
  const pad = (hi - lo) * 0.15 + 1, y0 = lo - pad, y1 = hi + pad;
  const t0 = pts[0][0], t1 = pts[pts.length - 1][0];
  const X = (t: number) => ((t - t0) / Math.max(1, t1 - t0)) * (w - 30) + 28, Y = (v: number) => height - 18 - ((v - y0) / (y1 - y0)) * (height - 26);
  const d = pts.map((q, i) => `${i ? 'L' : 'M'}${X(q[0]).toFixed(1)},${Y(q[1]).toFixed(1)}`).join(' ');
  const min = kind === 'hr' ? pts.reduce((a, b) => (b[1] < a[1] ? b : a)) : pts.reduce((a, b) => (b[1] > a[1] ? b : a));
  const col = kind === 'hr' ? p.danger : p.teal;
  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)}>
      {w ? (
        <Svg width={w} height={height}>
          {[lo, hi].map((v, i) => (
            <React.Fragment key={i}>
              <Line x1={28} x2={w} y1={Y(v)} y2={Y(v)} stroke={p.border} strokeDasharray="3 4" />
              <SvgText x={0} y={Y(v) + 4} fontSize={11} fill={p.muted}>{Math.round(v)}</SvgText>
            </React.Fragment>
          ))}
          <Path d={d} stroke={col} strokeWidth={2} fill="none" strokeLinejoin="round" />
          <Circle cx={X(min[0])} cy={Y(min[1])} r={4.5} fill={col} stroke={p.surface} strokeWidth={2} />
          <SvgText x={Math.min(w - 96, Math.max(30, X(min[0]) - 28))} y={Y(min[1]) + (kind === 'hr' ? 16 : -8)} fontSize={11} fill={p.text}>
            {kind === 'hr' ? `low ${Math.round(min[1])}` : `peak ${Math.round(min[1])}`} · {fmtClock(min[0])}
          </SvgText>
          <SvgText x={28} y={height - 2} fontSize={11} fill={p.muted}>{fmtClock(t0)}</SvgText>
          <SvgText x={w - 34} y={height - 2} fontSize={11} fill={p.muted}>{fmtClock(t1)}</SvgText>
        </Svg>
      ) : <View style={{ height }} />}
    </View>
  );
}

/** Vital tile with the change vs your normal (mean of previous nights) once 3 nights exist. */
export function MiniMetric({ icon, label, value, sub, color, delta, goodUp }: {
  icon: any; label: string; value: string; sub?: string; color?: string; delta?: number | null; goodUp?: boolean;
}) {
  const p = usePalette();
  const show = delta != null && Math.abs(delta) >= 0.5;
  const good = show && (goodUp ? delta! > 0 : delta! < 0);
  return (
    <View style={{ flex: 1, minWidth: '45%', gap: 2, padding: space[3], backgroundColor: p.surfaceAlt, borderRadius: radius.lg }}>
      <Row gap={6}><Icon name={icon} size={13} color={color ?? p.teal} /><T v="small" style={{ fontSize: 12 }}>{label}</T></Row>
      <T v="num" style={{ fontSize: 22 }}>{value}</T>
      {show ? <T v="small" color={good ? p.success : p.danger} style={{ fontSize: 12 }}>{delta! > 0 ? '▲' : '▼'} {Math.abs(delta!).toFixed(Math.abs(delta!) < 10 ? 1 : 0)} vs your normal</T>
        : sub ? <T v="small" style={{ fontSize: 12 }} numberOfLines={1}>{sub}</T> : null}
    </View>
  );
}

const avgOf = (h: Night[], k: keyof Night) => { const v = h.map((x) => x[k]).filter((x) => typeof x === 'number') as number[]; return v.length >= 3 ? v.reduce((a, b) => a + b, 0) / v.length : null; };

/** Last-night card: duration, score chip, timeline, four vitals with change vs your normal. */
export function LastNightCard({ n, sleep, history = [], embedded }: { n: Night; sleep: Score | null; history?: Night[]; embedded?: boolean }) {
  const p = usePalette();
  const prev = history.filter((h) => h.end < n.end).slice(-30);
  const d = (k: keyof Night) => { const m = avgOf(prev, k); const v = n[k]; return m != null && typeof v === 'number' ? v - m : null; };
  return (
    <Card onPress={embedded ? undefined : () => router.push('/wellness/sleep')} accessibilityLabel="Last night" style={{ borderRadius: radius.xl, padding: space[4], gap: space[3] }}>
      {embedded ? <T v="label">Night timeline</T> : <>
      <Row>
        <Icon name="moon.fill" size={14} color="#6F8CF0" />
        <T v="label" style={{ flex: 1 }}>Last night</T>
        <T v="small">{fmtClock(n.start)} – {fmtClock(n.end)}</T>
        <Icon name="chevron.right" size={11} color={p.faint} />
      </Row>
      <Row style={{ alignItems: 'flex-end' }}>
        <View style={{ flex: 1 }}>
          <T v="numLg" style={{ fontSize: 40, lineHeight: 46 }}>{fmtDur(n.tstMin)}</T>
          <T v="small">asleep · {Math.round(n.efficiency * 100)}% of time in bed</T>
        </View>
        {sleep?.score != null ? (
          <View style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill, backgroundColor: '#6F8CF022' }}>
            <T v="small" color="#4D67C9" style={{ fontWeight: '600' }}>Sleep {sleep.score} · {sleep.label}</T>
          </View>
        ) : null}
      </Row>
      </>}
      <Hypnogram n={n} />
      {n.stages?.length && n.deepMin != null && n.remMin != null ? (
        <Row gap={space[2]}>
          {[{ i: 2, m: n.deepMin }, { i: 3, m: n.remMin }, { i: 1, m: n.lightMin ?? 0 }].map((x) => (
            <View key={x.i} style={{ flex: 1, gap: 2, paddingVertical: 8, paddingHorizontal: 10, borderRadius: radius.md, backgroundColor: STAGE[x.i].c + '1F' }}>
              <T v="small" color={STAGE[x.i].c} style={{ fontWeight: '600', fontSize: 12 }}>{STAGE[x.i].k}</T>
              <T v="num" style={{ fontSize: 18 }}>{fmtDur(x.m)}</T>
            </View>
          ))}
        </Row>
      ) : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space[2] }}>
        <MiniMetric icon="heart.fill" color={p.danger} label="Lowest HR" value={n.lowestHr ? `${Math.round(n.lowestHr)} bpm` : '—'} delta={d('lowestHr')} goodUp={false}
          sub={n.lowestHrAt ? `at ${fmtClock(n.lowestHrAt)}${n.lowestHrPos != null && n.lowestHrPos > 0.66 ? ' · late' : ''}` : undefined} />
        <MiniMetric icon="waveform.path.ecg" label="Overnight HRV" value={n.sleepRmssd ? `${Math.round(n.sleepRmssd)} ms` : '—'} delta={d('sleepRmssd')} goodUp
          sub={n.lateRmssd ? `${Math.round(n.lateRmssd)} ms by morning` : undefined} />
        <MiniMetric icon="lungs.fill" color="#6F8CF0" label="Breathing" value={n.respRate ? `${n.respRate.toFixed(1)} /min` : '—'} delta={d('respRate')} goodUp={false} sub={n.respRate ? "from your devices" : "calibrating"} />
        <MiniMetric icon="arrow.down.heart.fill" color={p.copper} label="HR drop" value={n.hrDropPct != null ? `${Math.round(n.hrDropPct)}%` : '—'} delta={d('hrDropPct')} goodUp
          sub={n.hrDropPct != null ? 'bedtime → asleep' : 'too little time in bed'} />
      </View>
    </Card>
  );
}

export function ContributorList({ items }: { items: Contributor[] }) {
  const p = usePalette();
  return (
    <Card style={{ gap: space[3] }}>
      {items.map((c) => (
        <View key={c.key} style={{ gap: 4 }}>
          <Row>
            <T v="body" style={{ flex: 1, fontWeight: '600' }}>{c.label}</T>
            <T v="body">{c.value}</T>
          </Row>
          <View style={{ height: 6, borderRadius: 3, backgroundColor: p.surfaceAlt, overflow: 'hidden' }}>
            {c.score != null ? <View style={{ width: `${c.score}%`, height: 6, borderRadius: 3, backgroundColor: c.score >= 70 ? p.success : c.score >= 45 ? p.warn : p.danger }} /> : null}
          </View>
          <T v="small">{c.note}</T>
        </View>
      ))}
    </Card>
  );
}

const ZONE_COLORS = ['#9FC5B8', '#5FB08F', '#E2B04A', '#E58A4E', '#D3523F'];
/** Strain's equivalent of the sleep hypnogram: one column per hour of the day, stacked by heart-rate zone minutes
 *  (Z1 at the bottom → Z5 on top), in the zone colours. Column height = that hour's training load (zone-weighted
 *  minutes), so a hard 40-minute session towers over a gentle walk of the same length. */
export function StrainColumns({ mins, age }: { mins: MinuteRec[]; age: number }) {
  const p = usePalette();
  const max = hrMax(age);
  const hours = Array.from({ length: 24 }, () => [0, 0, 0, 0, 0]);
  for (const m of mins) {
    if (!m.hr || m.quality === 'poor' || m.quality === 'no_contact') continue;
    const f = m.hr / max; if (f < 0.5) continue;
    const h = new Date(m.ts).getHours(); hours[h][Math.min(4, Math.floor((f - 0.5) * 10))] += 1;
  }
  const load = hours.map((z) => z.reduce((s, v, i) => s + v * (i + 1), 0));
  const peak = Math.max(1, ...load), H = 120, now = new Date().getHours();
  return (
    <View style={{ gap: 6 }}>
      <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: H, gap: 2 }}>
        {hours.map((z, h) => (
          <View key={h} style={{ flex: 1, height: Math.max(2, (load[h] / peak) * H), borderRadius: 3, overflow: 'hidden', backgroundColor: p.surfaceAlt, flexDirection: 'column-reverse', opacity: h > now ? 0.35 : 1 }}>
            {load[h] ? z.map((v, i) => (v ? <View key={i} style={{ flex: v * (i + 1), backgroundColor: ZONE_COLORS[i] }} /> : null)) : null}
          </View>
        ))}
      </View>
      <Row>
        {['00', '06', '12', '18', '24'].map((l, i) => <T key={l} v="small" style={{ flex: i === 4 ? 0 : 1, fontSize: type.micro }} color={p.faint}>{l}</T>)}
      </Row>
    </View>
  );
}

export function ZoneBar({ zones }: { zones: number[] }) {
  const p = usePalette();
  const total = zones.reduce((a, b) => a + b, 0);
  return (
    <View style={{ gap: 6 }}>
      <View style={{ flexDirection: 'row', height: 12, borderRadius: 6, overflow: 'hidden', backgroundColor: p.surfaceAlt }}>
        {total ? zones.map((z, i) => (z ? <View key={i} style={{ flex: z, backgroundColor: ZONE_COLORS[i] }} /> : null)) : null}
      </View>
      <Row style={{ flexWrap: 'wrap' }} gap={10}>
        {zones.map((z, i) => <T key={i} v="small"><T v="small" color={ZONE_COLORS[i]}>●</T> Z{i + 1} {z} min</T>)}
      </Row>
    </View>
  );
}

export function StressStrip({ timeline }: { timeline: { ts: string; level: 0 | 1 | 2 }[] }) {
  const p = usePalette();
  if (!timeline.length) return <T v="small">Wear the band during the day to see your stress rhythm.</T>;
  const col = [p.success, p.surfaceAlt, p.warn];
  return (
    <View style={{ gap: 4 }}>
      <View style={{ flexDirection: 'row', height: 22, borderRadius: 4, overflow: 'hidden' }}>
        {timeline.map((m, i) => <View key={i} style={{ flex: 1, backgroundColor: col[m.level] }} />)}
      </View>
      <Row style={{ justifyContent: 'space-between' }}>
        <T v="small">{timeline[0].ts.slice(11)}</T>
        <T v="small"><T v="small" color={p.success}>■ calm</T>  <T v="small" color={p.warn}>■ stress</T></T>
        <T v="small">{timeline[timeline.length - 1].ts.slice(11)}</T>
      </Row>
    </View>
  );
}

/** Last 7 nights: sleep bars with HRV value. */
export function NightTrend({ nights }: { nights: Night[] }) {
  const p = usePalette();
  const last = nights.slice(-7);
  if (last.length < 2) return null;
  const max = Math.max(9 * 60, ...last.map((n) => n.tstMin));
  return (
    <Row style={{ alignItems: 'flex-end', height: 120 }} gap={8}>
      {last.map((n) => (
        <View key={n.id} style={{ flex: 1, alignItems: 'center', gap: 4 }}>
          <T v="small" style={{ fontSize: 11 }}>{n.sleepRmssd ? Math.round(n.sleepRmssd) : ''}</T>
          <View style={{ width: '70%', height: (n.tstMin / max) * 80, borderRadius: 4, backgroundColor: n.tstMin >= 420 ? '#5B7FD6' : p.copper }} />
          <T v="small" style={{ fontSize: 11 }}>{new Date(n.end * 1000).toLocaleDateString('en-GB', { weekday: 'narrow' })}</T>
        </View>
      ))}
    </Row>
  );
}
