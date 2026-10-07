import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import Svg, { Circle, G, Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import { usePalette } from '@/lib/theme';
import { Chip, Row, T } from '@/ui/core';

export const VERDICT: Record<string, { label: string; tone: 'success' | 'teal' | 'danger' | 'muted' | 'warn' }> = {
  helped: { label: 'Working for you', tone: 'success' },
  promising: { label: 'Promising', tone: 'teal' },
  possible_negative: { label: 'Possible negative', tone: 'danger' },
  no_signal: { label: 'No reliable signal', tone: 'muted' },
  too_early: { label: 'Too early', tone: 'warn' },
  in_session_only: { label: 'In-session only', tone: 'muted' },
};

export function VerdictChip({ verdict }: { verdict?: string | null }) {
  const p = usePalette();
  if (!verdict) return <Chip label="Not tried" />;
  const v = VERDICT[verdict] ?? { label: verdict, tone: 'muted' };
  const c = { success: [p.success, p.successSoft], teal: [p.teal, p.tealSoft], danger: [p.danger, p.dangerSoft], warn: [p.warn, p.warnSoft],
    muted: [p.muted, p.surfaceAlt] }[v.tone];
  return <Chip label={v.label} fg={c[0]} bg={c[1]} />;
}

export function SafetyChip({ status }: { status?: string }) {
  const p = usePalette();
  if (status === 'not_suitable') return <Chip label="Not suitable for you" fg={p.danger} bg={p.dangerSoft} />;
  if (status === 'caution') return <Chip label="Check with clinician" fg={p.warn} bg={p.warnSoft} />;
  return <Chip label="Cleared by Vault check" fg={p.success} bg={p.successSoft} />;
}

const PHASE_NAMES: Record<string, string> = {
  baseline: 'Baseline', active: 'In session', recovery: 'Recovery', compression: 'Compression', stable: 'At pressure',
  decompression: 'Decompression', hot: 'Heat', cold: 'Cold', hypoxic: 'Hypoxic', hyperoxic: 'Hyperoxic',
};

export const phaseName = (p: string) => PHASE_NAMES[p] ?? p;

/** One physiological signal across the whole session, with phases shaded (seconds on the x-axis). */
export function SessionChart({ t, y, phases, unit, label, band, height = 150, decimals = 0, color }: {
  t: number[]; y: (number | null)[]; phases: { phase: string; start: number; end: number }[]; unit: string; label: string;
  band?: [number, number] | null; height?: number; decimals?: number; color?: string;
}) {
  const p = usePalette();
  const [w, setW] = useState(320);
  const [sel, setSel] = useState<number | null>(null);
  const pts = t.map((x, i) => [x, y[i]] as const).filter((q): q is readonly [number, number] => q[1] != null);
  if (pts.length < 2) return null;
  const pad = { l: 34, r: 8, t: 10, b: 20 };
  const vals = pts.map((q) => q[1]);
  let lo = Math.min(...vals, ...(band ?? []));
  let hi = Math.max(...vals, ...(band ?? []));
  if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
  const m = (hi - lo) * 0.08;
  lo -= m; hi += m;
  const T0 = pts[0][0], T1 = pts[pts.length - 1][0];
  const sx = (x: number) => pad.l + ((x - T0) / Math.max(1, T1 - T0)) * (w - pad.l - pad.r);
  const sy = (v: number) => pad.t + (1 - (v - lo) / (hi - lo)) * (height - pad.t - pad.b);
  const d = pts.map((q, i) => `${i ? 'L' : 'M'}${sx(q[0]).toFixed(1)},${sy(q[1]).toFixed(1)}`).join(' ');
  const shade = (ph: string) => (ph === 'baseline' ? null : ph === 'recovery' || ph === 'decompression' || ph === 'hyperoxic' ? p.teal : p.copper);
  const s = sel != null ? pts[sel] : null;
  const fmt = (v: number) => v.toFixed(decimals);
  return (
    <View onLayout={(e) => setW(e.nativeEvent.layout.width)} style={{ gap: 4 }}>
      <Row>
        <T v="label" style={{ flex: 1 }}>{label}</T>
        <T v="small" style={{ fontVariant: ['tabular-nums'] }}>{s ? `${Math.round(s[0] / 60)} min · ${fmt(s[1])} ${unit}` : `${fmt(Math.min(...vals))}–${fmt(Math.max(...vals))} ${unit}`}</T>
      </Row>
      <Pressable onPressIn={(e) => {
        const x = e.nativeEvent.locationX;
        let best = 0;
        pts.forEach((q, i) => { if (Math.abs(sx(q[0]) - x) < Math.abs(sx(pts[best][0]) - x)) best = i; });
        setSel(best);
      }} accessibilityLabel={`${label} during the session, ${fmt(Math.min(...vals))} to ${fmt(Math.max(...vals))} ${unit}`}>
        <Svg width={w} height={height}>
          {phases.map((ph, i) => {
            const c = shade(ph.phase);
            if (!c || ph.end <= T0 || ph.start >= T1) return null;
            const x0 = sx(Math.max(ph.start, T0)), x1 = sx(Math.min(ph.end, T1));
            return <Rect key={i} x={x0} width={Math.max(1, x1 - x0)} y={pad.t} height={height - pad.t - pad.b} fill={c} opacity={0.09} />;
          })}
          {band ? <Rect x={pad.l} width={w - pad.l - pad.r} y={sy(band[1])} height={Math.max(1, sy(band[0]) - sy(band[1]))} fill={p.teal} opacity={0.12} /> : null}
          {[lo + m, (lo + hi) / 2, hi - m].map((v, i) => (
            <G key={i}>
              <Line x1={pad.l} x2={w - pad.r} y1={sy(v)} y2={sy(v)} stroke={p.border} strokeWidth={1} opacity={0.45} />
              <SvgText x={pad.l - 5} y={sy(v) + 3} fontSize={9} fill={p.muted} textAnchor="end" fontFamily="Inter_400Regular">{fmt(v)}</SvgText>
            </G>
          ))}
          <Path d={d} stroke={color ?? p.teal} strokeWidth={1.4} fill="none" />
          {s ? <G><Line x1={sx(s[0])} x2={sx(s[0])} y1={pad.t} y2={height - pad.b} stroke={p.muted} strokeWidth={1} /><Circle cx={sx(s[0])} cy={sy(s[1])} r={3.5} fill={p.copper} /></G> : null}
          {[0, 0.25, 0.5, 0.75, 1].map((f) => {
            const x = T0 + f * (T1 - T0);
            return <SvgText key={f} x={sx(x)} y={height - 5} fontSize={9} fill={p.muted} textAnchor={f === 0 ? 'start' : f === 1 ? 'end' : 'middle'} fontFamily="Inter_400Regular">{Math.round(x / 60)}′</SvgText>;
          })}
        </Svg>
      </Pressable>
    </View>
  );
}

export function PhaseLegend({ phases }: { phases: { phase: string; start: number; end: number }[] }) {
  const p = usePalette();
  return (
    <Row style={{ flexWrap: 'wrap' }} gap={10}>
      {Array.from(new Set(phases.map((x) => x.phase))).map((ph) => {
        const c = ph === 'baseline' ? p.surfaceAlt : ph === 'recovery' || ph === 'decompression' || ph === 'hyperoxic' ? p.tealSoft : p.copperSoft;
        return (
          <Row key={ph} gap={4}>
            <View style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: c, borderWidth: 1, borderColor: p.border }} />
            <Text style={{ color: p.muted, fontSize: 11, fontFamily: 'Inter_500Medium' }}>{phaseName(ph)}</Text>
          </Row>
        );
      })}
    </Row>
  );
}

