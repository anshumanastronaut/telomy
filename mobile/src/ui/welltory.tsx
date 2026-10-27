// Welltory-style signature graphs, rendered on the member's OWN Telomy data — never a demo dashboard.
//  · SleepHrRainbow  — the overnight heart-rate line coloured by sleep stage (Welltory's "rainbow" sleep graph).
//  · StressTimeline  — today's minute-by-minute calm/stress timeline (the coping-curve / protected-minutes idea).
//  · MeasurementHistory — the trend of camera-HRV reads (lib/ppg → wellnessAppend('ppg')): HR + RMSSD over time.
// Each graph shows only what has data; HR/HRV are measured, the stress/energy/health shades are normative estimates.
import React, { useEffect, useState } from 'react';
import { LayoutChangeEvent, View } from 'react-native';
import Svg, { Circle, Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import { Band } from '../../modules/ky-ecg';
import { data, space, usePalette } from '@/lib/theme';
import { fmtClock, hrMax, type MinuteRec, type Night } from '@/lib/wellness-core';
import { Card, Row, T } from './core';
import { STAGE } from './wellness';

// 5 Karvonen heart-rate zones (same palette as the training screen's zone bars)
const ZONE_C = ['#9FC5B8', '#5FB08F', '#E2B04A', '#E58A4E', '#D3523F'];
const ZONE_MET = [3, 4.5, 6, 8.5, 11]; // representative METs per zone, for MET-minute totals

// stage value (0 wake, 1 light, 2 deep, 3 REM, -1 no data) → the shared stage colour
const stageColor = (v: number, fallback: string) => (v >= 0 && v < STAGE.length ? STAGE[v].c : fallback);

/** Overnight HR line, each segment tinted by the sleep stage you were in — the one-glance "how my night went" view.
 *  Needs the 4-stage model; without it the caller should fall back to the plain NightHrChart. */
export function SleepHrRainbow({ n, height = 140 }: { n: Night; height?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  const pts = n.hr5;
  if (!n.stages?.length || pts.length < 4) return null;

  const stageAt = (t: number) => {
    const i = Math.floor((t - n.start) / n.epochSec);
    return i >= 0 && i < n.stages!.length ? n.stages![i] : -1;
  };
  const ys = pts.map((q) => q[1]);
  const lo = Math.min(...ys), hi = Math.max(...ys);
  const pad = (hi - lo) * 0.15 + 1, y0 = lo - pad, y1 = hi + pad;
  const t0 = pts[0][0], t1 = pts[pts.length - 1][0];
  const left = 28, X = (t: number) => ((t - t0) / Math.max(1, t1 - t0)) * (w - left - 6) + left;
  const Y = (v: number) => height - 20 - ((v - y0) / (y1 - y0)) * (height - 30);
  const minPt = pts.reduce((a, b) => (b[1] < a[1] ? b : a));

  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)}
      accessible accessibilityLabel={`Overnight heart rate from ${Math.round(lo)} to ${Math.round(hi)} beats per minute, coloured by sleep stage`}>
      {w ? (
        <Svg width={w} height={height}>
          {[lo, hi].map((v, i) => (
            <React.Fragment key={i}>
              <Line x1={left} x2={w} y1={Y(v)} y2={Y(v)} stroke={p.border} strokeDasharray="3 4" />
              <SvgText x={0} y={Y(v) + 4} fontSize={11} fill={p.muted}>{Math.round(v)}</SvgText>
            </React.Fragment>
          ))}
          {/* one coloured segment per adjacent pair, tinted by the stage at the segment's start */}
          {pts.slice(1).map((q, i) => {
            const a = pts[i];
            const st = stageAt(a[0]);
            return <Line key={i} x1={X(a[0])} y1={Y(a[1])} x2={X(q[0])} y2={Y(q[1])}
              stroke={stageColor(st, p.danger)} strokeWidth={2.5} strokeLinecap="round" opacity={st < 0 ? 0.25 : 1} />;
          })}
          <Circle cx={X(minPt[0])} cy={Y(minPt[1])} r={4.5} fill={p.danger} stroke={p.surface} strokeWidth={2} />
          <SvgText x={Math.min(w - 96, Math.max(left, X(minPt[0]) - 28))} y={Y(minPt[1]) + 16} fontSize={11} fill={p.text}>
            low {Math.round(minPt[1])} · {fmtClock(minPt[0])}
          </SvgText>
          <SvgText x={left} y={height - 3} fontSize={11} fill={p.muted}>{fmtClock(t0)}</SvgText>
          <SvgText x={w - 34} y={height - 3} fontSize={11} fill={p.muted}>{fmtClock(t1)}</SvgText>
        </Svg>
      ) : <View style={{ height }} />}
      <Row gap={12} style={{ flexWrap: 'wrap', marginTop: space[2] }}>
        {STAGE.map((s) => (
          <Row key={s.k} gap={5}>
            <View style={{ width: 10, height: 4, borderRadius: 2, backgroundColor: s.c }} />
            <T v="small">{s.k}</T>
          </Row>
        ))}
      </Row>
    </View>
  );
}

