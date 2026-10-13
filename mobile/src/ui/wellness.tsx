// Wellness visuals: hero score rings, last-night card, overnight HR chart, zones, stress strip, contributors.
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import { radius, space, usePalette, type Palette } from '@/lib/theme';
import { coachLine, fmtClock, fmtDur, useWellness, type Contributor, type Night, type Score, type Wellness } from '@/lib/wellness';
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
  useEffect(() => {
    Animated.timing(anim, { toValue: value == null ? 0 : Math.max(0, Math.min(1, value / max)), duration: 1100, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start();
  }, [value, max]);
  const offset = anim.interpolate({ inputRange: [0, 1], outputRange: [circ, 0] });
  return (
    <Pressable onPress={() => { Haptics.selectionAsync(); onPress?.(); }} accessibilityRole="button" accessibilityLabel={`${label ?? ''} ${center}`} style={{ alignItems: 'center', gap: 6 }}>
      <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
        <Svg width={size} height={size} style={{ position: 'absolute' }}>
          <Circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
          <ACircle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
            strokeDasharray={`${circ} ${circ}`} strokeDashoffset={offset as any} rotation={-90} origin={`${size / 2}, ${size / 2}`} />
        </Svg>
        <T v="num" color="#fff" style={{ fontSize: size > 140 ? 52 : size > 90 ? 28 : 22, lineHeight: size > 140 ? 60 : undefined }}>{center}</T>
        {sub ? <T v="small" color="rgba(255,255,255,0.65)" style={{ fontSize: 10, marginTop: -2 }}>{sub}</T> : null}
      </View>
      {label ? <T v="small" color="rgba(255,255,255,0.85)" style={{ fontWeight: '600', letterSpacing: 0.5 }}>{label.toUpperCase()}</T> : null}
    </Pressable>
  );
}

/** Asleep/awake timeline: merged runs as rounded bars, wake on a raised lane, hour ticks. */
export function Hypnogram({ n, height = 46 }: { n: Night; height?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  const N = n.hypnogram.length || 1;
  const runs: { v: number; a: number; b: number }[] = [];
  n.hypnogram.forEach((v, i) => { const r = runs[runs.length - 1]; if (r && r.v === v) r.b = i + 1; else runs.push({ v, a: i, b: i + 1 }); });
  const X = (i: number) => (i / N) * w;
  const hours: number[] = [];
  for (let t = Math.ceil(n.start / 3600) * 3600; t < n.start + N * n.epochSec; t += 3600) hours.push(t);
  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)} style={{ gap: 4 }}>
      {w ? (
        <Svg width={w} height={height + 14}>
          {hours.map((t) => { const x = X((t - n.start) / n.epochSec); return <Line key={t} x1={x} x2={x} y1={0} y2={height} stroke={p.border} strokeWidth={1} />; })}
          {runs.map((r, k) => (
            <Rect key={k} x={X(r.a) + 0.5} width={Math.max(2, X(r.b) - X(r.a) - 1)} rx={3}
              y={r.v ? height * 0.42 : height * 0.06} height={r.v ? height * 0.52 : height * 0.26}
              fill={r.v ? '#6F8CF0' : '#E0894F'} opacity={r.v ? 0.95 : 0.9} />
          ))}
          {hours.map((t) => { const x = X((t - n.start) / n.epochSec); return x > 18 && x < w - 18 ? <SvgText key={'l' + t} x={x} y={height + 12} fontSize={10} fill={p.muted} textAnchor="middle">{new Date(t * 1000).getHours()}</SvgText> : null; })}
        </Svg>
      ) : <View style={{ height: height + 14 }} />}
      <Row gap={14}>
        <Row gap={5}><View style={{ width: 10, height: 6, borderRadius: 3, backgroundColor: '#6F8CF0' }} /><T v="small">Asleep</T></Row>
        <Row gap={5}><View style={{ width: 10, height: 6, borderRadius: 3, backgroundColor: '#E0894F' }} /><T v="small">Awake</T></Row>
      </Row>
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
              <SvgText x={0} y={Y(v) + 4} fontSize={10} fill={p.muted}>{Math.round(v)}</SvgText>
            </React.Fragment>
          ))}
          <Path d={d} stroke={col} strokeWidth={2} fill="none" strokeLinejoin="round" />
          <Circle cx={X(min[0])} cy={Y(min[1])} r={4.5} fill={col} stroke={p.surface} strokeWidth={2} />
          <SvgText x={Math.min(w - 96, Math.max(30, X(min[0]) - 28))} y={Y(min[1]) + (kind === 'hr' ? 16 : -8)} fontSize={10} fill={p.text}>
            {kind === 'hr' ? `low ${Math.round(min[1])}` : `peak ${Math.round(min[1])}`} · {fmtClock(min[0])}
          </SvgText>
          <SvgText x={28} y={height - 2} fontSize={10} fill={p.muted}>{fmtClock(t0)}</SvgText>
          <SvgText x={w - 34} y={height - 2} fontSize={10} fill={p.muted}>{fmtClock(t1)}</SvgText>
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
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space[2] }}>
        <MiniMetric icon="heart.fill" color={p.danger} label="Lowest HR" value={n.lowestHr ? `${Math.round(n.lowestHr)} bpm` : '—'} delta={d('lowestHr')} goodUp={false}
          sub={n.lowestHrAt ? `at ${fmtClock(n.lowestHrAt)}${n.lowestHrPos != null && n.lowestHrPos > 0.66 ? ' · late' : ''}` : undefined} />
        <MiniMetric icon="waveform.path.ecg" label="Overnight HRV" value={n.sleepRmssd ? `${Math.round(n.sleepRmssd)} ms` : '—'} delta={d('sleepRmssd')} goodUp
          sub={n.lateRmssd ? `${Math.round(n.lateRmssd)} ms by morning` : undefined} />
        <MiniMetric icon="lungs.fill" color="#6F8CF0" label="Breathing" value={n.respRate ? `${n.respRate.toFixed(1)} /min` : '—'} delta={d('respRate')} goodUp={false} sub="from your ECG" />
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
          <T v="small" style={{ fontSize: 10 }}>{n.sleepRmssd ? Math.round(n.sleepRmssd) : ''}</T>
          <View style={{ width: '70%', height: (n.tstMin / max) * 80, borderRadius: 4, backgroundColor: n.tstMin >= 420 ? '#5B7FD6' : p.copper }} />
          <T v="small" style={{ fontSize: 10 }}>{new Date(n.end * 1000).toLocaleDateString('en-GB', { weekday: 'narrow' })}</T>
        </View>
      ))}
    </Row>
  );
}
