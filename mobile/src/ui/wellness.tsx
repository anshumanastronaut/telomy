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

/** Home block from the band alone (works when the Telomy server is unreachable). */
export function WellnessToday({ age }: { age?: number | null }) {
  const w = useWellness(age ?? null);
  const p = usePalette();
  if (w.loading) return null;
  const s = w.today.stress;
  return (
    <View style={{ gap: space[3] }}>
      <TodayHero w={w} coach={coachLine(w.recovery, w.sleep, w.last)} />
      {w.last ? <LastNightCard n={w.last} sleep={w.sleep} /> : null}
      <Row gap={space[3]}>
        <Card style={{ flex: 1 }} onPress={() => router.push('/wellness/stress')}>
          <Row gap={6}><Icon name="brain.head.profile" size={16} color={p.warn} /><T v="label">Stress</T></Row>
          <T v="num">{s.score == null ? '—' : s.score}</T>
          <T v="small">{s.minutes ? `${s.stressMin} stress · ${s.calmMin} calm min` : 'Wear the band in the day'}</T>
        </Card>
        <Card style={{ flex: 1 }} onPress={() => router.push('/wellness/recovery')}>
          <Row gap={6}><Icon name="figure.run" size={16} color={p.teal} /><T v="label">Heart fitness</T></Row>
          <T v="num">{w.vo2 ? Math.round(w.vo2) : '—'}</T>
          <T v="small">{w.restingHr ? `VO₂max est. · resting ${Math.round(w.restingHr)} bpm` : 'Needs a few calm minutes with the band'}</T>
        </Card>
      </Row>
    </View>
  );
}

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
        <T v="num" color="#fff" style={{ fontSize: size > 90 ? 28 : 22 }}>{center}</T>
        {sub ? <T v="small" color="rgba(255,255,255,0.65)" style={{ fontSize: 10, marginTop: -2 }}>{sub}</T> : null}
      </View>
      {label ? <T v="small" color="rgba(255,255,255,0.85)" style={{ fontWeight: '600', letterSpacing: 0.5 }}>{label.toUpperCase()}</T> : null}
    </Pressable>
  );
}

/** Dark hero: Recovery · Sleep · Strain + readiness + coach line + live heart pill. */
export function TodayHero({ w, coach }: { w: Wellness; coach: string }) {
  const p = usePalette();
  const b = useBand();
  const live = b.status?.state === 'streaming' && b.metrics?.hr;
  const rec = w.recovery.score, sl = w.sleep?.score ?? null, st = w.today.worn >= 10 ? w.today.strain : null;
  return (
    <LinearGradient colors={['#10231E', '#183A31', '#1F5C4E']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ borderRadius: radius.xl, padding: space[5], gap: space[4] }}>
      <Row>
        <View style={{ flex: 1 }}>
          <T v="label" color="rgba(255,255,255,0.6)">TODAY</T>
          <T v="h2" color="#fff">{rec == null ? 'Start tonight' : w.recovery.label}</T>
        </View>
        <Pressable onPress={() => router.push('/monitor')} accessibilityRole="button" accessibilityLabel="Live heart"
          style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill, backgroundColor: 'rgba(255,255,255,0.12)' }}>
          {live ? <BeatHeart lastBeatAt={b.lastBeatAt} size={14} /> : <Icon name="heart" size={14} color="rgba(255,255,255,0.7)" />}
          <T v="small" color="#fff" style={{ fontWeight: '600' }}>{live ? `${Math.round(b.metrics!.hr!)} bpm` : b.status?.state === 'connected' ? 'Band on' : 'Band off'}</T>
        </Pressable>
      </Row>
      <Row style={{ justifyContent: 'space-between' }}>
        <ScoreRing label="Recovery" value={rec} color={rec == null ? 'rgba(255,255,255,0.3)' : recoveryColor({ ...p, success: '#5FD39A', warn: '#F2B94B', danger: '#FF7A66' } as Palette, rec)}
          track="rgba(255,255,255,0.12)" center={rec == null ? '—' : `${rec}`} sub={rec == null ? undefined : '%'} onPress={() => router.push('/wellness/recovery')} />
        <ScoreRing label="Sleep" value={sl} color="#8FB8FF" track="rgba(255,255,255,0.12)" center={sl == null ? '—' : `${sl}`}
          sub={w.last ? fmtDur(w.last.tstMin) : undefined} onPress={() => router.push('/wellness/sleep')} />
        <ScoreRing label="Strain" value={st} max={21} color="#F0A36B" track="rgba(255,255,255,0.12)" center={st == null ? '—' : st.toFixed(1)}
          sub="of 21" onPress={() => router.push('/wellness/strain')} />
      </Row>
      {w.recovery.calibrating ? <T v="small" color="rgba(255,255,255,0.6)">{w.recovery.calibrating}</T> : null}
      <T v="body" color="rgba(255,255,255,0.92)">{coach}</T>
    </LinearGradient>
  );
}

