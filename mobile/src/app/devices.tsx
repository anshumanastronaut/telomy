// Devices hub: every source (chest patch, smart ring, Apple Health), what each provides, and a side-by-side comparison
// of metrics measured by more than one device — showing which reading Telomy uses and how closely they agree.
// Works with one device or none; nothing here fails when a device is absent.
import { router, Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';
import { connectHealth } from '@/lib/health';
import { METRIC_SOURCES, SOURCE_LABEL, useDevices, type SourceId } from '@/lib/devices';
import { Ring } from '../../modules/ky-ecg';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

const ICON: Record<SourceId, any> = { patch: 'waveform.path.ecg', ring: 'circle.circle', health: 'heart.text.square' };
const UNIT: Record<string, string> = { hr: 'bpm', hrv: 'ms', spo2: '%', skinTemp: '°C', steps: '', vo2max: '' };
const LABEL: Record<string, string> = { hr: 'Heart rate', hrv: 'HRV', spo2: 'SpO₂', skinTemp: 'Skin temp', steps: 'Steps', vo2max: 'VO₂max' };

export default function Devices() {
  const p = usePalette();
  const { toast, show } = useToast();
  const d = useDevices();

  const compareRows = Object.entries(d.live).filter(([, f]) => f.value != null && (METRIC_SOURCES[Object.keys(d.live).find((k) => d.live[k] === f)!] ?? []).length > 1);

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Devices' }} />
        <T v="small">Telomy combines your devices and uses the most accurate source for each measurement. It works with one device, and keeps working when any are missing.</T>

        <Section title="Your devices">
          {d.devices.map((dev) => (
            <Card key={dev.id} tone={dev.connected ? 'teal' : undefined}>
              <Row>
                <Icon name={ICON[dev.id]} color={dev.connected ? p.teal : p.faint} />
                <View style={{ flex: 1 }}>
                  <T v="h3">{dev.label}</T>
                  <T v="small">{dev.detail}</T>
                </View>
                {!dev.connected ? (
                  <Button kind="secondary" title="Connect"
                    onPress={() => {
                      if (dev.id === 'ring') { Ring.scan(); show('Searching for your ring…'); }
                      else if (dev.id === 'health') connectHealth().then((r) => show(r.ok ? 'Apple Health connected.' : 'Not connected.', r.ok ? 'success' : 'alert'));
                      else router.push('/monitor');
                    }} />
                ) : <Icon name="checkmark.circle.fill" color={p.success} />}
              </Row>
              <T v="small" color={p.muted}>Provides: {metricsOf(dev.id).join(' · ')}</T>
            </Card>
          ))}
        </Section>

        <Section title="What Telomy is using now">
          <Card style={{ gap: space[3] }}>
            {Object.entries(d.live).filter(([, f]) => f.value != null).map(([k, f]) => (
              <View key={k} style={{ gap: 2 }}>
                <Row>
                  <T v="body" style={{ flex: 1 }}>{LABEL[k] ?? k}</T>
                  <T v="num" style={{ fontSize: 18 }}>{fmt(k, f.value!)} <T v="small">{UNIT[k]}</T></T>
                </Row>
                <Row gap={6}>
                  <T v="small" color={p.teal}>via {SOURCE_LABEL[f.source!]}</T>
                  {f.others.map((o) => <T key={o.source} v="small" color={p.muted}>· {SOURCE_LABEL[o.source]} {fmt(k, o.value)}{agree(k, f.value!, o.value)}</T>)}
                </Row>
              </View>
            ))}
            {!Object.values(d.live).some((f) => f.value != null) ? <T v="small">No live readings yet. Connect a device above.</T> : null}
          </Card>
        </Section>

        <Card>
          <T v="label">How sources are ranked</T>
          <T v="small">Heart rate & HRV: ECG patch is most accurate, then the ring (optical), then Apple Health. SpO₂ & skin temperature: the ring. Steps, workouts & VO₂max: Apple Health. Rhythm screening & sleep stages: the ECG patch. When two devices disagree a lot, Telomy flags the lower-quality one.</T>
        </Card>
      </Screen>
      {toast}
    </View>
  );
}

function metricsOf(id: SourceId): string[] {
  const names: Record<string, string> = { hr: 'HR', hrv: 'HRV', ecg: 'ECG', rhythm: 'rhythm', spo2: 'SpO₂', skinTemp: 'temp', respRate: 'breathing', motion: 'motion', steps: 'steps', distanceKm: 'distance', activeKcal: 'energy', workouts: 'workouts', vo2max: 'VO₂max', sleepStages: 'sleep' };
  return Object.entries(METRIC_SOURCES).filter(([, ss]) => ss[0] === id || ss.includes(id)).filter(([, ss]) => ss[0] === id).map(([m]) => names[m] ?? m);
}
function fmt(k: string, v: number) { return k === 'skinTemp' ? v.toFixed(1) : k === 'steps' ? Math.round(v).toLocaleString('en-IN') : `${Math.round(v)}`; }
function agree(k: string, a: number, b: number) {
  if (k === 'steps' || k === 'vo2max') return '';
  const diff = Math.abs(a - b);
  const tol = k === 'hr' ? 5 : k === 'hrv' ? 10 : k === 'spo2' ? 2 : k === 'skinTemp' ? 0.5 : 5;
  return diff <= tol ? ' ✓' : ' ⚠︎';
}
