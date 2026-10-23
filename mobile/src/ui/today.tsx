// Home "Today": one big thing (Recovery), state-tinted, with doorways to Sleep and Strain, last night and body tiles.
// Design notes: docs/design/TODAY_UI.md.
import * as Haptics from 'expo-haptics';
import { LinearGradient } from 'expo-linear-gradient';
import { router, useFocusEffect } from 'expo-router';
import { SFSymbol } from 'expo-symbols';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, View } from 'react-native';
import ReAnimated, { Easing as ReEasing, FadeInDown, useReducedMotion } from 'react-native-reanimated';
import Svg, { Circle, Defs, Line, LinearGradient as SvgGrad, Path, RadialGradient, Stop } from 'react-native-svg';

import { useBand } from '@/lib/band';
import { radius, space, type, usePalette, data, onInk } from '@/lib/theme';
import { coachLine, fmtClock, fmtDur, useWellness, type Wellness } from '@/lib/wellness';
import { phoneActivity } from '../../modules/ky-ecg';
import { HEALTH_AVAILABLE, HEALTH_LABEL, useHealth } from '@/lib/health';
import { useDevices } from '@/lib/devices';
import { BeatHeart } from '@/ui/ecg';
import { Icon, Row, T } from '@/ui/core';
import { LastNightCard, ScoreRing } from '@/ui/wellness';
import { VitalsGrid } from '@/ui/vitals';
import { useApi } from '@/lib/api';
import { useHomeLayout, type HomeWidget } from '@/lib/homeprefs';
import { DayTimeline } from '@/ui/trends';
import { DayTimelineVitals } from '@/ui/daytimeline';

const EASE_OUT = ReEasing.bezier(0.23, 1, 0.32, 1);

/** Narrow colour vocabulary: recovery state, sleep, strain, stress (same on every screen). */
export const C = {
  green: '#4FD08F', amber: '#F2B94B', red: data.heart, none: onInk.faint,
  sleep: data.sleep, strain: '#FF9A5A', stress: '#F2B94B',
  ink: '#0B1210', ink2: '#121D1A',
};
export const stateColor = (v: number | null) => (v == null ? C.none : v >= 67 ? C.green : v >= 34 ? C.amber : C.red);

