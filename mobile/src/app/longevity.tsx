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
  const { data: bio } = useApi<any>('/bioage');
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
      <PaceAndAges la={la} bio={bio} />
      <Section title="Epigenetic clocks">
        <Card>
          {Object.keys(la.clocks ?? {}).length ? (
            Object.entries(la.clocks).map(([k, c]: any) => (
              <Pressable key={k} onPress={() => router.push(`/marker/${k}`)}>
                <Row>
                  <T v="body" style={{ flex: 1 }}>{c.name}</T>
                  <T v="num" style={{ fontSize: 16 }}>{c.value} <T v="small">{c.unit}</T></T>
                </Row>
                <T v="small">{fmtDate(c.day, true)}</T>
              </Pressable>
            ))
          ) : (
            <T v="small">GrimAge, Horvath and DunedinPACE (pace of aging) are measured from a DNA-methylation test, not from blood chemistry. Add an epigenetic test and they'll appear here alongside your PhenoAge.</T>
          )}
        </Card>
      </Section>
      <T v="small">
        The dial uses PhenoAge (Levine 2018), computed from albumin, creatinine, glucose, hs-CRP, lymphocytes, MCV, RDW, alkaline phosphatase and WBC. Epigenetic and proteomic clocks measure different biology, so they rarely agree exactly — the trend matters more than any single number.
      </T>
    </Screen>
  );
}

function PaceAndAges({ la, bio }: { la: any; bio: any }) {
  const p = usePalette();
  // Pace of aging from the PhenoAge trend across panels: change in blood age per year of real time (DunedinPACE is the
  // gold standard, from methylation — this is the blood-chemistry proxy).
  let pace: number | null = null;
  const h = la?.history ?? [];
  if (h.length >= 2) {
    const first = h[0], last = h[h.length - 1];
    const yrs = (new Date(last.day).getTime() - new Date(first.day).getTime()) / (365.25 * 86400000);
    if (yrs > 0.15) pace = Math.round(((last.phenoage - first.phenoage) / yrs) * 100) / 100;
  }
  const ages: { label: string; value: number | null; delta: number | null; note: string }[] = [];
  if (bio?.blood?.kdm?.available) ages.push({ label: 'KDM biological age', value: bio.blood.kdm.value, delta: bio.blood.kdm.delta, note: 'Clinical biomarkers · NHANES-fitted' });
  if (bio?.heart?.available) ages.push({ label: 'Heart / vascular age', value: bio.heart.value, delta: bio.heart.delta, note: `10-yr CVD risk ${bio.heart.ten_year_cvd_risk_pct}%` });
  if (bio?.muscle?.available) ages.push({ label: 'Muscle age', value: bio.muscle.value, delta: bio.muscle.delta, note: bio.muscle.basis });
  const col = (d: number | null) => (d == null ? p.muted : d <= -1 ? p.teal : d >= 2 ? p.copper : p.text);
  return (
    <Section title="Pace & other ages">
      <Card>
        <Row>
          <View style={{ flex: 1 }}><T v="body">Pace of aging</T><T v="small" color={p.muted}>Change in blood age per year, from your panel trend</T></View>
          <T v="num" style={{ fontSize: 18 }} color={pace == null ? p.muted : pace < 1 ? p.teal : p.copper}>{pace == null ? '—' : `${pace > 0 ? '+' : ''}${pace}×`}</T>
        </Row>
        {pace != null ? <T v="small" color={p.muted}>{pace < 1 ? 'Below 1 means your blood age is rising slower than real time — aging slower.' : 'Above 1 means faster than real time.'} DunedinPACE (methylation) is the gold-standard measure.</T> : <T v="small" color={p.muted}>Needs at least two blood panels a few months apart.</T>}
      </Card>
      {ages.map((a) => (
        <Card key={a.label}>
          <Row>
            <View style={{ flex: 1 }}><T v="body">{a.label}</T><T v="small" color={p.muted}>{a.note}</T></View>
            <View style={{ alignItems: 'flex-end' }}>
              <T v="num" style={{ fontSize: 18 }} color={col(a.delta)}>{a.value != null ? Math.round(a.value) : '—'}</T>
              <T v="small" color={col(a.delta)}>{a.delta == null ? '' : a.delta < 0 ? `${Math.abs(Math.round(a.delta))} yr younger` : a.delta < 1 ? 'about your age' : `${Math.round(a.delta)} yr older`}</T>
            </View>
          </Row>
        </Card>
      ))}
    </Section>
  );
}
