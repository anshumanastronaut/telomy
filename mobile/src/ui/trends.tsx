// "Your day so far" timeline and trend charts with a shaded personal normal range.
import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import { radius, space, usePalette } from '@/lib/theme';
import { fmtClock, stressFor, type Wellness } from '@/lib/wellness';
import { Card, Icon, Row, T } from '@/ui/core';

const COL = { asleep: '#6F8CF0', active: '#FF9A5A', stress: '#F2B94B', calm: '#4FD08F' };
const toUnix = (ts: string) => new Date(ts).getTime() / 1000;

/** Wake → now: heart-rate line over state bands (asleep · calm · stress · active), with therapy sessions pinned. */
export function DayTimeline({ w }: { w: Wellness }) {
  const p = usePalette();
  const [width, setW] = useState(0);
  const now = Date.now() / 1000;
  const dayStart = new Date(); dayStart.setHours(6, 0, 0, 0);
  const t0 = w.last && now - w.last.end < 18 * 3600 ? Math.min(w.last.end, now - 1800) : Math.min(dayStart.getTime() / 1000, now - 3600);
  const t1 = now;
  const mins = w.today.minutes.filter((m) => toUnix(m.ts) >= t0);
  const levels = new Map(w.today.stress.timeline.map((x) => [x.ts, x.level]));
  const H = 92, top = 6, laneH = 14, chartH = H - laneH - 22;
  const X = (t: number) => ((t - t0) / Math.max(1, t1 - t0)) * width;
  const hrs = mins.map((m) => m.hr).filter(Boolean) as number[];
  const lo = hrs.length ? Math.min(...hrs) - 5 : 50, hi = hrs.length ? Math.max(...hrs) + 5 : 120;
  const Y = (v: number) => top + chartH - ((v - lo) / Math.max(1, hi - lo)) * chartH;
  let d = '', prevT = 0;
  for (const m of mins) {
    if (!m.hr) continue;
    const t = toUnix(m.ts);
    d += `${!d || t - prevT > 300 ? 'M' : 'L'}${X(t).toFixed(1)},${Y(m.hr).toFixed(1)}`;
    prevT = t;
  }
  const ticks: number[] = [];
  for (let t = Math.ceil(t0 / 10800) * 10800; t < t1; t += 10800) ticks.push(t);
  const stateOf = (m: (typeof mins)[number]) => m.sleep === 'asleep' ? 'asleep' : m.activity === 'active' || m.activity === 'moving' ? 'active'
    : levels.get(m.ts) === 2 ? 'stress' : levels.get(m.ts) === 0 ? 'calm' : null;
  return (
    <Card style={{ borderRadius: radius.xl, gap: space[3] }}>
      <Row>
        <Icon name="clock" size={14} color={p.teal} />
        <T v="label" style={{ flex: 1 }}>Your day so far</T>
        <T v="small">{fmtClock(t0)} – now</T>
      </Row>
      <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)}>
        {width ? (
          <Svg width={width} height={H}>
            {ticks.map((t) => <Line key={t} x1={X(t)} x2={X(t)} y1={top} y2={H - 18} stroke={p.border} />)}
            {mins.map((m) => { const s = stateOf(m); return s ? <Rect key={m.ts} x={X(toUnix(m.ts))} y={H - 18 - laneH} width={Math.max(1.5, width / ((t1 - t0) / 60))} height={laneH} fill={COL[s]} opacity={0.9} /> : null; })}
            <Rect x={0} y={H - 18 - laneH} width={width} height={laneH} rx={4} fill="none" stroke={p.border} />
            {d ? <Path d={d} stroke={p.danger} strokeWidth={1.8} fill="none" strokeLinejoin="round" /> : null}
            {w.sessionsToday.map((s) => (
              <React.Fragment key={s.t}>
                <Rect x={X(s.t)} y={top} width={Math.max(3, X(s.end) - X(s.t))} height={chartH} fill={p.copper} opacity={0.18} />
                <Circle cx={X(s.t)} cy={top + 4} r={4} fill={p.copper} />
              </React.Fragment>
            ))}
            <Circle cx={5} cy={top + 5} r={4.5} fill="#F2B94B" stroke={p.surface} strokeWidth={1.5} />
            {ticks.map((t) => <SvgText key={'l' + t} x={X(t)} y={H - 2} fontSize={10} fill={p.muted} textAnchor="middle">{fmtClock(t)}</SvgText>)}
          </Svg>
        ) : <View style={{ height: H }} />}
      </View>
      {mins.length ? (
        <Row style={{ flexWrap: 'wrap' }} gap={12}>
          {(['calm', 'stress', 'active', 'asleep'] as const).map((k) => (
            <Row key={k} gap={5}><View style={{ width: 10, height: 6, borderRadius: 3, backgroundColor: COL[k] }} /><T v="small" style={{ fontSize: 12 }}>{k[0].toUpperCase() + k.slice(1)}</T></Row>
          ))}
          <Row gap={5}><View style={{ width: 10, height: 2, backgroundColor: p.danger }} /><T v="small" style={{ fontSize: 12 }}>Heart rate</T></Row>
        </Row>
      ) : (
        <T v="small">Woke at {fmtClock(t0)}. Wear the band during the day to see your heart rate, calm and stress, activity and therapy sessions here.</T>
      )}
      {w.sessionsToday.length ? (
        <Pressable onPress={() => router.push('/captures')} accessibilityRole="button">
          <T v="small" color={p.copper}>● {w.sessionsToday.map((s) => `${s.label} ${fmtClock(s.t)}`).join(' · ')}</T>
        </Pressable>
      ) : null}
    </Card>
  );
}