/** Asleep/awake timeline for a night. */
export function Hypnogram({ n, height = 34 }: { n: Night; height?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  const N = n.hypnogram.length || 1;
  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)} style={{ gap: 4 }}>
      {w ? (
        <Svg width={w} height={height}>
          {n.hypnogram.map((v, i) => (
            <Rect key={i} x={(i / N) * w} y={v ? height * 0.3 : 0} width={Math.max(1, w / N + 0.5)} height={v ? height * 0.7 : height * 0.3}
              fill={v ? '#5B7FD6' : p.copper} opacity={v ? 0.9 : 0.75} />
          ))}
        </Svg>
      ) : <View style={{ height }} />}
      <Row style={{ justifyContent: 'space-between' }}>
        <T v="small">{fmtClock(n.start)}</T>
        <T v="small">■ asleep  <T v="small" color={p.copper}>■ awake</T></T>
        <T v="small">{fmtClock(n.end)}</T>
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

export function MiniMetric({ icon, label, value, sub, color }: { icon: any; label: string; value: string; sub?: string; color?: string }) {
  const p = usePalette();
  return (
    <View style={{ flex: 1, minWidth: '45%', gap: 2, padding: space[3], backgroundColor: p.surfaceAlt, borderRadius: radius.md }}>
      <Row gap={6}><Icon name={icon} size={14} color={color ?? p.teal} /><T v="small">{label}</T></Row>
      <T v="num" style={{ fontSize: 20 }}>{value}</T>
      {sub ? <T v="small" numberOfLines={2}>{sub}</T> : null}
    </View>
  );
}

/** Last-night summary card for Home. */
export function LastNightCard({ n, sleep }: { n: Night; sleep: Score | null }) {
  const p = usePalette();
  return (
    <Card onPress={() => router.push('/wellness/sleep')} accessibilityLabel="Last night">
      <Row>
        <Icon name="moon.stars" color="#5B7FD6" />
        <T v="label" style={{ flex: 1 }}>Last night</T>
        {sleep?.score != null ? <T v="small" color={p.teal} style={{ fontWeight: '600' }}>Sleep {sleep.score} · {sleep.label}</T> : null}
      </Row>
      <Row style={{ alignItems: 'baseline' }}>
        <T v="numLg">{fmtDur(n.tstMin)}</T>
        <T v="small">asleep · {Math.round(n.efficiency * 100)}% efficient</T>
      </Row>
      <Hypnogram n={n} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space[2] }}>
        <MiniMetric icon="heart" color={p.danger} label="Lowest HR" value={n.lowestHr ? `${Math.round(n.lowestHr)} bpm` : '—'}
          sub={n.lowestHrAt ? `at ${fmtClock(n.lowestHrAt)}${n.lowestHrPos != null && n.lowestHrPos > 0.66 ? ' (late)' : ''}` : undefined} />
        <MiniMetric icon="waveform.path.ecg" label="Overnight HRV" value={n.sleepRmssd ? `${Math.round(n.sleepRmssd)} ms` : '—'}
          sub={n.lateRmssd ? `${Math.round(n.lateRmssd)} ms by morning` : undefined} />
        <MiniMetric icon="lungs" color="#5B7FD6" label="Breathing" value={n.respRate ? `${n.respRate.toFixed(1)}/min` : '—'} sub="estimated from ECG" />
        <MiniMetric icon="arrow.down.heart" color={p.copper} label="HR drop" value={n.hrDropPct != null ? `${Math.round(n.hrDropPct)}%` : '—'} sub="bedtime → asleep" />
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