export function HsaiCard({ h, onPress }: { h: any; onPress?: () => void }) {
  const p = usePalette();
  if (!h?.available) return null;
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`Adaptability index ${h.score}`}>
      <View style={{ backgroundColor: p.surface, borderRadius: 16, borderWidth: 1, borderColor: p.border, padding: 16, gap: 8 }}>
        <Row>
          <View style={{ flex: 1 }}>
            <T v="label">Health-span adaptability (HSAI)</T>
            <T v="small">How well your body responds to and recovers from stress</T>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <T v="num" style={{ fontSize: 30 }} color={p.teal}>{h.score}</T>
            <T v="small">{h.range[0]}–{h.range[1]}</T>
          </View>
        </Row>
        <Chip label={h.zone} fg={p.teal} bg={p.tealSoft} />
        {h.domains.map((d: any) => (
          <View key={d.key} style={{ gap: 2 }}>
            <Row><T v="small" style={{ flex: 1 }}>{d.name}</T><T v="small" style={{ fontVariant: ['tabular-nums'] }}>{d.score}</T></Row>
            <View style={{ height: 6, borderRadius: 3, backgroundColor: p.surfaceAlt }}>
              <View style={{ width: `${Math.max(3, d.score)}%`, height: 6, borderRadius: 3, backgroundColor: d.score < 45 ? p.copper : p.teal, opacity: 0.35 + 0.65 * d.weight / 0.25 }} />
            </View>
          </View>
        ))}
        <T v="small">{h.message}</T>
      </View>
    </Pressable>
  );
}

export const inr = (n: number) => `₹${Math.round(n).toLocaleString('en-IN')}`;
