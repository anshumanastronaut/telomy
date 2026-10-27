// Camera-HRV measurement — the "put your fingertip on the back lens for a minute" read. The native module (KYPpg.swift)
// turns on the torch and streams per-frame average R/G/B; lib/ppg.ts (validated against the Welltory PPG dataset,
// HR MAE 0.37 bpm on accepted reads) turns the red-channel series into HR + HRV. The waveform drawn here is the REAL
// pulse signal; the trio (Stress / Energy / Health) are normative spot estimates, while HR and the raw HRV metrics
// are the hard numbers. Low-quality reads are rejected, not shown.
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import React, { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, View } from 'react-native';
import Svg, { Circle, Path, Polyline } from 'react-native-svg';

import { isAvailable, Ppg, Band, type PpgFrame } from '../../modules/ky-ecg';
import { analysePpg, scoresFromHrv, type HrvResult } from '@/lib/ppg';
import { data, radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, T } from '@/ui/core';

const DURATION = 60;        // seconds of good contact we aim for
const MIN_SECONDS = 30;     // allow an early finish after this much
const WAVE_SPAN = 6;        // seconds of signal shown in the live waveform

type Phase = 'intro' | 'measuring' | 'analysing' | 'result' | 'error';

/** Rolling contact check: with a fingertip over the lens + torch, the red channel sits high and dominates G/B.
 *  A dark or uncovered lens (low red) or a red that doesn't dominate means "no finger". */
function contactOk(r: number[], g: number[], b: number[]): boolean {
  if (r.length < 8) return true; // give it a moment before complaining
  const n = Math.min(30, r.length);
  const avg = (a: number[]) => a.slice(-n).reduce((s, x) => s + x, 0) / n;
  const rm = avg(r);
  return rm > 70 && rm > avg(g) * 1.15 && rm > avg(b) * 1.15;
}

