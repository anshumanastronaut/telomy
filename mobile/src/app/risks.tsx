import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { statusColor, usePalette } from '@/lib/theme';
import { Card, Chip, ErrorState, Loading, Row, Screen, T } from '@/ui/core';

export default function Risks() {
  const p = usePalette();
  const { data, error, reload } = useApi<any[]>('/risks');
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Loading what="Building your risk map…" /></Screen>;
  const col = (l: string) => (l === 'high' ? [p.danger, p.dangerSoft] : l === 'moderate' ? [p.warn, p.warnSoft] : l === 'low' ? [p.success, p.successSoft] : [p.muted, p.surfaceAlt]);
  return (
    <Screen edges={[]}>
      <T v="h1">Risk map</T>
      <T v="small">Each level shows which of your markers drove it, how much of the evidence is on file, and what's missing. It's a prompt for a conversation with your clinician, not a diagnosis.</T>
      {data.map((r) => {
        const [fg, bg] = col(r.level);
        return (
          <Card key={r.condition}>
            <Row>
              <T v="h3" style={{ flex: 1 }}>{r.condition}</T>
              <Chip label={r.level === 'unknown' ? 'Not enough data' : r.level} fg={fg} bg={bg} />
            </Row>
            <T v="small">{Math.round((r.coverage ?? 0) * 100)}% of the evidence for this condition is in your Vault</T>
            {r.drivers.map((d: any) => (
              <Pressable key={d.id} onPress={() => router.push(`/marker/${d.id}`)}>
                <Row>
                  <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: statusColor(p, d.status).fg }} />
                  <T v="body" style={{ flex: 1 }}>{d.name}</T>
                  <T v="small">{String(d.value)}</T>
                </Row>
              </Pressable>
            ))}
            {r.missing?.length ? <T v="small">Not yet tested: {r.missing.slice(0, 5).join(', ')}</T> : null}
          </Card>
        );
      })}
    </Screen>
  );
}
