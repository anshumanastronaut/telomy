import { router } from 'expo-router';
import React from 'react';

import { fmtDate, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Bars } from '@/ui/charts';
import { Button, Card, Divider, Loading, Row, Screen, Section, Segmented, Stat, T } from '@/ui/core';
import { View } from 'react-native';

export default function Nutrition() {
  const p = usePalette();
  const tr = useApi<any>('/nutrition/trends?days=7');
  const meals = useApi<any[]>('/meals?limit=20');
  const [goal, setGoal] = React.useState<'maintain' | 'lose'>('maintain');
  const tg = useApi<any>(`/nutrition/targets?goal=${goal}`);
  const t = tg.data?.targets;
  if (!tr.data) return <Screen edges={[]}><Loading what="Loading…" /></Screen>;
  const logged = tr.data.days.filter((d: any) => d.logged);
  const avg = logged.length ? Math.round(logged.reduce((a: number, d: any) => a + d.kcal, 0) / logged.length) : null;
  return (
    <Screen edges={[]}>
      {t?.ok ? (
        <Card style={{ gap: 8 }}>
          <Row>
            <T v="label" style={{ flex: 1 }}>Your daily targets</T>
            <Segmented options={[{ key: 'maintain', label: 'Maintain' }, { key: 'lose', label: 'Lose 0.5 kg/wk' }]} value={goal} onChange={setGoal} />
          </Row>
          <Row>
            <Stat label="Energy" value={t.kcal} unit="kcal" />
            <Stat label="Protein" value={t.protein_g} unit="g" />
            <Stat label="Fibre" value={t.fibre_g} unit="g" />
          </Row>
          <Row>
            <Stat label="Carbs" value={t.carbs_g} unit="g" />
            <Stat label="Fat" value={t.fat_g} unit="g" />
            <Stat label="Water" value={t.water_l} unit="L" />
          </Row>
          {tg.data.left ? <T v="small">Left today: {tg.data.left.kcal} kcal · {tg.data.left.protein_g} g protein · {tg.data.left.fibre_g} g fibre.</T> : null}
          <T v="small" color={p.faint}>From your body (BMI {t.bmi}), measured activity ({t.pal_why}) and your labs. Protein uses a reference weight of {t.reference_weight} kg.</T>
        </Card>
      ) : tg.data?.targets?.reason ? <Card><T v="small">{tg.data.targets.reason}</T></Card> : null}
      {t?.labs?.length ? (
        <Section title="What your labs mean for food">
          {t.labs.map((l: any) => (
            <Card key={l.marker}><T v="small" color={l.kind === 'doctor' ? p.danger : l.kind === 'test' ? p.warn : p.text}>{l.text}</T></Card>
          ))}
        </Section>
      ) : null}
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
