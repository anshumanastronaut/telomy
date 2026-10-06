import React, { useState } from 'react';
import { Pressable, ScrollView, TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { StackBar } from '@/ui/charts';
import { Button, Card, ErrorState, Icon, Loading, Row, Screen, T } from '@/ui/core';

export default function Menu() {
  const p = usePalette();
  const { data, error, reload, setData } = useApi<any[]>('/menu');
  const [day, setDay] = useState(0);
  const [swapFor, setSwapFor] = useState<number | null>(null);
  const [pref, setPref] = useState('');
  const [busy, setBusy] = useState(false);
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Loading what="Planning your week…" /></Screen>;
  const d = data[day];
  async function swap(i: number) {
    setBusy(true);
    const r = await api('/menu/swap', { body: { name: d.meals[i].name, preference: pref } });
    const next = [...data!];
    next[day] = { ...d, meals: d.meals.map((m: any, k: number) => (k === i ? { ...m, ...r, swapped: r.reason } : m)) };
    setData(next);
    setSwapFor(null);
    setPref('');
    setBusy(false);
  }
  return (
    <Screen edges={[]}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
        {data.map((x, i) => {
          const dt = new Date(x.day + 'T12:00:00');
          const on = i === day;
          return (
            <Pressable key={x.day} onPress={() => setDay(i)} style={{ width: 58, alignItems: 'center', paddingVertical: 10, borderRadius: radius.lg, borderWidth: 1, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.tealSoft : p.surface }}>
              <T v="label" color={on ? p.teal : p.muted}>{dt.toLocaleDateString('en-GB', { weekday: 'short' })}</T>
              <T v="h2" color={on ? p.teal : p.text}>{dt.getDate()}</T>
            </Pressable>
          );
        })}
      </ScrollView>
      {d.meals.map((m: any, i: number) => (
        <Card key={i}>
          <Row>
            <T v="label" style={{ flex: 1 }}>{m.time}</T>
            <Pressable onPress={() => setSwapFor(swapFor === i ? null : i)} accessibilityRole="button" style={{ flexDirection: 'row', gap: 4, alignItems: 'center' }}>
              <Icon name="arrow.triangle.2.circlepath" size={13} color={p.teal} />
              <T v="small" color={p.teal} style={{ fontWeight: '600' }}>Swap</T>
            </Pressable>
          </Row>
          <T v="h3">{m.name}</T>
          {m.swapped ? <T v="small" color={p.copper}>{m.swapped}</T> : null}
          <Row>
            <T v="small" style={{ flex: 1 }}>{Math.round(m.kcal)} kcal · P {Math.round(m.protein)} g · C {Math.round(m.carbs)} g · F {Math.round(m.fat)} g</T>
            <T v="small">score {m.score}</T>
          </Row>
          <StackBar parts={[{ value: m.protein * 4, color: p.teal }, { value: m.carbs * 4, color: p.copper }, { value: m.fat * 9, color: p.graphite }]} />
          {swapFor === i ? (
            <View style={{ gap: 8 }}>
              <TextInput value={pref} onChangeText={setPref} placeholder="Any preference? e.g. high protein, no eggs, lighter" placeholderTextColor={p.faint} style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10, color: p.text, fontFamily: 'Inter_400Regular' }} />
              <Button title="Find a swap" loading={busy} onPress={() => swap(i)} />
            </View>
          ) : null}
        </Card>
      ))}
      <T v="small">Built around your active protocol: protein-first breakfasts, dinner 3 h before bed.</T>
    </Screen>
  );
}
