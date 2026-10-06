import { router } from 'expo-router';
import React from 'react';

import { fmtDate, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Bars } from '@/ui/charts';
import { Button, Card, Divider, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';
import { View } from 'react-native';

export default function Nutrition() {
  const p = usePalette();
  const tr = useApi<any>('/nutrition/trends?days=7');
  const meals = useApi<any[]>('/meals?limit=20');
  if (!tr.data) return <Screen edges={[]}><Loading what="Loading…" /></Screen>;
  const logged = tr.data.days.filter((d: any) => d.logged);
  const avg = logged.length ? Math.round(logged.reduce((a: number, d: any) => a + d.kcal, 0) / logged.length) : null;
  return (
    <Screen edges={[]}>
      <Card>
        <T v="label">Energy · last 7 days</T>
        <Bars data={tr.data.days.map((d: any) => ({ x: d.day, y: d.kcal }))} target={tr.data.goals.kcal} unit="kcal" />
        <Row>
          <Stat label="Average (logged days)" value={avg} unit="kcal" />
          <Stat label="Target" value={tr.data.goals.kcal} unit="kcal" />
          <Stat label="Days logged" value={`${logged.length}/7`} />
        </Row>
        <T v="small">Days without logs are left empty, not counted as zero.</T>
      </Card>
      <Button icon="plus" title="Log a meal" onPress={() => router.push('/log?kind=meal')} />
      <Section title="Meal history">
        <Card style={{ paddingVertical: 2 }}>
          {(meals.data ?? []).map((m: any, i: number) => (
            <View key={m.id}>
              {i ? <Divider /> : null}
              <Row style={{ paddingVertical: 10 }}>
                <View style={{ width: 38, height: 38, borderRadius: 19, borderWidth: 2, borderColor: m.analysis.score >= 70 ? p.success : m.analysis.score >= 45 ? p.warn : p.danger, alignItems: 'center', justifyContent: 'center' }}>
                  <T v="small" style={{ fontWeight: '700' }}>{m.analysis.score ?? '—'}</T>
                </View>
                <View style={{ flex: 1 }}>
                  <T v="body">{m.name}</T>
                  <T v="small">{Math.round(m.analysis.kcal ?? 0)} kcal · P {Math.round(m.analysis.protein ?? 0)} g · {fmtDate(m.ts)} {m.ts.slice(11, 16)}</T>
                </View>
              </Row>
            </View>
          ))}
        </Card>
      </Section>
    </Screen>
  );
}