type StressPoint = { ts: string; level: 0 | 1 | 2 };
const STRESS_C = ['#4FD08F', '#C98A1B', '#FF6B57']; // calm · elevated · high

/** Today's calm/stress timeline as a coloured band, with calm ("protected") vs stressed minutes called out. */
export function StressTimeline({ timeline, height = 44 }: { timeline: StressPoint[]; height?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  if (!timeline || timeline.length < 10) return null;
  const n = timeline.length;
  // collapse to runs of equal level so we draw a few rects, not hundreds
  const runs: { v: number; a: number; b: number }[] = [];
  timeline.forEach((pt, i) => { const r = runs[runs.length - 1]; if (r && r.v === pt.level) r.b = i + 1; else runs.push({ v: pt.level, a: i, b: i + 1 }); });
  const calm = timeline.filter((x) => x.level === 0).length;
  const high = timeline.filter((x) => x.level === 2).length;
  const X = (i: number) => (i / n) * w;
  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)} style={{ gap: space[2] }}
      accessible accessibilityLabel={`Stress timeline: ${calm} calm minutes, ${high} high-stress minutes of ${n}`}>
      {w ? (
        <Svg width={w} height={height}>
          {runs.map((r, k) => (
            <Rect key={k} x={X(r.a)} y={0} width={Math.max(1, X(r.b) - X(r.a))} height={height} rx={2} fill={STRESS_C[r.v]} opacity={r.v === 0 ? 0.55 : 0.95} />
          ))}
        </Svg>
      ) : <View style={{ height }} />}
      <Row gap={14} style={{ flexWrap: 'wrap' }}>
        <Row gap={5}><View style={{ width: 10, height: 6, borderRadius: 3, backgroundColor: STRESS_C[0] }} /><T v="small">{calm} calm min</T></Row>
        <Row gap={5}><View style={{ width: 10, height: 6, borderRadius: 3, backgroundColor: STRESS_C[2] }} /><T v="small">{high} high-stress min</T></Row>
      </Row>
    </View>
  );
}

type PpgRec = { t: number; hr: number; rmssd: number; sdnn: number; stress?: number; energy?: number; health?: number; quality?: number };

/** A small multi-line trend from a numeric series, with the latest value marked. */
function TrendLine({ series, color, label, unit, p }: { series: number[]; color: string; label: string; unit: string; p: any }) {
  const [w, setW] = useState(0);
  const h = 56;
  if (series.length < 2) return null;
  const lo = Math.min(...series), hi = Math.max(...series), rng = hi - lo || 1;
  const X = (i: number) => (i / (series.length - 1)) * (w - 4) + 2;
  const Y = (v: number) => h - 8 - ((v - lo) / rng) * (h - 16);
  const d = series.map((v, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
  const last = series[series.length - 1];
  return (
    <View style={{ flex: 1 }}>
      <Row style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
        <T v="small" color={p.muted}>{label}</T>
        <T v="num" style={{ fontSize: 18, color }}>{Math.round(last)}<T v="small" color={p.muted}> {unit}</T></T>
      </Row>
      <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)}>
        {w ? (
          <Svg width={w} height={h}>
            <Path d={d} stroke={color} strokeWidth={2} fill="none" strokeLinejoin="round" strokeLinecap="round" />
            <Circle cx={X(series.length - 1)} cy={Y(last)} r={3.5} fill={color} />
          </Svg>
        ) : <View style={{ height: h }} />}
      </View>
    </View>
  );
}

