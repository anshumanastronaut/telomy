// Lab insights — derived biomarker ratios & indices computed from your own labs (atherogenic + insulin-resistance
// signals, the kind Superpower/Function surface). Wellness information, not a diagnosis. Backend: /biomarkers/ratios.
import { router, Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Card, Empty, Icon, Loading, Row, Screen, T } from '@/ui/core';

type Ratio = { key: string; name: string; value: number; unit: string; status: string; optimal: string; interpretation: string; inputs: string[]; ref: string };

function statusColor(s: string, p: any) {
  return s === 'good' ? '#2F8F6B' : s === 'borderline' ? '#C98A1B' : s === 'high' || s === 'low' ? '#D3523F' : p.muted;
}
const statusLabel: Record<string, string> = { good: 'Optimal', borderline: 'Borderline', high: 'Above optimal', low: 'Below optimal' };

export default function Ratios() {
  const p = usePalette();
  const r = useApi<{ ratios: Ratio[]; note: string; available: number }>('/biomarkers/ratios');

  if (!r.data) return <Screen><Stack.Screen options={{ title: 'Lab insights' }} /><Loading what="Working out your ratios…" /></Screen>;
  const items = r.data.ratios ?? [];

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Lab insights' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Lab insights</T>
        <T v="small" color={p.muted}>Ratios and indices worked out from your latest labs — higher-signal than any single marker. Wellness information, not a diagnosis.</T>
      </View>

      {items.length === 0 ? (
        <Empty title="Not enough labs yet" body="Add a blood report with cholesterol, triglycerides and glucose and these insights will appear." actions={[{ title: 'Add a report', onPress: () => router.push('/upload') }]} />
      ) : (
        <>
          {items.map((x) => (
            <Card key={x.key} style={{ gap: space[2] }}>
              <Row style={{ alignItems: 'center' }}>
                <View style={{ flex: 1 }}>
                  <T v="h3">{x.name}</T>
                  <T v="small" color={p.muted}>Optimal {x.optimal} · {x.ref}</T>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <T v="num" style={{ color: statusColor(x.status, p) }}>{x.value}</T>
                  <Row gap={4} style={{ alignItems: 'center' }}>
                    <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: statusColor(x.status, p) }} />
                    <T v="small" color={statusColor(x.status, p)}>{statusLabel[x.status] ?? x.status}</T>
                  </Row>
                </View>
              </Row>
              <T v="small">{x.interpretation}</T>
              <Row gap={6} style={{ flexWrap: 'wrap' }}>
                {x.inputs.map((i) => <T key={i} v="small" color={p.faint} style={{ backgroundColor: p.surfaceAlt, borderRadius: radius.sm, paddingVertical: 2, paddingHorizontal: 7 }}>{i}</T>)}
              </Row>
            </Card>
          ))}
          <Row style={{ alignItems: 'flex-start', paddingHorizontal: space[1] }}>
            <Icon name="info.circle" size={14} color={p.faint} />
            <T v="small" color={p.faint} style={{ flex: 1, marginLeft: space[2] }}>{r.data.note}</T>
          </Row>
        </>
      )}
    </Screen>
  );
}
