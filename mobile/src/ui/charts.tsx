// Charts per Design System §7: 1px strokes, grid at 40% border, primary series teal, bands at 15%,
// every chart captioned with n + freshness, and a "view as table" alternative.
import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import Svg, { Circle, G, Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import { usePalette } from '@/lib/theme';

import { Row, T } from './core';

export function Sparkline({ data, width = 80, height = 28, color }: { data: number[]; width?: number; height?: number; color?: string }) {
  const p = usePalette();
  if (!data || data.length < 2) return <View style={{ width, height }} />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((v, i) => [(i / (data.length - 1)) * (width - 4) + 2, height - 3 - ((v - min) / span) * (height - 6)]);
  const d = pts.map((pt, i) => `${i ? 'L' : 'M'}${pt[0].toFixed(1)},${pt[1].toFixed(1)}`).join(' ');
  const last = pts[pts.length - 1];
  return (
    <Svg width={width} height={height}>
      <Path d={d} stroke={color ?? p.teal} strokeWidth={1.25} fill="none" />
      <Circle cx={last[0]} cy={last[1]} r={2.5} fill={color ?? p.copper} />
    </Svg>
  );
}

type Pt = { x: string; y: number };

export function LineChart({
  points,
  height = 190,
  band,
  refBand,
  events = [],
  unit = '',
  caption,
  dots = false,
  decimals = 1,
}: {
  points: Pt[];
  height?: number;
  band?: [number | null, number | null] | null;
  refBand?: [number | null, number | null] | null;
  events?: { x: string; label: string }[];
  unit?: string;
  caption?: string;
  dots?: boolean;
  decimals?: number;
}) {
  const p = usePalette();
  const [w, setW] = useState(320);
  const [sel, setSel] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  if (!points.length) return <T v="small">No data in this window.</T>;
  const pad = { l: 34, r: 10, t: 12, b: 22 };
  const ys = points.map((q) => q.y);
  const extra = [band?.[0], band?.[1], refBand?.[0], refBand?.[1]].filter((v): v is number => v != null);
  let min = Math.min(...ys, ...extra);
  let max = Math.max(...ys, ...extra);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const spanY = (max - min) * 1.1;
  min -= (max - min) * 0.05;
  const xs = points.map((q) => new Date(q.x).getTime());
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs) || x0 + 1;
  const sx = (t: number) => pad.l + ((t - x0) / Math.max(x1 - x0, 1)) * (w - pad.l - pad.r);
  const sy = (v: number) => pad.t + (1 - (v - min) / spanY) * (height - pad.t - pad.b);
  const d = points.map((q, i) => `${i ? 'L' : 'M'}${sx(xs[i]).toFixed(1)},${sy(q.y).toFixed(1)}`).join(' ');
  const step = niceStep(spanY / 3);
  const ticks: number[] = [];
  for (let t = Math.ceil(min / step) * step; t <= min + spanY; t += step) ticks.push(t);
  const bandRect = (b: [number | null, number | null] | null | undefined, color: string, op: number) => {
    if (!b) return null;
    const lo = b[0] ?? min;
    const hi = b[1] ?? min + spanY;
    return <Rect x={pad.l} width={w - pad.l - pad.r} y={sy(hi)} height={Math.max(0, sy(lo) - sy(hi))} fill={color} opacity={op} />;
  };
  const s = sel != null ? points[sel] : null;
  return (
    <View onLayout={(e) => setW(e.nativeEvent.layout.width)} style={{ gap: 6 }}>
      {table ? (
        <View style={{ gap: 4 }}>
          {points
            .slice()
            .reverse()
            .slice(0, 40)
            .map((q) => (
              <Row key={q.x}>
                <T v="small" style={{ flex: 1 }}>
                  {q.x.slice(0, 10)}
                </T>
                <T v="body" style={{ fontVariant: ['tabular-nums'] }}>
                  {q.y.toFixed(decimals)} {unit}
                </T>
              </Row>
            ))}
        </View>
      ) : (
        <Pressable
          onPressIn={(e) => {
            const x = e.nativeEvent.locationX;
            let best = 0;
            xs.forEach((t, i) => {
              if (Math.abs(sx(t) - x) < Math.abs(sx(xs[best]) - x)) best = i;
            });
            setSel(best);
          }}
          accessibilityLabel={`Chart of ${points.length} values${unit ? ' in ' + unit : ''}`}>
          <Svg width={w} height={height}>
            {ticks.map((t, i) => (
              <G key={i}>
                <Line x1={pad.l} x2={w - pad.r} y1={sy(t)} y2={sy(t)} stroke={p.border} strokeWidth={1} opacity={0.4} />
                <SvgText x={pad.l - 6} y={sy(t) + 3} fontSize={9} fill={p.muted} textAnchor="end" fontFamily="Inter_400Regular">
                  {Math.abs(t) >= 10 || Number.isInteger(t) ? Math.round(t) : t.toFixed(decimals)}
                </SvgText>
              </G>
            ))}
            {bandRect(refBand, p.graphite, 0.08)}
            {bandRect(band, p.teal, 0.15)}
            {events.map((ev, i) => {
              const t = new Date(ev.x).getTime();
              if (t < x0 || t > x1) return null;
              return <Line key={i} x1={sx(t)} x2={sx(t)} y1={pad.t} y2={height - pad.b} stroke={p.copper} strokeWidth={1} strokeDasharray="2,3" opacity={0.6} />;
            })}
            <Path d={d} stroke={p.teal} strokeWidth={1.25} fill="none" />
            {(dots || points.length < 12) &&
              points.map((q, i) => <Circle key={i} cx={sx(xs[i])} cy={sy(q.y)} r={3} fill={p.surface} stroke={p.teal} strokeWidth={1.25} />)}
            {s ? (
              <G>
                <Line x1={sx(xs[sel!])} x2={sx(xs[sel!])} y1={pad.t} y2={height - pad.b} stroke={p.muted} strokeWidth={1} />
                <Circle cx={sx(xs[sel!])} cy={sy(s.y)} r={4} fill={p.copper} />
              </G>
            ) : null}
            <SvgText x={pad.l} y={height - 6} fontSize={9} fill={p.muted} fontFamily="Inter_400Regular">
              {points[0].x.slice(5, 10)}
            </SvgText>
            <SvgText x={w - pad.r} y={height - 6} fontSize={9} fill={p.muted} textAnchor="end" fontFamily="Inter_400Regular">
              {points[points.length - 1].x.slice(5, 10)}
            </SvgText>
          </Svg>
        </Pressable>
      )}
      <Row>
        <T v="small" style={{ flex: 1 }}>
          {s ? `${s.x.slice(0, 10)} · ${s.y.toFixed(decimals)} ${unit}` : caption ?? `n = ${points.length}`}
        </T>
        <Pressable onPress={() => setTable(!table)} hitSlop={8} accessibilityRole="button">
          <Text style={{ color: p.teal, fontSize: 12, fontFamily: 'Inter_600SemiBold' }}>{table ? 'View as chart' : 'View as table'}</Text>
        </Pressable>
      </Row>
    </View>
  );
}