function useCountUp(target: number | null, ms = 700) {
  const [v, setV] = useState(0);
  const a = useRef(new Animated.Value(0)).current;
  const reduced = useReducedMotion();
  useEffect(() => {
    if (target == null) return;
    if (reduced) { setV(target); return; }   // Reduce Motion: show the value, no count-up
    a.setValue(0);
    const id = a.addListener(({ value }) => setV(Math.round(value)));
    Animated.timing(a, { toValue: target, duration: ms, easing: Easing.bezier(0.23, 1, 0.32, 1), useNativeDriver: false }).start();
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
  const reduced = useReducedMotion();
  useEffect(() => {
    const to = value == null ? 0 : value / 100;
    if (reduced) { anim.setValue(to); return; }
    Animated.timing(anim, { toValue: to, duration: 700, easing: Easing.bezier(0.23, 1, 0.32, 1), useNativeDriver: false }).start();
  }, [value]);
  const offset = anim.interpolate({ inputRange: [0, 1], outputRange: [len, 0] });
  const shown = useCountUp(value);
  const tick = (v: number) => { const d = a0 + (sweep * v) / 100; const [x0, y0] = pt(d, r - 12); const [x1, y1] = pt(d, r + 12); return <Line x1={x0} y1={y0} x2={x1} y2={y1} stroke={onInk.faint} strokeWidth={2} />; };
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
        <Path d={arc(a0, a0 + sweep)} stroke={onInk.track} strokeWidth={stroke} fill="none" strokeLinecap="round" />
        <AnimatedPath d={arc(a0, a0 + sweep)} stroke="url(#arc)" strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={`${len} ${len}`} strokeDashoffset={offset as any} />
        {value != null ? <>{tick(33)}{tick(67)}</> : null}
      </Svg>
      {shown == null ? (
        // Empty state lives inside the ring's opening: an icon and a short label that always fits — never a sentence.
        <View style={{ position: 'absolute', top: size * 0.3, alignItems: 'center', gap: space[2], maxWidth: size * 0.62 }}>
          <Icon name="moon.stars" size={30} color={onInk.muted} />
          <T v="h3" color={onInk.secondary} style={{ textAlign: 'center' }} numberOfLines={1} adjustsFontSizeToFit>{label}</T>
        </View>
      ) : (
        <View style={{ position: 'absolute', top: size * 0.25, alignItems: 'center' }}>
          <Row gap={2} style={{ alignItems: 'flex-start' }}>
            <T v="display" color="#fff" style={{ fontSize: type.display + 8, lineHeight: type.display + 16, letterSpacing: -1.5 }}>{shown}</T>
            <T v="h2" color={onInk.muted} style={{ marginTop: 14 }}>%</T>
          </Row>
          <T v="h3" color={col} style={{ letterSpacing: 0.3 }} numberOfLines={1}>{label}</T>
        </View>
      )}
    </View>
  );
}

function Doorway({ icon, color, title, value, sub, ring, max, onPress }: {
  icon: SFSymbol; color: string; title: string; value: string; sub: string; ring: number | null; max: number; onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${title} ${value}`}
      style={({ pressed }) => ({ flex: 1, padding: 14, gap: 2, borderRadius: radius.xl, transform: [{ scale: pressed ? 0.97 : 1 }],
        backgroundColor: pressed ? onInk.track : onInk.hairline, borderWidth: 1, borderColor: onInk.hairline })}>
      <Row gap={5}>
        <Icon name={icon} size={11} color={color} />
        <T v="label" color={onInk.muted} style={{ fontSize: type.micro, flex: 1 }}>{title}</T>
        <Icon name="chevron.right" size={10} color={onInk.faint} />
      </Row>
      <Row style={{ alignItems: 'center' }}>
        <T v="num" color="#fff" style={{ fontSize: type.h1, lineHeight: 36, flex: 1 }}>{value}</T>
        <ScoreRing value={ring} max={max} size={30} stroke={4} color={color} track={onInk.track} center="" />
      </Row>
      <T v="small" color={onInk.muted} style={{ fontSize: type.micro + 1 }} numberOfLines={1}>{sub}</T>
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
    <LinearGradient colors={[C.ink, C.ink2]} style={{ borderRadius: 28, paddingHorizontal: space[4], paddingTop: space[4], paddingBottom: space[4], gap: space[3], overflow: 'hidden', borderWidth: 1, borderColor: onInk.hairline }}>
      <Row>
        <T v="label" color={onInk.muted} style={{ flex: 1 }}>Recovery</T>
        <Pressable onPress={() => router.push('/monitor')} accessibilityRole="button" accessibilityLabel="Live heart" hitSlop={8}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill, backgroundColor: onInk.hairline }}>
          {live ? <BeatHeart lastBeatAt={b.lastBeatAt} size={13} /> : <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: b.status?.state === 'connected' ? C.green : onInk.faint }} />}
          <T v="small" color="#fff" style={{ fontWeight: '600', fontSize: type.micro + 1 }}>{live ? `${Math.round(b.metrics!.hr!)} bpm` : b.status?.state === 'connected' ? 'Patch on' : 'Patch off'}</T>
        </Pressable>
      </Row>
      <Pressable onPress={() => router.push('/wellness/recovery')} accessibilityRole="button" accessibilityLabel={`Recovery ${rec ?? 'not available'}`} style={{ alignItems: 'center', marginTop: -4 }}>
        <RecoveryDial value={rec} label={rec == null ? 'No night yet' : w.recovery.label} />
      </Pressable>
      <T v="body" color={onInk.primary} style={{ textAlign: 'center', marginTop: -16, paddingHorizontal: space[2] }}>
        {rec == null ? 'Wear the patch, ring or WHOOP to bed. Telomy notices when you fall asleep and starts recording on its own.' : coachLine(w.recovery, w.sleep, w.last)}
      </T>
      {w.recovery.calibrating && rec != null ? (
        <View style={{ alignSelf: 'center', paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill, backgroundColor: onInk.hairline }}>
          <T v="small" color={onInk.muted} style={{ fontSize: type.micro }}>{w.recovery.calibrating}</T>
        </View>
      ) : null}
      <Row gap={space[2]} style={{ marginTop: space[1] }}>
        <Doorway icon="moon.fill" color={C.sleep} title="Sleep" value={sl == null ? '—' : `${sl}`} sub={w.last ? `${fmtDur(w.last.tstMin)} asleep` : 'No night yet'}
          ring={sl} max={100} onPress={() => router.push('/wellness/sleep')} />
        <Doorway icon="flame.fill" color={C.strain} title="Strain" value={st == null ? '—' : st.toFixed(1)} sub={st == null ? 'No wearable data today' : `${w.today.activeMin} active min`}
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
    <LinearGradient colors={[C.ink, C.ink2]} style={{ borderRadius: 28, padding: space[5], alignItems: 'center', gap: space[2], borderWidth: 1, borderColor: onInk.hairline }}>
      {dial ? <RecoveryDial value={value} label={label} /> : (
        <>
          <ScoreRing value={value} max={max} size={168} stroke={13} color={color} track={onInk.track}
            center={shown} sub={unit} />
          <T v="h3" color={color}>{label}</T>
        </>
      )}
      {sub ? <T v="small" color={onInk.secondary} style={{ textAlign: 'center', marginTop: dial ? -12 : 0 }}>{sub}</T> : null}
    </LinearGradient>
  );
}

function BodyTile({ icon, color, title, value, unit, sub, onPress }: { icon: SFSymbol; color: string; title: string; value: string; unit?: string; sub: string; onPress: () => void }) {
  const p = usePalette();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${title} ${value}`}
      style={({ pressed }) => ({ flex: 1, gap: 4, padding: space[4], borderRadius: radius.xl, backgroundColor: p.surface, opacity: pressed ? 0.9 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] })}>
      <Row gap={6}>
        <View style={{ width: 26, height: 26, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: color + '22' }}><Icon name={icon} size={13} color={color} /></View>
        <T v="label" style={{ flex: 1 }}>{title}</T>
        <Icon name="chevron.right" size={11} color={p.faint} />
      </Row>
      <Row gap={4} style={{ alignItems: 'baseline' }}>
        <T v="num" style={{ fontSize: type.h1 }}>{value}</T>
        {unit ? <T v="small">{unit}</T> : null}
      </Row>
      <T v="small" numberOfLines={2}>{sub}</T>
    </Pressable>
  );
}

