import { router, Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Ring } from '@/ui/charts';
import { Card, Chip, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';
import { InsightCard } from '@/ui/insight';

export default function Domain() {
  const { key } = useLocalSearchParams<{ key: string }>();
  const p = usePalette();
  const { data: d, error, reload } = useApi<any>(`/domains/${key}`, [key]);
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen edges={[]}><Loading what="Scoring…" /></Screen>;
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: d.title }} />
      <Card>
        <Row>
          <Ring value={d.score} size={84} stroke={8} color={d.score >= 80 ? p.success : d.score >= 60 ? p.warn : p.danger} />
          <View style={{ flex: 1, gap: 4 }}>
            <T v="h1">{d.title}</T>
            <T v="body">{d.status ?? 'Not enough data'}</T>
            <T v="small">{Math.round(d.confidence * 100)}% confidence · {Math.round(d.coverage * 100)}% of inputs available</T>
          </View>
        </Row>
        {d.missing.length ? <T v="small" color={p.warn}>Missing: {d.missing.join(', ')}. Their weight is excluded and confidence lowered — nothing is filled in.</T> : null}
      </Card>
      {d.pillars.map((pl: any) => (
        <Card key={pl.name}>
          <Row>
            <T v="h3" style={{ flex: 1 }}>{pl.name}</T>
            <Chip label={`${Math.round(pl.weight * 100)}% weight`} />
            <T v="num" style={{ fontSize: 18 }}>{pl.score ?? '—'}</T>
          </Row>
          {pl.inputs.length ? (
            pl.inputs.map((x: any) => (
              <Pressable key={x.id} onPress={() => router.push(x.source.startsWith('lab') ? `/marker/${x.id}` : `/signal/${x.id}`)}>
                <Row>
                  <T v="body" style={{ flex: 1 }}>{x.name}</T>
                  <T v="small">{x.value} {x.unit}</T>
                  <T v="small" style={{ width: 34, textAlign: 'right' }}>{Math.round(x.score)}</T>
                </Row>
                <T v="small">{x.source}</T>
              </Pressable>
            ))
          ) : (
            <T v="small">No data for this pillar yet.</T>
          )}
        </Card>
      ))}
      <T v="small">{d.method}</T>
      {d.related?.length ? (
        <Section title="Related patterns">
          {d.related.map((i: any) => <InsightCard key={i.id} i={i} compact />)}
        </Section>
      ) : null}
    </Screen>
  );
}