export default function Measure() {
  const p = usePalette();
  const [phase, setPhase] = useState<Phase>('intro');
  const [elapsed, setElapsed] = useState(0);
  const [contact, setContact] = useState(true);
  const [wave, setWave] = useState<number[]>([]);
  const [result, setResult] = useState<HrvResult | null>(null);
  const [errMsg, setErrMsg] = useState('');

  // collected samples live in refs (frames arrive ~30 fps; we snapshot to state ~10 fps for the viz)
  const t = useRef<number[]>([]);
  const r = useRef<number[]>([]);
  const g = useRef<number[]>([]);
  const b = useRef<number[]>([]);
  const sub = useRef<{ remove: () => void } | null>(null);
  const startedAt = useRef(0);
  const finished = useRef(false);

  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => () => { stopCapture(); }, []); // clean up on unmount

  function reset() {
    t.current = []; r.current = []; g.current = []; b.current = [];
    setWave([]); setElapsed(0); setContact(true); setResult(null); setErrMsg(''); finished.current = false;
  }

  function stopCapture() {
    sub.current?.remove(); sub.current = null;
    try { Ppg.stop(); } catch {}
  }

  function start() {
    if (!isAvailable) { setErrMsg('Camera measurement needs the Telomy device build.'); setPhase('error'); return; }
    reset();
    setPhase('measuring');
    startedAt.current = Date.now();
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 650, easing: Easing.out(Easing.quad), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 650, easing: Easing.in(Easing.quad), useNativeDriver: true }),
      ]),
    ).start();
    sub.current = Ppg.onFrame((f: PpgFrame) => {
      if (f.error) {
        fail(f.error === 'denied' ? 'Camera access is off. Turn it on for Telomy in Settings to measure.'
           : f.error === 'no_camera' ? 'No camera available on this device.'
           : 'Could not open the camera.');
        return;
      }
      if (f.t == null || f.r == null) return;
      t.current.push(f.t); r.current.push(f.r); g.current.push(f.g ?? 0); b.current.push(f.b ?? 0);
    });
    try { Ppg.start(); } catch { fail('Could not start the camera.'); }
  }

  // snapshot loop: progress, contact, scrolling waveform — off the per-frame path to keep renders cheap
  useEffect(() => {
    if (phase !== 'measuring') return;
    const id = setInterval(() => {
      const secs = (Date.now() - startedAt.current) / 1000;
      setElapsed(secs);
      setContact(contactOk(r.current, g.current, b.current));
      // last WAVE_SPAN s of red, normalised 0..1, downsampled to ~120 points
      const tt = t.current, rr = r.current;
      if (tt.length > 4) {
        const cutoff = tt[tt.length - 1] - WAVE_SPAN * 1000;
        let i0 = tt.length - 1; while (i0 > 0 && tt[i0] > cutoff) i0--;
        const seg = rr.slice(i0);
        const step = Math.max(1, Math.floor(seg.length / 120));
        const ds: number[] = []; for (let i = 0; i < seg.length; i += step) ds.push(seg[i]);
        const lo = Math.min(...ds), hi = Math.max(...ds), rng = hi - lo || 1;
        setWave(ds.map((v) => (v - lo) / rng));
      }
      if (secs >= DURATION && !finished.current) finish();
    }, 100);
    return () => clearInterval(id);
  }, [phase]);

  function fail(msg: string) {
    if (finished.current) return;
    finished.current = true;
    stopCapture();
    setErrMsg(msg);
    setPhase('error');
  }

  function finish() {
    if (finished.current) return;
    finished.current = true;
    stopCapture();
    setPhase('analysing');
    // let the UI paint the "analysing" state before the (synchronous) maths
    setTimeout(() => {
      const res = analysePpg(t.current, r.current);
      if (!res || !res.hr || res.quality < 0.5) {
        setErrMsg(
          !res ? 'The reading was too short. Hold your fingertip still on the lens for the full minute.'
               : 'The signal was too noisy to trust. Keep still, cover the lens and flash fully, and try again.',
        );
        setPhase('error');
        return;
      }
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      setResult(res);
      setPhase('result');
      try {
        const s = scoresFromHrv(res.hr, res.rmssd, res.sdnn);
        Band.wellnessAppend('ppg', {
          t: Math.round(Date.now() / 1000), hr: Math.round(res.hr),
          rmssd: Math.round(res.rmssd), sdnn: Math.round(res.sdnn), pnn50: Math.round(res.pnn50),
          meanIbi: Math.round(res.meanIbi), quality: res.quality, durSec: res.durSec, ...s,
        });
      } catch {}
    }, 60);
  }

  const close = () => { stopCapture(); router.back(); };

  // ---------- render ----------
  if (phase === 'intro') return <Intro onStart={start} onClose={close} />;
  if (phase === 'error') return <ErrorView msg={errMsg} onRetry={start} onClose={close} />;
  if (phase === 'analysing') return <Analysing />;
  if (phase === 'result' && result) return <Result res={result} onAgain={start} onClose={close} />;

  // measuring
  const pct = Math.min(1, elapsed / DURATION);
  const canFinish = elapsed >= MIN_SECONDS;
  return (
    <Screen edges={['top', 'bottom']} scroll={false}>
      {/* non-scrolling Screen has no gutter, so pad here — otherwise the header sits in the corner under the edge-swipe zone */}
      <View style={{ flex: 1, paddingHorizontal: space[5], paddingTop: space[3], paddingBottom: space[4] }}>
        <Row style={{ justifyContent: 'center', alignItems: 'center' }}>
          <T v="label">{contact ? 'READING YOUR PULSE' : 'FIND YOUR PULSE'}</T>
        </Row>

        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <PulseRing pulse={pulse} pct={pct} contact={contact} color={data.heart} p={p} />
          <View style={{ height: space[6] }} />
          <T v="h2" style={{ textAlign: 'center' }}>
            {contact ? `${Math.max(0, Math.ceil(DURATION - elapsed))}s` : 'Cover the lens & flash'}
          </T>
          <T v="small" color={p.muted} style={{ textAlign: 'center', marginTop: space[1], paddingHorizontal: space[6] }}>
            {contact
              ? 'Rest your fingertip gently over the back camera and flash. Breathe normally and stay still.'
              : 'Place the pad of your finger flat across the back camera and flash until the screen glows red.'}
          </T>
          <View style={{ height: space[5] }} />
          <Waveform values={wave} color={contact ? data.heart : p.faint} p={p} />
        </View>

        {/* reachable bottom controls — the only close path while measuring (no tiny top-corner X) */}
        <View style={{ gap: space[2] }}>
          {canFinish ? <Button title="Finish now" onPress={finish} /> : null}
          <Button title="Cancel" kind="ghost" onPress={close} />
        </View>
      </View>
    </Screen>
  );
}

// ---------------- sub-views ----------------

