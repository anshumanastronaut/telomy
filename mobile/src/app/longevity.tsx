import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { fmtDate, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Dial, LineChart } from '@/ui/charts';
import { Card, ErrorState, Loading, Prov, Row, Screen, Section, T } from '@/ui/core';

export default function Longevity() {
  const p = usePalette();
  const { data: la, error, reload } = useApi<any>('/longevity');
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!la) return <Screen edges={[]}><Loading what="Calculating…" /></Screen>;
  return (
    <Screen edges={[]}>
      <View style={{ alignItems: 'center' }}>
        <Dial value={la.value} chrono={la.chronological} confidence={la.confidence} size={240} />
      </View>
      <Prov source={la.method} when={la.as_of ? fmtDate(la.as_of, true) : null} confidence={la.confidence} />
      {la.history?.length > 1 ? (
        <Section title="Over time">
          <Card>
            <LineChart points={la.history.map((h: any) => ({ x: h.day, y: h.phenoage }))} unit="y" dots caption={`PhenoAge at each blood panel (n = ${la.history.length})`} />
          </Card>
        </Section>
      ) : null}
      <Section title="What moves your number">
        <Card>
          <T v="small">Years added (+) or removed (−) by each marker versus an optimal reference person.</T>
          {(la.contributors ?? []).map((c: any) => (
            <Pressable key={c.marker_id} onPress={() => router.push(`/marker/${c.marker_id}`)}>
              <Row>
                <T v="body" style={{ flex: 1 }}>{c.name}</T>
                <T v="small">{c.value}</T>
                <View style={{ width: 90, alignItems: c.years >= 0 ? 'flex-start' : 'flex-end' }}>
                  <View style={{ height: 8, width: Math.min(90, Math.abs(c.years) * 18), backgroundColor: c.years > 0 ? p.graphite : p.copper, borderRadius: 4 }} />
                </View>
                <T v="num" style={{ fontSize: 14, width: 44, textAlign: 'right' }}>{c.years > 0 ? '+' : ''}{c.years}</T>
              </Row>
            </Pressable>
          ))}
        </Card>
      </Section>
      <Section title="Other clocks in your Vault">
        <Card>
          {Object.entries(la.clocks ?? {}).map(([k, c]: any) => (
            <Pressable key={k} onPress={() => router.push(`/marker/${k}`)}>
              <Row>
                <T v="body" style={{ flex: 1 }}>{c.name}</T>
                <T v="num" style={{ fontSize: 16 }}>{c.value} <T v="small">{c.unit}</T></T>
              </Row>
              <T v="small">{fmtDate(c.day, true)}</T>
            </Pressable>
          ))}
        </Card>
      </Section>
      <T v="small">
        The dial uses PhenoAge (Levine 2018), computed from albumin, creatinine, glucose, hs-CRP, lymphocytes, MCV, RDW, alkaline phosphatase and WBC. Epigenetic and proteomic clocks measure different biology, so they rarely agree exactly — the trend matters more than any single number.
      </T>
    </Screen>
  );
}
