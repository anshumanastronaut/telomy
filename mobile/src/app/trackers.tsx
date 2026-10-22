// Your trackers — everything you've told Sinc to follow (pain, symptoms, supplements, medicines, habits, measurements,
// anything). Today's check-ins sit on top: one tap per score.
import { router, Stack } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Card, ListRow, Row, Screen, Section, T } from '@/ui/core';

const ICON: Record<string, any> = { pain: 'bandage', symptom: 'thermometer.medium', supplement: 'pills', medicine: 'cross.case',
  habit_break: 'nosign', habit_build: 'checkmark.circle', measure: 'ruler', custom: 'square.and.pencil' };

export function ScoreRow({ onPick }: { onPick: (v: number) => void }) {
  const p = usePalette();
  return (
    <Row gap={4} style={{ flexWrap: 'wrap' }}>
      {Array.from({ length: 11 }, (_, v) => (
        <Pressable key={v} onPress={() => onPick(v)} accessibilityLabel={`Score ${v}`}
          style={({ pressed }) => ({ width: 30, height: 30, borderRadius: 15, alignItems: 'center', justifyContent: 'center',
            backgroundColor: pressed ? p.teal : p.surfaceAlt })}>
          <T v="small">{v}</T>
        </Pressable>
      ))}
    </Row>
  );
}

export default function Trackers() {
  const p = usePalette();
  const list = useApi<any[]>('/trackers');
  const today = useApi<any[]>('/trackers/today');
  async function log(id: number, value: number) {
    await api(`/trackers/${id}/entry`, { body: { value } });
    today.reload(); list.reload();
  }
  const items = list.data ?? [];
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Your trackers' }} />
      <T v="small">Tell Sinc anything — "my knee hurts, 5", "started magnesium at night", "track my migraines", "I want to cut sugar" — and it sets up a tracker with a baseline and a plan. They all live here.</T>
      {today.data?.length ? (
        <Section title="Today's check-in">
          {today.data.map((t) => (
            <Card key={t.id} style={{ gap: space[2] }}>
              <T v="body" style={{ fontWeight: '600' }}>{t.ask}</T>
              {t.scale === '0–10' ? <ScoreRow onPick={(v) => log(t.id, v)} /> : (
                <Row>
                  {[['Yes', 1], ['No', 0]].map(([l, v]) => (
                    <Pressable key={l as string} onPress={() => log(t.id, v as number)} style={{ paddingHorizontal: 18, paddingVertical: 8, borderRadius: radius.pill, backgroundColor: p.surfaceAlt }}>
                      <T v="small">{l}</T>
                    </Pressable>
                  ))}
                </Row>
              )}
            </Card>
          ))}
        </Section>
      ) : null}
      <Section title="Following">
        {items.filter((t) => t.active).map((t) => (
          <ListRow key={t.id} icon={ICON[t.kind] ?? 'circle'} title={t.name} subtitle={`${t.baseline?.text ?? ''} · ${t.entries} entries`}
            onPress={() => router.push(`/tracker/${t.id}` as any)} />
        ))}
        {list.data && !items.some((t) => t.active) ? <T v="small">Nothing yet. Tell Sinc about anything you want to follow.</T> : null}
      </Section>
      {items.some((t) => !t.active) ? (
        <Section title="Stopped">
          {items.filter((t) => !t.active).map((t) => (
            <ListRow key={t.id} icon={ICON[t.kind] ?? 'circle'} title={t.name} subtitle={`${t.entries} entries`} onPress={() => router.push(`/tracker/${t.id}` as any)} />
          ))}
        </Section>
      ) : null}
      <View style={{ height: 40 }} />
    </Screen>
  );
}