/** Steps and activity from Apple Health (read-only). Asks to connect once. */
function ActivityCard() {
  const p = usePalette();
  const h = useHealth(14);
  const [busy, setBusy] = useState(false);
  if (!HEALTH_AVAILABLE) return null;        // no Android health integration yet — don't show "Connect Apple Health"
  if (h.connected === null) return null;
  if (!h.connected) {
    return (
      <View style={{ gap: space[2], padding: space[4], borderRadius: radius.xl, backgroundColor: p.surface }}>
        <Row gap={8}><Icon name="heart.text.square" size={16} color={data.heart} /><T v="label" style={{ flex: 1 }}>Apple Health</T></Row>
        <T v="body">Add your steps, workouts and activity to Strain and Recovery. Telomy only reads, never writes.</T>
        <Pressable disabled={busy} onPress={async () => { setBusy(true); await h.connect(); setBusy(false); }} accessibilityRole="button"
          style={({ pressed }) => ({ alignSelf: 'flex-start', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 999, backgroundColor: p.teal, opacity: busy ? 0.5 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] })}>
          <T v="small" color={p.onAccent} style={{ fontWeight: '600' }}>{busy ? 'Connecting…' : 'Connect Apple Health'}</T>
        </Pressable>
      </View>
    );
  }
  const t = h.today, week = h.data.slice(-7), max = Math.max(1, ...week.map((d) => d.steps ?? 0));
  return (
    <View style={{ gap: space[3], padding: space[4], borderRadius: radius.xl, backgroundColor: p.surface }}>
      <Row gap={8}><Icon name="figure.walk" size={15} color={data.activity} /><T v="label" style={{ flex: 1 }}>Activity</T><T v="small">Apple Health</T></Row>
      <Row style={{ alignItems: 'flex-end' }}>
        <View style={{ flex: 1 }}>
          <Row gap={4} style={{ alignItems: 'baseline' }}><T v="num" style={{ fontSize: type.h1 }}>{t?.steps != null ? Math.round(t.steps).toLocaleString('en-IN') : '—'}</T><T v="small">steps</T></Row>
          <T v="small">{[t?.distanceKm != null ? `${t.distanceKm.toFixed(1)} km` : null, t?.activeKcal != null ? `${Math.round(t.activeKcal)} kcal` : null,
            t?.exerciseMin != null ? `${Math.round(t.exerciseMin)} exercise min` : null].filter(Boolean).join(' · ') || 'No activity yet today'}</T>
          {h.stepsAvg7 != null ? <T v="small">7-day average {Math.round(h.stepsAvg7).toLocaleString('en-IN')}</T> : null}
        </View>
        <Row gap={4} style={{ alignItems: 'flex-end', height: 44 }}>
          {week.map((d) => <View key={d.date} style={{ width: 8, height: Math.max(3, ((d.steps ?? 0) / max) * 44), borderRadius: 3, backgroundColor: d === t ? data.activity : p.surfaceAlt }} />)}
        </Row>
      </Row>
    </View>
  );
}

