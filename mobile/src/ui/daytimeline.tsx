// Vitals timeline — the whole day on one clock: heart rate (and other vitals) with your events overlaid, from the
// unified longitudinal record (/vitals/day). Optional Home widget. Empty until the patch/ring/WHOOP has data for today.
import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';
import Svg, { Circle, Line, Path, Text as SvgText } from 'react-native-svg';

import { useApi } from '@/lib/api';
import { kindColor } from '@/lib/events';
import { radius, space, type, usePalette } from '@/lib/theme';
import { Card, Icon, Row, T } from '@/ui/core';


export function DayTimelineVitals() {
  const p = usePalette();
  const { data } = useApi<any>('/vitals/day');
  const hr = data?.metrics?.hr;
  const events: any[] = data?.events ?? [];

  const W = 320, H = 120, padL = 28, padB = 16, padT = 8;
  const start = data?.start, end = data?.end;
  const pts: [number, number][] = hr?.points ?? [];
  const body = (() => {
    if (!data) return null;
    if (!pts.length) {
      return <T v="small" color={p.muted}>No vitals recorded for today yet. Wear the patch, ring or WHOOP and this fills through the day — heart rate, HRV, SpO₂ — with your events on the same clock.</T>;
    }
    const ys = pts.map((q) => q[1]);
    const lo = Math.min(...ys) - 3, hi = Math.max(...ys) + 3;
    const x = (ts: number) => padL + ((ts - start) / (end - start)) * (W - padL - 6);
    const y = (v: number) => padT + (1 - (v - lo) / Math.max(1, hi - lo)) * (H - padT - padB);
    const d = pts.map((q, i) => `${i ? 'L' : 'M'}${x(q[0]).toFixed(1)},${y(q[1]).toFixed(1)}`).join(' ');
    const hours = [0, 6, 12, 18, 24].map((h) => start + h * 3600).filter((t) => t <= end);
    return (
      <View style={{ gap: 6 }}>
        <Svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
          {[lo, (lo + hi) / 2, hi].map((v, i) => (
            <React.Fragment key={i}>
              <Line x1={padL} y1={y(v)} x2={W - 6} y2={y(v)} stroke={p.surfaceAlt} strokeWidth={0.5} />
              <SvgText x={2} y={y(v) + 3} fontSize={7} fill={p.faint}>{Math.round(v)}</SvgText>
            </React.Fragment>
          ))}
          {hours.map((t, i) => (
            <SvgText key={i} x={x(t)} y={H - 4} fontSize={7} fill={p.faint} textAnchor="middle">{new Date(t * 1000).getHours()}h</SvgText>
          ))}
          <Path d={d} stroke={'#E05B6B'} strokeWidth={1.3} fill="none" />
          {events.map((e, i) => {
            const t = typeof e.ts === 'string' ? new Date(e.ts).getTime() / 1000 : e.ts;
            if (t < start || t > end) return null;
            return <Circle key={i} cx={x(t)} cy={padT + 2} r={2.6} fill={kindColor(e.kind)} />;
          })}
        </Svg>
        <Row style={{ flexWrap: 'wrap' }} gap={8}>
          <T v="small" color={p.muted}>{hr.sources?.join(', ')} · {Math.round((hr.coverage_s ?? 0) / 60)} min captured</T>
          {events.length ? <T v="small" color={p.muted}>· {events.length} events</T> : null}
        </Row>
      </View>
    );
  })();

  return (
      <Card style={{ gap: space[2] }}>
        <Row>
          <T v="label" style={{ flex: 1 }}>Your day so far</T>
          {data?.coverage_hours ? <T v="small" color={p.muted}>{data.coverage_hours} h</T> : null}
          <Pressable onPress={() => router.push('/log')} hitSlop={8} accessibilityRole="button" accessibilityLabel="Log an event"
            style={{ flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill, backgroundColor: p.tealSoft }}>
            <Icon name="plus" size={12} color={p.teal} />
            <T v="small" color={p.teal}>Log</T>
          </Pressable>
        </Row>
        {body}
      </Card>
  );
}
