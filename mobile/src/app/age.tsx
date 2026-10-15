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

      <Card style={{ alignItems: 'center', gap: space[2] }}>
        <Dial value={ac.overall?.years ?? null} chrono={ac.chrono} confidence={ac.overall ? (ac.overall.confidence === 'high' ? 1 : ac.overall.confidence === 'medium' ? 0.6 : 0.3) : 0} />
        {ac.overall ? (
          <View style={{ alignItems: 'center' }}>
            <T v="h2" color={deltaColor(ac.overall.delta)}>{Math.round(ac.overall.years)} yr</T>
            <T v="small">{deltaText(ac.overall.delta)}{ac.chrono ? ` · you are ${ac.chrono}` : ''} · {ac.overall.confidence} confidence</T>
          </View>
        ) : (
          <T v="small">Connect the ring, patch or Apple Health to see your wearable biological age.</T>
        )}
      </Card>

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
        <T v="small">A measured VO₂max from Apple Health makes Fitness age far more accurate than the resting-HR estimate. For Recovery age, wear the ECG patch or ring at rest or overnight so HRV is measured cleanly. Readings taken while moving are noisier and count less.</T>
      </Card>
    </Screen>
  );
}