/** Line of daily values with the personal normal range shaded (mean ± 1 SD of earlier values). */
export function TrendChart({ title, points, color, unit, band, decimals = 0, higherIsBetter }: {
  title: string; points: { t: number; v: number }[]; color: string; unit: string; band: { lo: number; hi: number; mean: number } | null;
  decimals?: number; higherIsBetter?: boolean;
}) {
  const p = usePalette();
  const [width, setW] = useState(0);
  const H = 120, padL = 4, padR = 34;
  const last = points[points.length - 1];
  const vs = points.map((q) => q.v).concat(band ? [band.lo, band.hi] : []);
  const lo = Math.min(...vs), hi = Math.max(...vs), span = Math.max(1e-6, hi - lo);
  const Y = (v: number) => 10 + (H - 30) * (1 - (v - lo) / span);
  const X = (i: number) => padL + (points.length > 1 ? (i / (points.length - 1)) * (width - padL - padR) : (width - padR) / 2);
  const d = points.map((q, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(q.v).toFixed(1)}`).join(' ');
  const delta = band && last ? last.v - band.mean : null;
  const good = delta != null && (higherIsBetter ? delta >= 0 : delta <= 0);
  return (
    <Card style={{ gap: space[2] }}>
      <Row style={{ alignItems: 'baseline' }}>
        <T v="label" style={{ flex: 1 }}>{title}</T>
        <T v="num" style={{ fontSize: 22 }}>{last ? last.v.toFixed(decimals) : '—'}</T>
        <T v="small"> {unit}</T>
      </Row>
      {band ? <T v="small" color={delta != null && Math.abs(delta) > (band.hi - band.mean) ? (good ? p.success : p.danger) : p.muted}>
        Your normal {band.lo.toFixed(decimals)}–{band.hi.toFixed(decimals)} {unit}{delta != null ? ` · today ${delta >= 0 ? '+' : ''}${delta.toFixed(decimals)}` : ''}
      </T> : <T v="small">Your normal range appears after 4 nights</T>}
      <View onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)}>
        {width && points.length ? (
          <Svg width={width} height={H}>
            {band ? <Rect x={padL} y={Y(band.hi)} width={width - padL - padR} height={Math.max(2, Y(band.lo) - Y(band.hi))} fill={color} opacity={0.12} rx={4} /> : null}
            {band ? <Line x1={padL} x2={width - padR} y1={Y(band.mean)} y2={Y(band.mean)} stroke={color} strokeOpacity={0.35} strokeDasharray="4 4" /> : null}
            {points.length > 1 ? <Path d={d} stroke={color} strokeWidth={2} fill="none" strokeLinejoin="round" /> : null}
            {points.map((q, i) => <Circle key={q.t} cx={X(i)} cy={Y(q.v)} r={i === points.length - 1 ? 4.5 : 2.5} fill={color} stroke={p.surface} strokeWidth={i === points.length - 1 ? 2 : 0} />)}
            <SvgText x={width - padR + 4} y={Y(hi) + 4} fontSize={10} fill={p.muted}>{hi.toFixed(decimals)}</SvgText>
            <SvgText x={width - padR + 4} y={Y(lo) + 4} fontSize={10} fill={p.muted}>{lo.toFixed(decimals)}</SvgText>
            <SvgText x={padL} y={H - 4} fontSize={10} fill={p.muted}>{new Date(points[0].t * 1000).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</SvgText>
            <SvgText x={width - padR} y={H - 4} fontSize={10} fill={p.muted} textAnchor="end">{new Date(last.t * 1000).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</SvgText>
          </Svg>
        ) : <View style={{ height: H }} />}
      </View>
    </Card>
  );
}
