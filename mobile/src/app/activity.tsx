import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Ring } from '@/ui/charts';
import { Card, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';

export default function Activity() {
  const p = usePalette();
  const { data: d, error, reload } = useApi<any>('/dashboard');
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen edges={[]}><Loading what="Loading today…" /></Screen>;
  const ringCol = [p.copper, p.teal, p.success];
  const max = Math.max(1, ...d.heatmap.map((h: any) => h.value ?? 0));
  return (
    <Screen edges={[]}>
      <Card>
        <T v="label">Today · {d.day}</T>
        <Row style={{ justifyContent: 'space-around' }}>
          {d.rings.map((r: any, i: number) => (
            <Pressable key={r.id} onPress={() => router.push(`/signal/${r.id}`)} style={{ alignItems: 'center', gap: 4 }}>
              <Ring value={Math.min(r.pct, 100)} size={78} stroke={8} color={ringCol[i]} label={`${r.pct}%`} />
              <T v="body" style={{ fontWeight: '600' }}>{r.label}</T>
              <T v="small">{r.value == null ? '—' : Math.round(r.value).toLocaleString('en-IN')} / {r.goal?.toLocaleString('en-IN')} {r.unit}</T>
            </Pressable>
          ))}
        </Row>
      </Card>
      <Row gap={space[3]}>
        <Gauge label="Recovery" value={d.recovery} color={d.recovery >= 67 ? p.success : d.recovery >= 34 ? p.warn : p.danger} />
        <Gauge label="Strain" value={d.strain != null ? Math.round((d.strain / 21) * 100) : null} text={d.strain != null ? `${d.strain}` : undefined} color={p.copper} />
        <Gauge label="Sleep" value={d.sleep_score} color={p.teal} />
        <Gauge label="Stress (est.)" value={d.stress} color={d.stress >= 60 ? p.danger : p.warn} />
      </Row>
      <T v="small">Recovery: {d.methods.recovery}. Strain: {d.methods.strain}. {d.stress_note}.</T>
      <Section title="Vitals vs your baseline">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space[3] }}>
          {d.vitals.map((v: any) => (
            <Pressable key={v.id} onPress={() => router.push(`/signal/${v.id}`)} style={{ width: '47.5%', backgroundColor: p.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: v.flag && v.flag !== 'normal' ? p.danger : p.border, padding: space[3], gap: 2 }}>
              <T v="small" numberOfLines={1}>{v.label}</T>
              <T v="num" style={{ fontSize: 19 }}>{v.value == null ? '—' : Number(v.value).toFixed(v.value < 10 ? 1 : 0)} <T v="small">{v.unit}</T></T>
              <T v="small" color={v.flag === 'normal' ? p.success : v.flag ? p.danger : p.faint}>
                {v.value == null ? 'No data today' : v.flag === 'normal' ? 'Within your usual range' : `${v.flag === 'high' ? 'Above' : 'Below'} your usual range`}
              </T>
            </Pressable>
          ))}
        </View>
      </Section>
      <Section title="Exercise · last 9 weeks">
        <Card>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
            {d.heatmap.map((h: any) => (
              <View key={h.day} accessibilityLabel={`${h.day}: ${h.value ?? 0} minutes`} style={{ width: 36, height: 16, borderRadius: 3, backgroundColor: h.value == null ? p.surfaceAlt : p.teal, opacity: h.value == null ? 1 : 0.15 + 0.85 * (h.value / max) }} />
            ))}
          </View>
          <T v="small">Darker = more exercise minutes. 7 squares per row = one week.</T>
        </Card>
      </Section>
    </Screen>
  );
}

function Gauge({ label, value, text, color }: { label: string; value: number | null; text?: string; color: string }) {
  return (
    <View style={{ flex: 1, alignItems: 'center', gap: 4 }}>
      <Ring value={value} size={64} stroke={6} color={color} label={text} />
      <T v="small" style={{ textAlign: 'center' }}>{label}</T>
    </View>
  );
}