export function Bars({ data, height = 120, target, color, unit = '' }: { data: { x: string; y: number; label?: string }[]; height?: number; target?: number; color?: string; unit?: string }) {
  const p = usePalette();
  const [w, setW] = useState(320);
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.y), target ?? 0) * 1.1 || 1;
  const bw = (w - 8) / data.length;
  return (
    <View onLayout={(e) => setW(e.nativeEvent.layout.width)} accessibilityLabel={`Bar chart of ${data.length} values ${unit}`}>
      <Svg width={w} height={height + 16}>
        {target ? <Line x1={0} x2={w} y1={height - (target / max) * height} y2={height - (target / max) * height} stroke={p.copper} strokeDasharray="3,3" strokeWidth={1} /> : null}
        {data.map((d, i) => {
          const h = (d.y / max) * height;
          return (
            <G key={i}>
              <Rect x={4 + i * bw + bw * 0.18} y={height - h} width={bw * 0.64} height={Math.max(h, 1)} rx={2} fill={color ?? p.teal} opacity={i === data.length - 1 ? 1 : 0.55} />
              <SvgText x={4 + i * bw + bw / 2} y={height + 12} fontSize={9} fill={p.muted} textAnchor="middle">
                {d.label ?? d.x.slice(8, 10)}
              </SvgText>
            </G>
          );
        })}
      </Svg>
    </View>
  );
}

