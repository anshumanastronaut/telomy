// Live ECG and HRV visuals: monitor-style sweep on ECG paper, beating heart, RR tachogram, HR trend, static strip.
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Animated, AppState, Easing, Pressable, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Path, Rect, Text as SvgText } from 'react-native-svg';
import { bandAvailable, ecg, useBand } from '@/lib/band';
import { fonts, usePalette } from '@/lib/theme';
import { Icon, T } from '@/ui/core';

const FS = 100;
/** Playback cushion: frames arrive every ~0.87 s; drawing this far behind real time gives a continuous sweep. */
export const CUSHION_S = 1.0;

/** ECG paper: 25 mm/s and 10 mm/mV (gain 1) — small squares 0.04 s / 0.1 mV, large 0.2 s / 0.5 mV. */
function Paper({ w, h, pxPerSec, color, strong }: { w: number; h: number; pxPerSec: number; color: string; strong: string }) {
  const small = pxPerSec * 0.04;
  const lines: React.ReactNode[] = [];
  for (let i = 0, x = 0; x <= w; i++, x = i * small) {
    lines.push(<Line key={`v${i}`} x1={x} x2={x} y1={0} y2={h} stroke={i % 5 === 0 ? strong : color} strokeWidth={i % 5 === 0 ? 0.8 : 0.4} />);
  }
  for (let i = 0, y = h / 2; y <= h; i++, y = h / 2 + i * small) {
    lines.push(<Line key={`h${i}`} x1={0} x2={w} y1={y} y2={y} stroke={i % 5 === 0 ? strong : color} strokeWidth={i % 5 === 0 ? 0.8 : 0.4} />);
    if (i) lines.push(<Line key={`H${i}`} x1={0} x2={w} y1={h - y} y2={h - y} stroke={i % 5 === 0 ? strong : color} strokeWidth={i % 5 === 0 ? 0.8 : 0.4} />);
  }
  return <>{lines}</>;
}

/**
 * Live sweep: the trace is redrawn ~30×/s from the ring buffer, `CUSHION_S` behind the newest sample,
 * erasing ahead of the cursor like a bedside monitor.
 */
export function EcgMonitor({ seconds = 5, height = 190, gain = 1, live }: { seconds?: number; height?: number; gain?: number; live: boolean }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  const [, tick] = useState(0);
  const raf = useRef<number | null>(null);
  useEffect(() => {
    if (!live) return;
    let last = 0;
    const loop = (ts: number) => {
      if (ts - last > 33) { last = ts; tick((x) => x + 1); }
      raf.current = requestAnimationFrame(loop);
    };
    const run = () => { if (raf.current == null) raf.current = requestAnimationFrame(loop); };
    const halt = () => { if (raf.current != null) cancelAnimationFrame(raf.current); raf.current = null; };
    // stop drawing in the background: a locked phone must not spend CPU on an invisible sweep
    const sub = AppState.addEventListener('change', (s) => (s === 'active' ? run() : halt()));
    if (AppState.currentState === 'active') run();
    return () => { sub.remove(); halt(); };
  }, [live]);

  const pxPerSec = w / seconds;
  const pxPerMv = pxPerSec * 0.4 * gain; // 10 mm/mV at 25 mm/s → 1 mV spans 0.4 s
  const W = seconds * FS;
  const now = Date.now() / 1000;
  const stale = !ecg.end || now - ecg.lastArrival > 3;
  let head = Math.floor((now - CUSHION_S - ecg.t0) * FS);
  head = Math.min(head, ecg.end - 1);
  const valid = (i: number) => i >= 0 && i < ecg.end && i >= ecg.end - ecg.data.length;
  const y = (v: number) => height / 2 - (v / 1000) * pxPerMv;
  let current = '';
  let previous = '';
  let cx = 0;
  if (!stale && w > 0 && head > 0) {
    const sweepStart = head - (head % W);
    cx = ((head % W) / W) * w;
    for (let i = sweepStart, k = 0; i <= head; i++, k++) {
      if (!valid(i)) continue;
      current += `${current ? 'L' : 'M'}${((k / W) * w).toFixed(1)},${y(ecg.at(i)).toFixed(1)}`;
    }
    const gap = Math.round(0.12 * FS);
    for (let i = head - W + gap + 1, k = (head % W) + gap + 1; i < sweepStart; i++, k++) {
      if (!valid(i)) continue;
      previous += `${previous ? 'L' : 'M'}${((k / W) * w).toFixed(1)},${y(ecg.at(i)).toFixed(1)}`;
    }
  }
  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)} style={{ height, borderRadius: 10, overflow: 'hidden', backgroundColor: p.surface }}
      accessible accessibilityLabel={stale ? 'ECG: waiting for signal' : 'Live ECG trace'}>
      {w > 0 ? (
        <Svg width={w} height={height}>
          <Paper w={w} h={height} pxPerSec={pxPerSec} color={p.copperSoft} strong={p.copper + '55'} />
          {previous ? <Path d={previous} stroke={p.text} strokeOpacity={0.35} strokeWidth={1.4} fill="none" strokeLinejoin="round" /> : null}
          {current ? <Path d={current} stroke={p.text} strokeWidth={1.8} fill="none" strokeLinejoin="round" /> : null}
          {current ? <Circle cx={cx} cy={y(ecg.at(head))} r={3.5} fill={p.teal} /> : null}
          {/* 1 mV calibration pulse */}
          <Path d={`M4,${height / 2} L8,${height / 2} L8,${height / 2 - pxPerMv} L18,${height / 2 - pxPerMv} L18,${height / 2} L22,${height / 2}`} stroke={p.muted} strokeWidth={1} fill="none" />
          <SvgText x={w - 6} y={height - 6} fill={p.muted} fontSize={10} textAnchor="end" fontFamily={fonts.body}>25 mm/s · {10 * gain} mm/mV · 0.5–40 Hz</SvgText>
          {stale ? <SvgText x={w / 2} y={height / 2 - 8} fill={p.muted} fontSize={14} textAnchor="middle" fontFamily={fonts.medium}>Waiting for ECG…</SvgText> : null}
        </Svg>
      ) : null}
    </View>
  );
}

