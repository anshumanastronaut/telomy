// Home "Today": one big thing (Recovery), state-tinted, with doorways to Sleep and Strain, last night and body tiles.
// Design notes: docs/design/TODAY_UI.md.
import * as Haptics from 'expo-haptics';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { SFSymbol } from 'expo-symbols';
import React, { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, View } from 'react-native';
import Svg, { Circle, Defs, Line, LinearGradient as SvgGrad, Path, RadialGradient, Stop } from 'react-native-svg';

import { useBand } from '@/lib/band';
import { radius, space, usePalette } from '@/lib/theme';
import { coachLine, fmtDur, useWellness, type Wellness } from '@/lib/wellness';
import { BeatHeart } from '@/ui/ecg';
import { Icon, Row, T } from '@/ui/core';
import { LastNightCard, ScoreRing } from '@/ui/wellness';
import { DayTimeline } from '@/ui/trends';

/** Narrow colour vocabulary: recovery state, sleep, strain, stress (same on every screen). */
export const C = {
  green: '#4FD08F', amber: '#F2B94B', red: '#FF6B57', none: 'rgba(255,255,255,0.35)',
  sleep: '#8EA8FF', strain: '#FF9A5A', stress: '#F2B94B',
  ink: '#0B1210', ink2: '#121D1A',
};
export const stateColor = (v: number | null) => (v == null ? C.none : v >= 67 ? C.green : v >= 34 ? C.amber : C.red);

function useCountUp(target: number | null, ms = 1100) {
  const [v, setV] = useState(0);
  const a = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (target == null) return;
    a.setValue(0);
    const id = a.addListener(({ value }) => setV(Math.round(value)));
    Animated.timing(a, { toValue: target, duration: ms, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start();
    return () => a.removeListener(id);
  }, [target]);
  return target == null ? null : v;
}

const AnimatedPath = Animated.createAnimatedComponent(Path);