/** No wearable night? The phone's motion coprocessor keeps 7 days of activity history even when Telomy wasn't
 *  running — the longest overnight still stretch is a fair in-bed estimate. Shown only as an estimate, never scored. */
function PhoneNight() {
  const p = usePalette();
  const [win, setWin] = useState<{ start: number; end: number } | null>(null);
  useEffect(() => {
    phoneActivity(20).then((segs) => {
      const night = segs.filter((s) => s.type === 'still').map((s) => {
        const a = new Date(s.start * 1000).getHours(), b = new Date(s.end * 1000).getHours();
        const overnight = a >= 20 || a < 6 || b < 12;                       // starts in the evening/night, ends by noon
        return overnight ? s : null;
      }).filter(Boolean) as { start: number; end: number }[];
      const best = night.sort((x, y) => (y.end - y.start) - (x.end - x.start))[0];
      if (best && best.end - best.start >= 3 * 3600) setWin(best);
    }).catch(() => {});
  }, []);
  if (!win) return null;
  const h = (win.end - win.start) / 3600;
  return (
    <View style={{ gap: space[1], padding: space[4], borderRadius: radius.xl, backgroundColor: p.surface }}>
      <Row gap={8}><Icon name="iphone" size={15} color={data.sleep} /><T v="label" style={{ flex: 1 }}>Last night · phone estimate</T></Row>
      <Row gap={4} style={{ alignItems: 'baseline' }}>
        <T v="num" style={{ fontSize: type.h1 }}>{Math.floor(h)}h {String(Math.round((h % 1) * 60)).padStart(2, '0')}m</T>
        <T v="small">{fmtClock(win.start)} – {fmtClock(win.end)}</T>
      </Row>
      <T v="small" color={p.muted}>Your phone was still this long overnight. Wear the patch, ring or WHOOP to bed for real sleep stages, heart rate and recovery.</T>
    </View>
  );
}

/** Live ring readings on Home when the smart ring is connected. */
function RingStrip() {
  const p = usePalette();
  const d = useDevices();
  const ring = d.devices.find((x) => x.id === 'ring');
  if (!ring?.connected) return null;
  const items = [
    { k: 'hr', label: 'Heart rate', unit: 'bpm', color: data.heart, icon: 'heart.fill' as const, v: d.live.hr?.value },
    { k: 'spo2', label: 'SpO₂', unit: '%', color: data.spo2, icon: 'drop.fill' as const, v: d.live.spo2?.value },
    { k: 'skinTemp', label: 'Skin temp', unit: '°C', color: data.temp, icon: 'thermometer.medium' as const, v: d.live.skinTemp?.value },
  ];
  return (
    <Pressable onPress={() => router.push('/ring')} accessibilityRole="button"
      style={({ pressed }) => ({ padding: space[4], gap: space[3], borderRadius: radius.xl, backgroundColor: p.surface, opacity: pressed ? 0.9 : 1 })}>
      <Row gap={6}><Icon name="circle.circle" size={15} color={data.temp} /><T v="label" style={{ flex: 1 }}>Smart ring{ring.detail.includes('%') ? ` · ${ring.detail.split('· ')[1]}` : ''}</T><Icon name="chevron.right" size={11} color={p.faint} /></Row>
      <Row gap={space[3]}>
        {items.map((it) => (
          <View key={it.k} style={{ flex: 1, gap: 2 }}>
            <Row gap={5}><Icon name={it.icon} size={12} color={it.color} /><T v="small" style={{ fontSize: type.micro }}>{it.label}</T></Row>
            <Row gap={3} style={{ alignItems: 'baseline' }}><T v="num" style={{ fontSize: type.title }}>{it.v != null ? (it.k === 'skinTemp' ? it.v.toFixed(1) : Math.round(it.v)) : '—'}</T><T v="small" style={{ fontSize: type.micro }}>{it.unit}</T></Row>
          </View>
        ))}
      </Row>
      <T v="small" style={{ fontSize: type.micro }}>Tap to take a fresh reading.</T>
    </Pressable>
  );
}