/** Heart icon that pulses on every detected beat. */
export function BeatHeart({ lastBeatAt, size = 26 }: { lastBeatAt: number; size?: number }) {
  const p = usePalette();
  const s = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (!lastBeatAt) return;
    s.setValue(1.28);
    Animated.timing(s, { toValue: 1, duration: 320, easing: Easing.out(Easing.quad), useNativeDriver: true }).start();
  }, [lastBeatAt, s]);
  return (
    <Animated.View style={{ transform: [{ scale: s }] }}>
      <Icon name="heart.fill" size={size} color={p.danger} />
    </Animated.View>
  );
}

/** Beat-to-beat intervals (tachogram) — breathing shows up as a wave. */
export function Tachogram({ rr, height = 90 }: { rr: { t: number; rr: number }[]; height?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  const pts = rr.slice(-120);
  if (pts.length < 3) return <View style={{ height }}><T v="small">Collecting beats…</T></View>;
  const lo = Math.min(...pts.map((x) => x.rr)) - 20, hi = Math.max(...pts.map((x) => x.rr)) + 20;
  const x = (i: number) => (i / (pts.length - 1)) * w;
  const yv = (v: number) => height - 14 - ((v - lo) / (hi - lo)) * (height - 24);
  const d = pts.map((q, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${yv(q.rr).toFixed(1)}`).join('');
  return (
    <View onLayout={(e) => setW(e.nativeEvent.layout.width)} style={{ height }} accessibilityLabel={`Beat intervals from ${Math.round(lo + 20)} to ${Math.round(hi - 20)} milliseconds`}>
      {w > 0 ? (
        <Svg width={w} height={height}>
          <Line x1={0} x2={w} y1={height - 14} y2={height - 14} stroke={p.border} />
          <Path d={d} stroke={p.teal} strokeWidth={1.8} fill="none" />
          {pts.map((q, i) => <Circle key={i} cx={x(i)} cy={yv(q.rr)} r={1.6} fill={p.teal} />)}
          <SvgText x={0} y={10} fill={p.muted} fontSize={10} fontFamily={fonts.body}>{Math.round(hi - 20)} ms</SvgText>
          <SvgText x={0} y={height - 2} fill={p.muted} fontSize={10} fontFamily={fonts.body}>{Math.round(lo + 20)} ms · last {pts.length} beats</SvgText>
        </Svg>
      ) : null}
    </View>
  );
}

/** Heart-rate trend with min/max band. */
export function HrTrend({ hr, height = 110, minutes = 30 }: { hr: { t: number; hr: number }[]; height?: number; minutes?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  if (hr.length < 5) return <View style={{ height }}><T v="small">Heart-rate trend appears after a few seconds.</T></View>;
  const now = hr[hr.length - 1].t;
  const from = now - minutes * 60;
  const pts = hr.filter((q) => q.t >= from);
  const lo = Math.floor(Math.min(...pts.map((q) => q.hr)) - 3), hi = Math.ceil(Math.max(...pts.map((q) => q.hr)) + 3);
  const x = (t: number) => ((t - from) / (now - from || 1)) * w;
  const yv = (v: number) => height - 16 - ((v - lo) / (hi - lo || 1)) * (height - 26);
  const d = pts.map((q, i) => `${i ? 'L' : 'M'}${x(q.t).toFixed(1)},${yv(q.hr).toFixed(1)}`).join('');
  const area = `${d}L${x(now).toFixed(1)},${height - 16}L${x(pts[0].t).toFixed(1)},${height - 16}Z`;
  return (
    <View onLayout={(e) => setW(e.nativeEvent.layout.width)} style={{ height }}>
      {w > 0 ? (
        <Svg width={w} height={height}>
          <Path d={area} fill={p.danger} fillOpacity={0.08} />
          <Path d={d} stroke={p.danger} strokeWidth={2} fill="none" />
          <Circle cx={x(now)} cy={yv(pts[pts.length - 1].hr)} r={3.5} fill={p.danger} />
          <SvgText x={0} y={10} fill={p.muted} fontSize={10} fontFamily={fonts.body}>{hi} bpm</SvgText>
          <SvgText x={0} y={height - 2} fill={p.muted} fontSize={10} fontFamily={fonts.body}>{lo} bpm · last {Math.round((now - pts[0].t) / 60) || 1} min</SvgText>
        </Svg>
      ) : null}
    </View>
  );
}

/** Static ECG strip on paper (saved recordings), horizontally scrollable by the caller. */
export function EcgStrip({ samples, fs = FS, height = 170, gain = 1, pxPerSec = 100 }: { samples: number[]; fs?: number; height?: number; gain?: number; pxPerSec?: number }) {
  const p = usePalette();
  const w = (samples.length / fs) * pxPerSec;
  const pxPerMv = pxPerSec * 0.4 * gain;
  const step = Math.max(1, Math.floor(fs / 200));
  let d = '';
  for (let i = 0; i < samples.length; i += step) d += `${i ? 'L' : 'M'}${((i / fs) * pxPerSec).toFixed(1)},${(height / 2 - (samples[i] / 1000) * pxPerMv).toFixed(1)}`;
  return (
    <Svg width={w} height={height}>
      <Rect x={0} y={0} width={w} height={height} fill={p.surface} />
      <Paper w={w} h={height} pxPerSec={pxPerSec} color={p.copperSoft} strong={p.copper + '55'} />
      <Path d={d} stroke={p.text} strokeWidth={1.5} fill="none" strokeLinejoin="round" />
      {Array.from({ length: Math.floor(samples.length / fs) + 1 }, (_, s) => (
        <SvgText key={s} x={s * pxPerSec + 3} y={height - 4} fill={p.muted} fontSize={9} fontFamily={fonts.body}>{s}s</SvgText>
      ))}
    </Svg>
  );
}

/** Home card: live heart rate when the band is connected; one tap to the monitor. */
export function LiveBandCard({ onPress }: { onPress: () => void }) {
  const p = usePalette();
  const b = useBand();
  if (!bandAvailable) return null;
  const s = b.status;
  const live = s?.state === 'streaming' && b.metrics?.hr;
  const sub = live ? `HRV ${b.metrics?.hrvReliable && b.metrics.rmssd60 ? `${Math.round(b.metrics.rmssd60)} ms` : '–'} · ${s?.deviceName ?? 'ECG band'}`
    : s?.state === 'connected' ? 'Band connected · tap for live ECG'
    : s?.rememberedId ? `${s.rememberedName ?? 'ECG band'} · reconnects when you wear it` : 'Connect your ECG band for live ECG, HR and HRV';
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={live ? `Heart rate ${Math.round(b.metrics!.hr!)} bpm. Open live ECG` : 'Open live ECG'}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: p.surface, borderRadius: 14, padding: 14, borderWidth: 1, borderColor: p.border }}>
        {live ? <BeatHeart lastBeatAt={b.lastBeatAt} /> : <Icon name="waveform.path.ecg" color={p.teal} size={24} />}
        <View style={{ flex: 1 }}>
          <T v="h3">{live ? `${Math.round(b.metrics!.hr!)} bpm` : 'Live ECG'}</T>
          <T v="small">{sub}</T>
        </View>
        <Icon name="chevron.right" size={14} color={p.muted} />
      </View>
    </Pressable>
  );
}

/** Band entry points that work offline: live ECG, therapy capture, saved sessions. Shown even when the server is unreachable. */
export function BandTools({ compact = false }: { compact?: boolean }) {
  const p = usePalette();
  if (!bandAvailable) return null;
  return (
    <View style={{ gap: 8 }}>
      <LiveBandCard onPress={() => router.push('/monitor')} />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <Pressable onPress={() => router.push('/capture')} accessibilityRole="button" style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 8, padding: 12, borderRadius: 12, backgroundColor: p.copperSoft }}>
          <Icon name="record.circle" color={p.copper} size={20} /><T v="h3" color={p.copper}>Record therapy</T>
        </Pressable>
        {!compact ? (
          <Pressable onPress={() => router.push('/captures')} accessibilityRole="button" style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 8, padding: 12, borderRadius: 12, backgroundColor: p.surfaceAlt }}>
            <Icon name="folder" color={p.text} size={20} /><T v="h3">Saved sessions</T>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}