function Intro({ onStart, onClose }: { onStart: () => void; onClose: () => void }) {
  const p = usePalette();
  const steps = [
    { icon: 'camera.fill' as const, text: 'Cover the back camera and flash with the pad of one fingertip.' },
    { icon: 'hand.raised.fill' as const, text: 'Hold still and breathe normally for about a minute.' },
    { icon: 'waveform.path.ecg' as const, text: 'We read your pulse from tiny colour changes under the skin.' },
  ];
  return (
    <Screen edges={['top', 'bottom']}>
      <Row style={{ justifyContent: 'flex-end' }}>
        <Pressable onPress={onClose} hitSlop={12}><Icon name="xmark" size={22} color={p.muted} /></Pressable>
      </Row>
      <View style={{ flex: 1, justifyContent: 'center' }}>
        <View style={{ alignItems: 'center', marginBottom: space[6] }}>
          <View style={{ width: 92, height: 92, borderRadius: 46, backgroundColor: data.heart + '22', alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="heart.fill" size={44} color={data.heart} />
          </View>
          <T v="h1" style={{ marginTop: space[4], textAlign: 'center' }}>Measure your heart</T>
          <T v="small" color={p.muted} style={{ textAlign: 'center', marginTop: space[2], paddingHorizontal: space[4] }}>
            A one-minute camera read of your heart rate and heart-rate variability — no extra hardware.
          </T>
        </View>
        {steps.map((s, i) => (
          <Card key={i} style={{ marginBottom: space[3] }}>
            <Row style={{ alignItems: 'center' }}>
              <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: p.surfaceAlt, alignItems: 'center', justifyContent: 'center', marginRight: space[3] }}>
                <Icon name={s.icon} size={20} color={p.teal} />
              </View>
              <T v="body" style={{ flex: 1 }}>{s.text}</T>
            </Row>
          </Card>
        ))}
      </View>
      <Button title="Start measurement" onPress={onStart} />
    </Screen>
  );
}

function Analysing() {
  const p = usePalette();
  return (
    <Screen edges={['top', 'bottom']} scroll={false}>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <Icon name="waveform.path.ecg" size={40} color={data.heart} />
        <T v="h2" style={{ marginTop: space[4] }}>Reading your beats…</T>
        <T v="small" color={p.muted} style={{ marginTop: space[1] }}>Finding every heartbeat in the signal</T>
      </View>
    </Screen>
  );
}

function ErrorView({ msg, onRetry, onClose }: { msg: string; onRetry: () => void; onClose: () => void }) {
  const p = usePalette();
  return (
    <Screen edges={['top', 'bottom']}>
      <Row style={{ justifyContent: 'flex-end' }}>
        <Pressable onPress={onClose} hitSlop={12}><Icon name="xmark" size={22} color={p.muted} /></Pressable>
      </Row>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: space[4] }}>
        <Icon name="exclamationmark.triangle.fill" size={40} color={data.stress} />
        <T v="h2" style={{ marginTop: space[4], textAlign: 'center' }}>Let's try that again</T>
        <T v="body" color={p.muted} style={{ marginTop: space[2], textAlign: 'center' }}>{msg}</T>
      </View>
      <Button title="Measure again" onPress={onRetry} />
    </Screen>
  );
}