/** Home block from the band alone (works when the Telomy server is unreachable). */
export function WellnessToday({ age }: { age?: number | null }) {
  const w = useWellness(age ?? null);
  // refresh when coming back (e.g. after logging an event or finishing a session)
  const first = useRef(true);
  useFocusEffect(useCallback(() => { if (first.current) { first.current = false; return; } w.reload(); }, [w.reload]));
  const { enabledInOrder, loaded } = useHomeLayout();
  if (w.loading || !loaded) return null;
  const s = w.today.stress;

  // each Home widget → its block; the screen renders only the enabled ones, in the saved order (Settings → Home layout)
  const blocks: Record<HomeWidget, React.ReactNode> = {
    recovery: <TodayHero w={w} />,
    sleep: w.last ? <LastNightCard n={w.last} sleep={w.sleep} history={w.nights} /> : <PhoneNight />,
    vitals: <VitalsGrid />,
    timeline: <DayTimeline w={w} />,
    daytimeline: <DayTimelineVitals />,
    strain: <BodyTile icon="flame.fill" color={data.heart} title="Effort / strain" value={w.today.worn >= 10 ? (Math.round(w.today.strain * 10) / 10).toFixed(1) : '—'}
      sub={`${w.today.activeMin} active min today`} onPress={() => router.push('/wellness/strain')} />,
    stress: <BodyTile icon="waveform.path" color={data.stress} title="Stress" value={s.score == null ? '—' : `${s.score}`} unit={s.score == null ? undefined : '/100'}
      sub={s.minutes ? `${s.stressMin} stressed · ${s.calmMin} calm min` : 'Wear the band during the day'} onPress={() => router.push('/wellness/stress')} />,
    fitness: <BodyTile icon="figure.run" color={data.activity} title="Fitness" value={w.vo2 ? `${Math.round(w.vo2)}` : '—'} unit={w.vo2 ? 'VO₂max' : undefined}
      sub={w.restingHr ? `Resting HR ${Math.round(w.restingHr)} bpm` : 'Needs calm minutes with the band'} onPress={() => router.push('/wellness/recovery')} />,
    bioage: <BodyTile icon="hourglass" color={data.age} title="Biological age" value="View" sub="Blood · heart · muscle · fitness ages" onPress={() => router.push('/age')} />,
    longevity: <LongevityTile />,
    activity: <ActivityCard />,
    devices: <BodyTile icon="sensor.tag.radiowaves.forward" color={data.temp} title="Devices" value="Manage" sub={`Patch · ring · ${HEALTH_LABEL}`} onPress={() => router.push('/devices')} />,
  };

  return (
    <View style={{ gap: space[3] }}>
      {enabledInOrder.map((k, i) => (
        <ReAnimated.View key={k} entering={FadeInDown.duration(320).delay(Math.min(240, i * 40)).easing(EASE_OUT)}>{blocks[k]}</ReAnimated.View>
      ))}
      <Pressable onPress={() => router.push('/home-settings' as any)} accessibilityRole="button"
        style={{ alignSelf: 'center', paddingVertical: space[2] }}>
        <Row gap={6}><Icon name="slider.horizontal.3" size={13} color={onInk.muted} /><T v="small" color={onInk.muted}>Customise home</T></Row>
      </Pressable>
    </View>
  );
}

/** Blood age vs chronological, straight on the Home when enabled. */
function LongevityTile() {
  const bio = useApi<any>('/bioage');
  const h = bio.data?.headline;
  const chrono = bio.data?.chronological_age;
  return (
    <BodyTile icon="hourglass.bottomhalf.filled" color={data.age} title="Longevity"
      value={h?.age != null ? `${Math.round(h.age)}` : '—'} unit={h?.age != null ? 'yr' : undefined}
      sub={h?.age != null && chrono != null ? `${h.method} · you are ${Math.round(chrono)}` : 'Add a blood panel to see your blood age'}
      onPress={() => router.push('/age')} />
  );
}
