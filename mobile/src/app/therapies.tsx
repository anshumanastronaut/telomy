import { router, Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, Chip, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';
import { SafetyChip, VerdictChip, inr } from '@/ui/therapy';

export default function Therapies() {
  const p = usePalette();
  const { data, error, reload } = useApi<any[]>('/therapy/catalogue');
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Loading what="Loading therapies…" /></Screen>;
  const cats = Array.from(new Set(data.map((m) => m.category)));
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'All therapies' }} />
      <T v="h1">Therapies at your centre</T>
      <T v="small">{data.length} therapies, each screened against your Vault (labs, medicines, conditions) and graded by evidence. Ozone therapy is not listed — the FDA classes ozone as a toxic gas with no proven medical use.</T>
      {cats.map((c) => (
        <Section key={c} title={c}>
          {data.filter((m) => m.category === c).map((m) => (
            <Card key={m.id} onPress={() => router.push(`/therapy/${m.id}`)}>
              <Row><T v="h3" style={{ flex: 1 }}>{m.name}</T><Chip label={`Evidence ${m.evidence}`} fg={p.teal} bg={p.tealSoft} /></Row>
              <T v="small" numberOfLines={2}>{m.mechanism}</T>
              <Row style={{ flexWrap: 'wrap' }}>
                <VerdictChip verdict={m.my_verdict} />
                <SafetyChip status={m.safety.status} />
                <Chip label={`${m.minutes} min · ${m.price ? inr(m.price) : 'free'}`} />
              </Row>
              <T v="small" color={p.muted}>For: {m.goals.join(', ')}</T>
            </Card>
          ))}
        </Section>
      ))}
      <View style={{ height: space[2] }} />
    </Screen>
  );
}