/** Longevity age dial (DS §7.4): chronological tick, copper fill when biological < chronological, graphite when higher. */
export function Dial({ value, chrono, size = 210, confidence }: { value: number | null; chrono: number | null; size?: number; confidence?: number }) {
  const p = usePalette();
  const r = size / 2 - 14;
  const c = size / 2;
  const lo = (chrono ?? 40) - 15;
  const hi = (chrono ?? 40) + 15;
  const ang = (v: number) => -220 + (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo) * 260;
  const pt = (a: number, rr = r) => [c + rr * Math.cos((a * Math.PI) / 180), c + rr * Math.sin((a * Math.PI) / 180)];
  const arc = (a0: number, a1: number) => {
    const [x0, y0] = pt(a0);
    const [x1, y1] = pt(a1);
    return `M${x0},${y0} A${r},${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1},${y1}`;
  };
  const younger = value != null && chrono != null && value <= chrono;
  const fill = younger ? p.copper : p.graphite;
  const [tx0, ty0] = chrono != null ? pt(ang(chrono), r - 10) : [0, 0];
  const [tx1, ty1] = chrono != null ? pt(ang(chrono), r + 10) : [0, 0];
  return (
    <Svg width={size} height={size * 0.82}>
      <Path d={arc(-220, 40)} stroke={p.surfaceAlt} strokeWidth={12} fill="none" strokeLinecap="round" />
      {value != null ? <Path d={arc(-220, ang(value))} stroke={fill} strokeWidth={12} fill="none" strokeLinecap="round" opacity={0.4 + 0.6 * (confidence ?? 1)} /> : null}
      {chrono != null ? <Line x1={tx0} y1={ty0} x2={tx1} y2={ty1} stroke={p.text} strokeWidth={2} /> : null}
      <SvgText x={c} y={c - 2} fontSize={46} fill={p.text} textAnchor="middle" fontFamily="Fraunces_500Medium">
        {value != null ? value.toFixed(1) : '—'}
      </SvgText>
      <SvgText x={c} y={c + 22} fontSize={12} fill={p.muted} textAnchor="middle" fontFamily="Inter_400Regular">
        {value != null && chrono != null ? `${Math.abs(value - chrono).toFixed(1)} y ${younger ? 'younger' : 'older'} than ${chrono.toFixed(1)}` : 'Needs a blood panel'}
      </SvgText>
    </Svg>
  );
}

export function Ring({ value, size = 56, stroke = 6, color, label }: { value: number | null; size?: number; stroke?: number; color?: string; label?: string }) {
  const p = usePalette();
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const v = value == null ? 0 : Math.max(0, Math.min(100, value));
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute' }}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={p.surfaceAlt} strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color ?? p.teal}
          strokeWidth={stroke}
          fill="none"
          strokeDasharray={`${(v / 100) * circ} ${circ}`}
          strokeLinecap="round"
          rotation={-90}
          origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <Text style={{ fontSize: size > 50 ? 15 : 12, fontFamily: 'Inter_600SemiBold', color: p.text, fontVariant: ['tabular-nums'] }}>{value == null ? '—' : label ?? Math.round(v)}</Text>
    </View>
  );
}

export function StackBar({ parts }: { parts: { value: number; color: string }[] }) {
  const total = parts.reduce((a, b) => a + b.value, 0) || 1;
  return (
    <View style={{ flexDirection: 'row', height: 8, borderRadius: 4, overflow: 'hidden', gap: 2 }}>
      {parts.map((pt, i) => (pt.value ? <View key={i} style={{ flex: pt.value / total, backgroundColor: pt.color }} /> : null))}
    </View>
  );
}

function niceStep(raw: number) {
  const mag = Math.pow(10, Math.floor(Math.log10(raw || 1)));
  const n = raw / mag;
  return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
}