/** Trend of the one-minute camera-HRV reads (HR + RMSSD), newest reads to the right. Hidden until there are 2+. */
export function MeasurementHistory() {
  const p = usePalette();
  const [recs, setRecs] = useState<PpgRec[] | null>(null);
  useEffect(() => {
    let live = true;
    Band.wellnessRead('ppg', 60).then((r) => { if (live) setRecs((r as PpgRec[]).filter((x) => x.hr).slice(-20)); }).catch(() => { if (live) setRecs([]); });
    return () => { live = false; };
  }, []);
  if (!recs || recs.length < 2) return null;
  const hr = recs.map((r) => r.hr);
  const rmssd = recs.map((r) => r.rmssd).filter((x) => x != null);
  return (
    <Card style={{ gap: space[4] }}>
      <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <T v="h3">Your measurements</T>
        <T v="small" color={p.muted}>{recs.length} reads</T>
      </Row>
      <Row gap={space[5]} style={{ alignItems: 'flex-start' }}>
        <TrendLine series={hr} color={data.heart} label="Heart rate" unit="bpm" p={p} />
        {rmssd.length >= 2 ? <TrendLine series={rmssd} color={data.hrv} label="HRV (RMSSD)" unit="ms" p={p} /> : null}
      </Row>
    </Card>
  );
}

const batteryColor = (v: number) => (v >= 66 ? data.activity : v >= 33 ? data.stress : data.heart);

/** Welltory-style "Energy / body battery" through the day: a filled curve that drains with exertion and recharges when
 *  calm or asleep. The series is modelled from the person's own heart rate / HRV / sleep (see energyCurve). */
export function EnergyCurve({ curve, height = 150 }: { curve: { t: number; v: number }[]; height?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  if (!curve || curve.length < 3) return null;
  const now = curve[curve.length - 1].v;
  const t0 = curve[0].t, t1 = curve[curve.length - 1].t;
  const left = 26, X = (t: number) => ((t - t0) / Math.max(1, t1 - t0)) * (w - left - 6) + left;
  const Y = (v: number) => height - 20 - (v / 100) * (height - 30);
  const line = curve.map((c, i) => `${i ? 'L' : 'M'}${X(c.t).toFixed(1)},${Y(c.v).toFixed(1)}`).join(' ');
  const area = `${line} L${X(t1).toFixed(1)},${Y(0).toFixed(1)} L${X(t0).toFixed(1)},${Y(0).toFixed(1)} Z`;
  const col = batteryColor(now);
  return (
    <View style={{ gap: space[2] }}>
      <Row style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
        <T v="h3">Energy</T>
        <T v="num" style={{ color: col }}>{Math.round(now)}<T v="small" color={p.muted}> / 100</T></T>
      </Row>
      <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)}
        accessible accessibilityLabel={`Energy now ${Math.round(now)} of 100, modelled across today`}>
        {w ? (
          <Svg width={w} height={height}>
            {[0, 33, 66, 100].map((v) => (
              <React.Fragment key={v}>
                <Line x1={left} x2={w} y1={Y(v)} y2={Y(v)} stroke={p.border} strokeDasharray="3 4" />
                <SvgText x={0} y={Y(v) + 4} fontSize={10} fill={p.muted}>{v}</SvgText>
              </React.Fragment>
            ))}
            <Path d={area} fill={col} opacity={0.14} />
            <Path d={line} stroke={col} strokeWidth={2.5} fill="none" strokeLinejoin="round" strokeLinecap="round" />
            <Circle cx={X(t1)} cy={Y(now)} r={4} fill={col} stroke={p.surface} strokeWidth={2} />
            <SvgText x={left} y={height - 3} fontSize={11} fill={p.muted}>{fmtClock(t0)}</SvgText>
            <SvgText x={w - 34} y={height - 3} fontSize={11} fill={p.muted}>{fmtClock(t1)}</SvgText>
          </Svg>
        ) : <View style={{ height }} />}
      </View>
      <T v="small" color={p.faint}>Modelled from your heart rate, HRV and sleep — drains with exertion, recharges when you rest.</T>
    </View>
  );
}

