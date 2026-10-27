// Vitals — the member's body by system, Oura/Ultrahuman-style: a big 0-100 score per system with color-coded
// contributor bars (green optimal · amber good · red needs attention). Deeper than a wearable — every bar traces
// to one of the member's own markers. Composed by /me/scores.
import { Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, Chip, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';

export default function Vitals() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<any>('/me/scores');
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Loading what="Scoring your systems…" /></Screen>;

  const col = (status: string) => status === 'optimal' ? p.success : status === 'good' ? p.warn : p.danger;
  const bandTone = (band: string) => /Optimal/.test(band) ? { fg: p.success, bg: p.successSoft } : /Good/.test(band) ? { fg: p.warn, bg: p.warnSoft } : { fg: p.danger, bg: p.dangerSoft };
  const ov = bandTone(data.overall_band ?? '');

  return (
    <Screen edges={[]} onRefresh={reload} refreshing={loading}>
      <Stack.Screen options={{ title: '' }} />
      <T v="h1">Vitals</T>
      <T v="small" color={p.muted}>Your body by system, scored 0–100 from your own labs and vitals. Deeper than a wearable — every bar traces to a marker.</T>

      <Card tone="teal" style={{ alignItems: 'center', paddingVertical: space[5] }}>
        <T v="display" style={{ fontSize: 68, color: ov.fg }}>{data.overall ?? '—'}</T>
        <Chip label={data.overall_band ?? '—'} fg={ov.fg} bg={p.surface} />
        <T v="small" color={p.muted} style={{ marginTop: 6 }}>Overall vitality · as of {data.as_of}</T>
      </Card>

      {(data.systems ?? []).map((s: any) => {
        const t = bandTone(s.band);
        return (
          <Section key={s.key} title={s.name}>
            <Card style={{ gap: space[2] }}>
              <Row style={{ alignItems: 'center' }}>
                <T v="display" style={{ fontSize: 42, flex: 1, color: t.fg }}>{s.score}</T>
                <Chip label={s.band} fg={t.fg} bg={t.bg} />
              </Row>
              {s.contributors.map((c: any) => (
                <View key={c.key}>
                  <Row style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <T v="body">{c.label}</T>
                    <T v="small" color={col(c.status)}>{c.value}{c.unit}</T>
                  </Row>
                  <View style={{ height: 8, borderRadius: 4, backgroundColor: p.surfaceAlt, marginTop: 4, overflow: 'hidden' }}>
                    <View style={{ height: '100%', width: `${Math.max(4, c.score ?? 0)}%`, backgroundColor: col(c.status), borderRadius: 4 }} />
                  </View>
                </View>
              ))}
            </Card>
          </Section>
        );
      })}

      <T v="small" color={p.faint} style={{ marginTop: space[3] }}>Green optimal · amber good · red needs attention — each scored against evidence-based reference ranges. Not a diagnosis.</T>
      <View style={{ height: space[6] }} />
    </Screen>
  );
}
