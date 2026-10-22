// One tracker: plan, baseline, recent entries, and what moves it in your own data.
import { Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Row, Screen, Section, T } from '@/ui/core';
import { ScoreRow } from '../trackers';

export default function Tracker() {
  const p = usePalette();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, reload } = useApi<any>(`/trackers/${id}`);
  if (!data) return <Screen edges={[]}><Stack.Screen options={{ title: 'Tracker' }} /></Screen>;
  const plan = data.plan ?? {};
  const entries: any[] = data.entries ?? [];
  const vals = entries.filter((e) => e.value != null).slice(0, 30).reverse();
  const max = Math.max(10, ...vals.map((e) => e.value));
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: data.name }} />
      <Card style={{ gap: space[2] }}>
        <T v="label">Baseline</T>
        <T v="body">{data.baseline?.text}</T>
        {vals.length ? (
          <Row gap={3} style={{ alignItems: 'flex-end', height: 70 }}>
            {vals.map((e, i) => <View key={i} style={{ flex: 1, height: Math.max(3, 66 * e.value / max), borderRadius: 2, backgroundColor: p.teal }} />)}
          </Row>
        ) : null}
      </Card>
      {data.active && data.scale === '0–10' ? (
        <Card style={{ gap: space[2] }}>
          <T v="label">Log today</T>
          <ScoreRow onPick={async (v) => { await api(`/trackers/${id}/entry`, { body: { value: v } }); reload(); }} />
        </Card>
      ) : null}
      <Section title="What moves it">
        <T v="body">{data.drivers?.text}</T>
        {data.drivers?.method ? <T v="small" color={p.muted}>{data.drivers.method}</T> : null}
      </Section>
      <Section title="The plan">
        {(plan.steps ?? []).map((s: string, i: number) => <T key={i} v="body">• {s}</T>)}
        {plan.review_on ? <T v="small">Review on {plan.review_on}</T> : null}
        {(plan.warnings ?? []).map((w: string, i: number) => <T key={i} v="small" color={p.warn}>{w}</T>)}
        {plan.safety ? <T v="small" color={p.muted}>{plan.safety}</T> : null}
      </Section>
      <Section title="Recent entries">
        {entries.slice(0, 12).map((e, i) => (
          <Row key={i}><T v="small" style={{ width: 120 }}>{e.ts.slice(0, 16).replace('T', ' ')}</T><T v="body">{e.value ?? '—'}</T>
            {e.note ? <T v="small" numberOfLines={1} style={{ flex: 1 }}>{e.note}</T> : null}</Row>
        ))}
        {!entries.length ? <T v="small">No entries yet.</T> : null}
      </Section>
      {data.active ? <Button kind="secondary" title="Stop tracking" onPress={async () => { await api(`/trackers/${id}/stop`, { method: 'POST' }); reload(); }} /> : null}
      <View style={{ height: 40 }} />
    </Screen>
  );
}