/** Heart rate through a workout, drawn over its 5 Karvonen zone bands (Welltory's workout HR graph). Needs minute
 *  heart-rate data covering the session window; returns null when there isn't enough. */
export function WorkoutHrLine({ mins, start, end, age, height = 132 }: { mins: MinuteRec[]; start: number; end: number; age: number; height?: number }) {
  const p = usePalette();
  const [w, setW] = useState(0);
  const max = hrMax(age);
  const pts = mins
    .map((m) => ({ t: new Date(m.ts).getTime() / 1000, hr: m.hr }))
    .filter((q) => q.hr && q.t >= start - 60 && q.t <= end + 60)
    .sort((a, b) => a.t - b.t);
  if (pts.length < 4) return null;
  const t0 = pts[0].t, t1 = pts[pts.length - 1].t;
  const lo = Math.min(0.45 * max, ...pts.map((q) => q.hr)), hi = Math.max(max, ...pts.map((q) => q.hr));
  const left = 28, X = (t: number) => ((t - t0) / Math.max(1, t1 - t0)) * (w - left - 6) + left;
  const Y = (v: number) => height - 16 - ((v - lo) / (hi - lo)) * (height - 24);
  // zone band edges in bpm: 50/60/70/80/90/100 % of HRmax
  const edges = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0].map((f) => f * max);
  const line = pts.map((q, i) => `${i ? 'L' : 'M'}${X(q.t).toFixed(1)},${Y(q.hr).toFixed(1)}`).join(' ');
  return (
    <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)} accessible accessibilityLabel="Heart rate through the workout across training zones">
      {w ? (
        <Svg width={w} height={height}>
          {ZONE_C.map((c, i) => {
            const yTop = Y(Math.min(hi, edges[i + 1])), yBot = Y(Math.max(lo, edges[i]));
            return yBot > yTop ? <Rect key={i} x={left} y={yTop} width={w - left} height={yBot - yTop} fill={c} opacity={0.14} /> : null;
          })}
          <Path d={line} stroke={p.text} strokeWidth={2} fill="none" strokeLinejoin="round" strokeLinecap="round" />
          <SvgText x={0} y={Y(edges[1]) + 4} fontSize={10} fill={p.muted}>Z1</SvgText>
          <SvgText x={0} y={Y(edges[5]) + 10} fontSize={10} fill={p.muted}>Z5</SvgText>
          <SvgText x={left} y={height - 2} fontSize={11} fill={p.muted}>{fmtClock(t0)}</SvgText>
          <SvgText x={w - 34} y={height - 2} fontSize={11} fill={p.muted}>{fmtClock(t1)}</SvgText>
        </Svg>
      ) : <View style={{ height }} />}
    </View>
  );
}

/** Minutes in each heart-rate zone + the session's MET-minutes (Welltory's intensity breakdown). */
export function WorkoutZoneBreakdown({ zones }: { zones: number[] }) {
  const p = usePalette();
  const total = zones.reduce((a, b) => a + b, 0);
  if (!total) return null;
  const metMin = Math.round(zones.reduce((s, z, i) => s + z * ZONE_MET[i], 0));
  const labels = ['Z1 Very light', 'Z2 Light', 'Z3 Moderate', 'Z4 Hard', 'Z5 Max'];
  return (
    <View style={{ gap: space[2] }}>
      <View style={{ flexDirection: 'row', height: 10, borderRadius: 5, overflow: 'hidden', backgroundColor: p.surfaceAlt }}>
        {zones.map((z, i) => (z ? <View key={i} style={{ flex: z, backgroundColor: ZONE_C[i] }} /> : null))}
      </View>
      {zones.map((z, i) => (z ? (
        <Row key={i}>
          <View style={{ width: 9, height: 9, borderRadius: 2, backgroundColor: ZONE_C[i] }} />
          <T v="small" style={{ flex: 1 }}>{labels[i]}</T>
          <T v="small" color={p.muted}>{z} min</T>
        </Row>
      ) : null))}
      <T v="small" color={p.faint}>{metMin} MET-minutes · {Math.round((100 * ((zones[2] ?? 0) + (zones[3] ?? 0) + (zones[4] ?? 0))) / total)}% at moderate+ intensity</T>
    </View>
  );
}