function Result({ res, onAgain, onClose }: { res: HrvResult; onAgain: () => void; onClose: () => void }) {
  const p = usePalette();
  const s = scoresFromHrv(res.hr, res.rmssd, res.sdnn);
  const trio = [
    { label: 'Stress', v: s.stress, color: data.stress, hint: res.stress == null ? '' : s.stress < 40 ? 'Low' : s.stress < 70 ? 'Moderate' : 'High' },
    { label: 'Energy', v: s.energy, color: data.activity, hint: s.energy < 40 ? 'Low' : s.energy < 70 ? 'Fair' : 'Good' },
    { label: 'Health', v: s.health, color: data.hrv, hint: s.health < 40 ? 'Low' : s.health < 70 ? 'Fair' : 'Strong' },
  ];
  const metrics = [
    { label: 'Heart rate', v: Math.round(res.hr), unit: 'bpm' },
    { label: 'RMSSD', v: Math.round(res.rmssd), unit: 'ms' },
    { label: 'SDNN', v: Math.round(res.sdnn), unit: 'ms' },
    { label: 'pNN50', v: Math.round(res.pnn50), unit: '%' },
    { label: 'Mean IBI', v: Math.round(res.meanIbi), unit: 'ms' },
    { label: 'Beats', v: res.n, unit: '' },
  ];
  const qPct = Math.round(res.quality * 100);
  return (
    <Screen edges={['top', 'bottom']}>
      <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <T v="h3">Measurement</T>
        <Pressable onPress={onClose} hitSlop={12}><Icon name="xmark" size={22} color={p.muted} /></Pressable>
      </Row>

      {/* hero: heart rate */}
      <View style={{ alignItems: 'center', marginVertical: space[5] }}>
        <T v="display" color={data.heart}>{Math.round(res.hr)}</T>
        <T v="label">BEATS PER MINUTE</T>
      </View>

      {/* the trio */}
      <Row style={{ justifyContent: 'space-between', marginBottom: space[4] }}>
        {trio.map((x) => (
          <Card key={x.label} style={{ flex: 1, marginHorizontal: space[1], alignItems: 'center', paddingVertical: space[4] }}>
            <GaugeRing value={x.v} color={x.color} p={p} />
            <T v="small" color={p.muted} style={{ marginTop: space[2] }}>{x.label}</T>
            {!!x.hint && <T v="small" color={x.color}>{x.hint}</T>}
          </Card>
        ))}
      </Row>

      {/* raw metrics */}
      <Card style={{ marginBottom: space[3] }}>
        <Row style={{ flexWrap: 'wrap' }}>
          {metrics.map((m, i) => (
            <View key={m.label} style={{ width: '33.33%', paddingVertical: space[2], alignItems: 'center' }}>
              <T v="num">{m.v}{m.unit ? <T v="small" color={p.muted}> {m.unit}</T> : null}</T>
              <T v="small" color={p.muted}>{m.label}</T>
            </View>
          ))}
        </Row>
      </Card>

      <Row style={{ alignItems: 'center', marginBottom: space[4], paddingHorizontal: space[1] }}>
        <Icon name="checkmark.seal.fill" size={15} color={qPct >= 80 ? data.hrv : data.stress} />
        <T v="small" color={p.muted} style={{ marginLeft: space[2], flex: 1 }}>
          Signal quality {qPct}% over {res.durSec}s. Stress, Energy and Health are spot estimates; HR and HRV are measured.
        </T>
      </Row>

      <Button title="Measure again" kind="secondary" onPress={onAgain} />
      <View style={{ height: space[2] }} />
      <Button title="Done" onPress={onClose} />
    </Screen>
  );
}

// ---------------- primitives ----------------

function PulseRing({ pulse, pct, contact, color, p }: { pulse: Animated.Value; pct: number; contact: boolean; color: string; p: any }) {
  const size = 220, stroke = 10, radius = (size - stroke) / 2, circ = 2 * Math.PI * radius;
  const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.08] });
  const opacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.25, 0.5] });
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Animated.View style={{ position: 'absolute', width: size, height: size, borderRadius: size / 2, backgroundColor: color, opacity: contact ? opacity : 0.08, transform: [{ scale }] }} />
      <Svg width={size} height={size} style={{ position: 'absolute' }}>
        <Circle cx={size / 2} cy={size / 2} r={radius} stroke={p.surfaceAlt} strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2} cy={size / 2} r={radius} stroke={color} strokeWidth={stroke} fill="none"
          strokeDasharray={`${pct * circ} ${circ}`} strokeLinecap="round"
          rotation={-90} origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <Icon name="heart.fill" size={54} color={contact ? color : p.faint} />
    </View>
  );
}

function Waveform({ values, color, p }: { values: number[]; color: string; p: any }) {
  const w = 300, h = 72, pad = 4;
  if (values.length < 3) {
    return <View style={{ width: w, height: h, alignItems: 'center', justifyContent: 'center' }}><T v="small" color={p.faint}>…</T></View>;
  }
  const pts = values.map((v, i) => `${pad + (i / (values.length - 1)) * (w - 2 * pad)},${h - pad - v * (h - 2 * pad)}`).join(' ');
  return (
    <Svg width={w} height={h}>
      <Polyline points={pts} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
    </Svg>
  );
}

function GaugeRing({ value, color, p }: { value: number; color: string; p: any }) {
  const size = 72, stroke = 7, r = (size - stroke) / 2, circ = 2 * Math.PI * r;
  const v = Math.max(0, Math.min(100, value));
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute' }}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={p.surfaceAlt} strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none"
          strokeDasharray={`${(v / 100) * circ} ${circ}`} strokeLinecap="round"
          rotation={-90} origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <T v="num" style={{ fontSize: 20 }}>{Math.round(v)}</T>
    </View>
  );
}