/** 270° dial, zone ticks at 33 and 67, gradient stroke in the state colour, number counts up. */
export function RecoveryDial({ value, size = 212, label }: { value: number | null; size?: number; label: string }) {
  const col = stateColor(value);
  const stroke = 14, r = size / 2 - stroke, c = size / 2;
  const a0 = 135, sweep = 270;
  const pt = (deg: number, rr = r) => [c + rr * Math.cos((deg * Math.PI) / 180), c + rr * Math.sin((deg * Math.PI) / 180)];
  const arc = (from: number, to: number) => {
    const [x0, y0] = pt(from), [x1, y1] = pt(to);
    return `M${x0},${y0} A${r},${r} 0 ${to - from > 180 ? 1 : 0} 1 ${x1},${y1}`;
  };
  const len = (Math.PI * 2 * r * sweep) / 360;
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(anim, { toValue: value == null ? 0 : value / 100, duration: 1200, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start();
  }, [value]);
  const offset = anim.interpolate({ inputRange: [0, 1], outputRange: [len, 0] });
  const shown = useCountUp(value);
  const tick = (v: number) => { const d = a0 + (sweep * v) / 100; const [x0, y0] = pt(d, r - 12); const [x1, y1] = pt(d, r + 12); return <Line x1={x0} y1={y0} x2={x1} y2={y1} stroke="rgba(255,255,255,0.35)" strokeWidth={2} />; };
  return (
    <View style={{ width: size, height: size * 0.86, alignItems: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute' }}>
        <Defs>
          <RadialGradient id="glow" cx="50%" cy="50%" r="50%">
            <Stop offset="0" stopColor={col} stopOpacity={value == null ? 0 : 0.28} />
            <Stop offset="1" stopColor={col} stopOpacity={0} />
          </RadialGradient>
          <SvgGrad id="arc" x1="0" y1="1" x2="1" y2="0">
            <Stop offset="0" stopColor={col} stopOpacity={0.55} />
            <Stop offset="1" stopColor={col} stopOpacity={1} />
          </SvgGrad>
        </Defs>
        <Circle cx={c} cy={c} r={c} fill="url(#glow)" />
        <Path d={arc(a0, a0 + sweep)} stroke="rgba(255,255,255,0.10)" strokeWidth={stroke} fill="none" strokeLinecap="round" />
        <AnimatedPath d={arc(a0, a0 + sweep)} stroke="url(#arc)" strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={`${len} ${len}`} strokeDashoffset={offset as any} />
        {tick(33)}{tick(67)}
      </Svg>
      <View style={{ position: 'absolute', top: size * 0.25, alignItems: 'center' }}>
        <Row gap={2} style={{ alignItems: 'flex-start' }}>
          <T v="display" color="#fff" style={{ fontSize: 64, lineHeight: 72 }}>{shown == null ? '—' : shown}</T>
          {shown != null ? <T v="h2" color="rgba(255,255,255,0.6)" style={{ marginTop: 14 }}>%</T> : null}
        </Row>
        <T v="h3" color={col} style={{ letterSpacing: 0.3 }}>{label}</T>
      </View>
    </View>
  );
}

function Doorway({ icon, color, title, value, sub, ring, max, onPress }: {
  icon: SFSymbol; color: string; title: string; value: string; sub: string; ring: number | null; max: number; onPress: () => void;
}) {
  return (
    <Pressable onPress={() => { Haptics.selectionAsync(); onPress(); }} accessibilityRole="button" accessibilityLabel={`${title} ${value}`}
      style={({ pressed }) => ({ flex: 1, padding: 14, gap: 2, borderRadius: radius.xl, transform: [{ scale: pressed ? 0.97 : 1 }],
        backgroundColor: pressed ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)' })}>
      <Row gap={5}>
        <Icon name={icon} size={11} color={color} />
        <T v="label" color="rgba(255,255,255,0.6)" style={{ fontSize: 10, flex: 1 }}>{title}</T>
        <Icon name="chevron.right" size={10} color="rgba(255,255,255,0.35)" />
      </Row>
      <Row style={{ alignItems: 'center' }}>
        <T v="num" color="#fff" style={{ fontSize: 30, lineHeight: 36, flex: 1 }}>{value}</T>
        <ScoreRing value={ring} max={max} size={30} stroke={4} color={color} track="rgba(255,255,255,0.12)" center="" />
      </Row>
      <T v="small" color="rgba(255,255,255,0.55)" style={{ fontSize: 12 }} numberOfLines={1}>{sub}</T>
    </Pressable>
  );
}

export function TodayHero({ w }: { w: Wellness }) {
  const b = useBand();
  const live = b.status?.state === 'streaming' && b.metrics?.hr;
  const rec = w.recovery.score;
  const sl = w.sleep?.score ?? null;
  const st = w.today.worn >= 10 ? Math.round(w.today.strain * 10) / 10 : null;
  return (
    <LinearGradient colors={[C.ink, C.ink2]} style={{ borderRadius: 28, paddingHorizontal: space[4], paddingTop: space[4], paddingBottom: space[4], gap: space[3], overflow: 'hidden', borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)' }}>
      <Row>
        <T v="label" color="rgba(255,255,255,0.6)" style={{ flex: 1 }}>Recovery</T>
        <Pressable onPress={() => router.push('/monitor')} accessibilityRole="button" accessibilityLabel="Live heart" hitSlop={8}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill, backgroundColor: 'rgba(255,255,255,0.08)' }}>
          {live ? <BeatHeart lastBeatAt={b.lastBeatAt} size={13} /> : <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: b.status?.state === 'connected' ? C.green : 'rgba(255,255,255,0.35)' }} />}
          <T v="small" color="#fff" style={{ fontWeight: '600', fontSize: 12 }}>{live ? `${Math.round(b.metrics!.hr!)} bpm` : b.status?.state === 'connected' ? 'Band connected' : 'Band off'}</T>
        </Pressable>
      </Row>
      <Pressable onPress={() => router.push('/wellness/recovery')} accessibilityRole="button" accessibilityLabel={`Recovery ${rec ?? 'not available'}`} style={{ alignItems: 'center', marginTop: -4 }}>
        <RecoveryDial value={rec} label={rec == null ? 'Wear the band tonight' : w.recovery.label} />
      </Pressable>
      <T v="body" color="rgba(255,255,255,0.88)" style={{ textAlign: 'center', marginTop: -16, paddingHorizontal: space[2] }}>{coachLine(w.recovery, w.sleep, w.last)}</T>
      {w.recovery.calibrating ? (
        <View style={{ alignSelf: 'center', paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill, backgroundColor: 'rgba(255,255,255,0.07)' }}>
          <T v="small" color="rgba(255,255,255,0.6)" style={{ fontSize: 11 }}>{w.recovery.calibrating}</T>
        </View>
      ) : null}
      <Row gap={space[2]} style={{ marginTop: space[1] }}>
        <Doorway icon="moon.fill" color={C.sleep} title="Sleep" value={sl == null ? '—' : `${sl}`} sub={w.last ? `${fmtDur(w.last.tstMin)} asleep` : 'No night yet'}
          ring={sl} max={100} onPress={() => router.push('/wellness/sleep')} />
        <Doorway icon="flame.fill" color={C.strain} title="Strain" value={st == null ? '—' : st.toFixed(1)} sub={st == null ? 'No band data today' : `${w.today.activeMin} active min`}
          ring={st} max={21} onPress={() => router.push('/wellness/strain')} />
      </Row>
    </LinearGradient>
  );
}

/** Dark hero for metric detail screens, continuous with Home. */
export function DetailHero({ value, max = 100, unit, label, sub, color, dial }: {
  value: number | null; max?: number; unit?: string; label: string; sub?: string; color: string; dial?: boolean;
}) {
  const tenths = useCountUp(value == null ? null : Math.round(max === 100 ? value : value * 10));
  const shown = tenths == null ? '—' : max === 100 ? `${tenths}` : (tenths / 10).toFixed(1);
  return (
    <LinearGradient colors={[C.ink, C.ink2]} style={{ borderRadius: 28, padding: space[5], alignItems: 'center', gap: space[2], borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)' }}>
      {dial ? <RecoveryDial value={value} label={label} /> : (
        <>
          <ScoreRing value={value} max={max} size={168} stroke={13} color={color} track="rgba(255,255,255,0.10)"
            center={shown} sub={unit} />
          <T v="h3" color={color}>{label}</T>
        </>
      )}
      {sub ? <T v="small" color="rgba(255,255,255,0.65)" style={{ textAlign: 'center', marginTop: dial ? -12 : 0 }}>{sub}</T> : null}
    </LinearGradient>
  );
}

function BodyTile({ icon, color, title, value, unit, sub, onPress }: { icon: SFSymbol; color: string; title: string; value: string; unit?: string; sub: string; onPress: () => void }) {
  const p = usePalette();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${title} ${value}`}
      style={({ pressed }) => ({ flex: 1, gap: 4, padding: space[4], borderRadius: radius.xl, backgroundColor: p.surface, borderWidth: 1, borderColor: p.border, opacity: pressed ? 0.9 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] })}>
      <Row gap={6}>
        <View style={{ width: 26, height: 26, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: color + '22' }}><Icon name={icon} size={13} color={color} /></View>
        <T v="label" style={{ flex: 1 }}>{title}</T>
        <Icon name="chevron.right" size={11} color={p.faint} />
      </Row>
      <Row gap={4} style={{ alignItems: 'baseline' }}>
        <T v="num" style={{ fontSize: 28 }}>{value}</T>
        {unit ? <T v="small">{unit}</T> : null}
      </Row>
      <T v="small" numberOfLines={2}>{sub}</T>
    </Pressable>
  );
}

/** Home block from the band alone (works when the Telomy server is unreachable). */
export function WellnessToday({ age }: { age?: number | null }) {
  const w = useWellness(age ?? null);
  if (w.loading) return null;
  const s = w.today.stress;
  return (
    <View style={{ gap: space[3] }}>
      <TodayHero w={w} />
      {w.last ? <LastNightCard n={w.last} sleep={w.sleep} history={w.nights} /> : null}
      <DayTimeline w={w} />
      <Row gap={space[3]} style={{ alignItems: 'stretch' }}>
        <BodyTile icon="waveform.path" color="#C98A1B" title="Stress" value={s.score == null ? '—' : `${s.score}`} unit={s.score == null ? undefined : '/100'}
          sub={s.minutes ? `${s.stressMin} stressed · ${s.calmMin} calm min` : 'Wear the band during the day'} onPress={() => router.push('/wellness/stress')} />
        <BodyTile icon="figure.run" color="#2F8F6B" title="Fitness" value={w.vo2 ? `${Math.round(w.vo2)}` : '—'} unit={w.vo2 ? 'VO₂max' : undefined}
          sub={w.restingHr ? `Resting HR ${Math.round(w.restingHr)} bpm` : 'Needs calm minutes with the band'} onPress={() => router.push('/wellness/recovery')} />
      </Row>
    </View>
  );
}
