import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { fmtDate, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Card, Chip, Loading, Row, Screen, Section, T } from '@/ui/core';

export default function Notes() {
  const p = usePalette();
  const { data } = useApi<any>('/clinician-notes');
  if (!data) return <Screen edges={[]}><Loading what="Summarising your Vault…" /></Screen>;
  return (
    <Screen edges={[]}>
      <Section title="TL;DR">
        <Card tone="teal"><T v="body">{data.tldr}</T></Card>
      </Section>
      <Section title="Top 3 priorities">
        {data.top.map((t: any, i: number) => (
          <Card key={t.id} onPress={() => router.push(`/marker/${t.id}`)}>
            <Row><T v="label">#{i + 1}</T><T v="h3" style={{ flex: 1 }}>{t.name}</T><T v="num" style={{ fontSize: 17 }} color={p.danger}>{t.value} <T v="small">{t.unit}</T></T></Row>
            <T v="small">{fmtDate(t.day, true)}{t.trend ? ` · was ${t.trend.from} on ${fmtDate(t.trend.from_day, true)}` : ''}</T>
            {t.why ? <T v="body">{t.why}</T> : null}
            {t.related.length ? (
              <View style={{ gap: 4 }}>
                <T v="label">Related markers also out of range</T>
                <Row style={{ flexWrap: 'wrap' }}>{t.related.map((r: any) => <Pressable key={r.id} onPress={() => router.push(`/marker/${r.id}`)}><Chip label={r.name} fg={p.danger} bg={p.dangerSoft} /></Pressable>)}</Row>
              </View>
            ) : null}
          </Card>
        ))}
      </Section>
      <T v="small">{data.disclaimer}</T>
    </Screen>
  );
}
