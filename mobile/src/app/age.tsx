// Wearable biological age — Fitness, Recovery (autonomic) and Cardiac clocks computed on-device from the connected
// patch / ring / Apple Health. Complements the blood-based PhenoAge on the Longevity screen. Works with whatever is
// connected: each clock that lacks its input shows what to connect instead of a number, and nothing here fails when a
// device is missing.
import { router, Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';
import { useApi } from '@/lib/api';
import { ageClocks, type Clock } from '@/lib/ageclocks';
import { useDevices } from '@/lib/devices';
import { useHealth } from '@/lib/health';
import { space, usePalette } from '@/lib/theme';
import { Dial } from '@/ui/charts';
import { Card, Icon, Row, Screen, Section, T } from '@/ui/core';

const ICON: Record<Clock['key'], any> = { fitness: 'figure.run', autonomic: 'bolt.heart', cardiac: 'heart.fill', muscle: 'figure.strengthtraining.traditional' };

export default function AgeScreen() {
  const p = usePalette();
  const prof = useApi<any>('/profile');
  const bio = useApi<any>('/bioage');
  const twin = useApi<any>('/twin');
  const almi = twin.data?.systems?.flatMap((s: any) => s.variables).find((v: any) => v.key === 'almi')?.value ?? null;
  const d = useDevices();
  const health = useHealth(2);

  const hrvFused = d.live.hrv;
  const inputs = {
    age: prof.data?.age ?? null,
    sex: (prof.data?.sex as 'male' | 'female' | undefined) ?? null,
    restingHr: health.today?.restingHr ?? null,
    hrvRmssd: hrvFused.source === 'patch' || hrvFused.source === 'ring' ? hrvFused.value : null,
    hrvSdnn: health.today?.hrvSdnn ?? null,
    vo2max: health.today?.vo2max ?? null,
    almi,
  };
  const ac = ageClocks(inputs);

  const deltaColor = (delta: number | null) => (delta == null ? p.muted : delta <= -1 ? p.teal : delta >= 2 ? p.copper : p.text);
  const deltaText = (delta: number | null) =>
    delta == null ? '' : Math.abs(delta) < 1 ? 'about your age' : `${Math.abs(Math.round(delta))} yr ${delta < 0 ? 'younger' : 'older'}`;

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Biological age' }} />
      <T v="small">Estimated from your connected devices — fitness, heart-rate variability and resting heart rate — against population norms for your age and sex. These are physiological estimates, not a diagnosis, and sit alongside the blood-based PhenoAge on the Longevity screen.</T>

      <ValidatedAges data={bio.data} deltaColor={deltaColor} deltaText={deltaText} />

      <Section title="Wearable clocks">
      <Card style={{ alignItems: 'center', gap: space[2] }}>
        <Dial value={ac.overall?.years ?? null} chrono={ac.chrono} confidence={ac.overall ? (ac.overall.confidence === 'high' ? 1 : ac.overall.confidence === 'medium' ? 0.6 : 0.3) : 0} />
        {ac.overall ? (
          <View style={{ alignItems: 'center' }}>
            <T v="h2" color={deltaColor(ac.overall.delta)}>{Math.round(ac.overall.years)} yr</T>
            <T v="small">{deltaText(ac.overall.delta)}{ac.chrono ? ` · you are ${ac.chrono}` : ''} · {ac.overall.confidence} confidence</T>
          </View>
        ) : (
          <T v="small">Connect the ring, patch or your phone's health app to see your wearable biological age.</T>
        )}
      </Card>
      </Section>

      <Section title="By system">
        {ac.clocks.map((c) => (
          <Card key={c.key} onPress={c.key === 'muscle' ? () => router.push('/muscle') : undefined}>
            <Row>
              <Icon name={ICON[c.key]} color={c.years != null ? deltaColor(c.delta) : p.faint} />
              <View style={{ flex: 1 }}>
                <T v="h3">{c.label}</T>
                <T v="small">{c.years != null ? c.basis : 'Not enough data yet'}</T>
              </View>
              {c.years != null ? (
                <View style={{ alignItems: 'flex-end' }}>
                  <T v="num" style={{ fontSize: 22 }} color={deltaColor(c.delta)}>{Math.round(c.years)}</T>
                  <T v="small" color={deltaColor(c.delta)}>{deltaText(c.delta)}</T>
                </View>
              ) : null}
            </Row>
            <T v="small" color={p.muted}>{c.note}{c.years != null && c.confidence ? ` · ${c.confidence} confidence` : ''}</T>
            {c.key === 'muscle' ? <T v="small" color={p.teal}>See the EMG muscle test →</T> : null}
          </Card>
        ))}
      </Section>

      <Card>
        <T v="label">How to sharpen these</T>
        <T v="small">A measured VO₂max from your phone's health app makes Fitness age far more accurate than the resting-HR estimate. For Recovery age, wear the ECG patch or ring at rest or overnight so HRV is measured cleanly. Readings taken while moving are noisier and count less.</T>
      </Card>
    </Screen>
  );
}

function ValidatedAges({ data, deltaColor, deltaText }: { data: any; deltaColor: (d: number | null) => string; deltaText: (d: number | null) => string }) {
  const p = usePalette();
  if (!data?.ok) return null;
  const b = data.blood ?? {};
  const rows: { label: string; value: number | null; delta: number | null; note: string }[] = [];
  if (b.phenoage?.available) rows.push({ label: 'PhenoAge (blood)', value: b.phenoage.value, delta: b.phenoage.delta, note: 'Mortality-based · Levine 2018 · NHANES r 0.92' });
  if (b.kdm?.available) rows.push({ label: 'KDM biological age', value: b.kdm.value, delta: b.kdm.delta, note: `Clinical biomarkers · ${b.kdm.markers_used} markers · NHANES-fitted` });
  if (data.heart?.available) rows.push({ label: 'Heart / vascular age', value: data.heart.value, delta: data.heart.delta, note: `From 10-yr CVD risk ${data.heart.ten_year_cvd_risk_pct}%` });
  if (data.muscle?.available) rows.push({ label: 'Muscle age', value: data.muscle.value, delta: data.muscle.delta, note: data.muscle.basis });
  if (data.fitness?.available) rows.push({ label: 'Fitness age', value: data.fitness.value, delta: data.fitness.delta, note: `VO₂max ${data.fitness.vo2max}` });
  if (!rows.length) return null;
  return (
    <Section title="Validated biological ages">
      <T v="small" color={p.muted}>Blood, heart and body ages from your Vault — each a published method, validated on NHANES population data. You are {data.chronological_age}.</T>
      {rows.map((r) => (
        <Card key={r.label}>
          <Row>
            <View style={{ flex: 1 }}><T v="h3">{r.label}</T><T v="small" color={p.muted}>{r.note}</T></View>
            <View style={{ alignItems: 'flex-end' }}>
              <T v="num" style={{ fontSize: 22 }} color={deltaColor(r.delta)}>{r.value != null ? Math.round(r.value) : '—'}</T>
              <T v="small" color={deltaColor(r.delta)}>{deltaText(r.delta)}</T>
            </View>
          </Row>
        </Card>
      ))}
      {data.blood?.homeostatic_dysregulation?.available ? (
        <T v="small" color={p.muted}>Homeostatic dysregulation (how far your biomarkers sit from a young-healthy reference): {data.blood.homeostatic_dysregulation.log_mahalanobis} — lower is better.</T>
      ) : null}
    </Section>
  );
}
