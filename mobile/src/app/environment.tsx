import { Stack } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { LineChart } from '@/ui/charts';
import { Card, Chip, Loading, Row, Screen, Section, T } from '@/ui/core';

const CITIES = ['Delhi', 'Bengaluru', 'Mumbai', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Noida', 'Gurugram'];

export default function Environment() {
  const p = usePalette();
  const me = useApi<any>('/environment');
  const [a, setA] = useState('Delhi');
  const [b, setB] = useState('Bengaluru');
  const cmp = useApi<any>(`/environment/compare?a=${a}&b=${b}`, [a, b]);
  const Picker = ({ value, onChange }: { value: string; onChange: (c: string) => void }) => (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
      {CITIES.map((c) => (
        <Pressable key={c} onPress={() => onChange(c)} accessibilityRole="button"
          style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill, backgroundColor: value === c ? p.teal : p.surface, borderWidth: 1, borderColor: value === c ? p.teal : p.border }}>
          <T v="small" color={value === c ? '#fff' : p.text}>{c}</T>
        </Pressable>
      ))}
    </View>
  );
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Environment' }} />
      <T v="h1">What your city does to you</T>
      {!me.data ? <Loading what="Downloading your air and UV history…" /> : me.data.available ? (
        <>
          <Card tone="teal">
            <T v="label">{me.data.home} · last {me.data.days} days</T>
            <T v="body">You breathed PM2.5 averaging {me.data.pm25_mean} µg/m³ (WHO guideline 5) — like {me.data.cigarette_equivalent_per_day} cigarettes a day. Lifelong at this level ≈ {me.data.aqli_years_if_lifelong} years of life expectancy (AQLI).</T>
            <T v="small">Midday UV maximum averaged {me.data.uv_mean_max}. Water: {me.data.water}</T>
          </Card>
          <Card>
            <T v="label">Daily PM2.5 where you were (µg/m³)</T>
            <LineChart points={me.data.timeline.filter((t: any) => t.pm25 != null).map((t: any) => ({ x: t.day, y: t.pm25 }))} height={140} unit="µg/m³" band={[0, 15]} />
            <T v="label">UV index (daily max)</T>
            <LineChart points={me.data.timeline.filter((t: any) => t.uv != null).map((t: any) => ({ x: t.day, y: t.uv }))} height={110} />
          </Card>
          {me.data.effects.length ? (
            <Section title="In your own data, per +10 µg/m³ PM2.5">
              <Card style={{ paddingVertical: 4 }}>
                {me.data.effects.map((e: any, i: number) => (
                  <Row key={e.metric} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                    <T v="body" style={{ flex: 1 }}>{e.label} next night</T>
                    <T v="small">{e.per_10ug > 0 ? '+' : ''}{e.per_10ug} {e.unit} [{e.ci95[0]}, {e.ci95[1]}] {e.p}</T>
                  </Row>
                ))}
              </Card>
              <T v="small">{me.data.method}</T>
            </Section>
          ) : null}
        </>
      ) : <Card><T v="body">{me.data.message}</T></Card>}

      <Section title="Same person, two cities">
        <Picker value={a} onChange={setA} />
        <T v="small" style={{ textAlign: 'center' }}>vs</T>
        <Picker value={b} onChange={setB} />
        {cmp.data ? (
          <>
            <Row>
              {cmp.data.cities.map((c: any) => (
                <Card key={c.city} style={{ flex: 1 }}>
                  <T v="h3">{c.city}</T>
                  <T v="small">PM2.5 {c.pm25_annual} µg/m³/yr{c.pm25_last_week ? ` · last week ${c.pm25_last_week}` : ''}</T>
                  <T v="small">≈ {c.cigarettes_per_day_equiv} cigarettes/day</T>
                  <T v="small">UV max ≈ {c.uv_mean_max} · {c.altitude_m} m</T>
                  <Chip label={`−${c.aqli_years_lost} y life (AQLI)`} fg={p.danger} bg={p.dangerSoft} />
                </Card>
              ))}
            </Row>
            <Card>{cmp.data.summary.map((s: string) => <T key={s} v="body">• {s}</T>)}</Card>
            <T v="small" color={p.muted}>Sources: {cmp.data.sources.join('; ')}.</T>
          </>
        ) : <Loading what="Comparing…" />}
      </Section>
      <View style={{ height: space[2] }} />
    </Screen>
  );
}
