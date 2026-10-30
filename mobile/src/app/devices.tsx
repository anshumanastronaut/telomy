// Devices hub: every source (chest patch, smart ring, Apple Health), what each provides, and a side-by-side comparison
// of metrics measured by more than one device — showing which reading Telomy uses and how closely they agree.
// Works with one device or none; nothing here fails when a device is absent.
import { router, Stack } from 'expo-router';
import React from 'react';
import { Platform, View } from 'react-native';
import { HEALTH_LABEL, connectHealth } from '@/lib/health';
import { METRIC_SOURCES, SOURCE_LABEL, useDevices, type SourceId } from '@/lib/devices';
import { hrHrvCorrelation, useRingHistory } from '@/lib/ringhistory';
import { Band, Ring } from '../../modules/ky-ecg';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

const ICON: Record<SourceId, any> = { patch: 'waveform.path.ecg', ring: 'circle.circle', jcvital: 'dot.radiowaves.left.and.right', health: 'heart.text.square' };
const UNIT: Record<string, string> = { hr: 'bpm', hrv: 'ms', spo2: '%', skinTemp: '°C', steps: '', vo2max: '' };
const LABEL: Record<string, string> = { hr: 'Heart rate', hrv: 'HRV', spo2: 'SpO₂', skinTemp: 'Skin temp', steps: 'Steps', vo2max: 'VO₂max' };

export default function Devices() {
  const p = usePalette();
  const { toast, show } = useToast();
  const d = useDevices();
  const rh = useRingHistory();
  const coupling = hrHrvCorrelation();
  const [autoRec, setAutoRec] = React.useState(Band.autoRecord());

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
                      else if (dev.id === 'health') connectHealth().then((r) => show(r.ok ? `${HEALTH_LABEL} connected.` : (r.error || 'Not connected.'), r.ok ? 'success' : 'alert'));
                      else router.push('/monitor');
                    }} />
                ) : <Icon name="checkmark.circle.fill" color={p.success} />}
              </Row>
              <T v="small" color={p.muted}>Provides: {metricsOf(dev.id).join(' · ')}</T>
            </Card>
          ))}
        </Section>

        <Section title="Coming to Telomy">
          {[
            { icon: 'drop.circle', name: 'Continuous glucose monitor (CGM)', body: 'Glucose every few minutes: meal responses, overnight lows, and time-in-range alongside your sleep, stress and recovery. Integration in progress with the manufacturer.' },
            { icon: 'figure.strengthtraining.traditional', name: 'Telomy Muscle band (EMG)', body: 'Muscle activation and fatigue from surface EMG — powers the Muscle age test and adds muscular load to Strain. In development.' },
          ].map((x) => (
            <Card key={x.name}>
              <Row>
                <Icon name={x.icon as any} color={p.faint} />
                <View style={{ flex: 1 }}><T v="h3">{x.name}</T><T v="small">{x.body}</T></View>
                <Chip label="Soon" />
              </Row>
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
                <Row gap={6} style={{ flexWrap: 'wrap' }}>
                  <T v="small" color={p.teal}>via {SOURCE_LABEL[f.source!]}</T>
                  {f.others.map((o) => <T key={o.source} v="small" color={p.muted}>· {SOURCE_LABEL[o.source]} {fmt(k, o.value)}{agree(k, f.value!, o.value)}</T>)}
                </Row>
              </View>
            ))}
            {!Object.values(d.live).some((f) => f.value != null) ? <T v="small">No live readings yet. Connect a device above.</T> : null}
          </Card>
        </Section>

        {rh.count > 0 ? (
          <Section title="Ring longitudinal data">
            <Card style={{ gap: space[2] }}>
              <Row>
                <T v="body" style={{ flex: 1 }}>Samples logged</T>
                <T v="num" style={{ fontSize: 18 }}>{rh.count.toLocaleString('en-IN')}</T>
              </Row>
              <T v="small" color={p.muted}>The ring measures itself every few minutes and Telomy syncs the log while connected — continuous HR, HRV, SpO₂ and temperature kept on this phone only.</T>
              {coupling.r != null ? (
                <View style={{ gap: 2 }}>
                  <Row>
                    <T v="body" style={{ flex: 1 }}>HR ↔ HRV coupling</T>
                    <T v="num" style={{ fontSize: 18 }} color={coupling.r < 0 ? p.teal : p.copper}>r = {coupling.r.toFixed(2)}</T>
                  </Row>
                  <T v="small" color={p.muted}>Across {coupling.n} paired samples. HR and HRV come from the same beat-to-beat intervals, so a negative r (higher HR ↔ lower HRV) is expected and confirms the ring's optical pulse detection is tracking real physiology — the same relationship the ECG patch shows.</T>
                </View>
              ) : (
                <T v="small" color={p.muted}>Collecting paired HR + HRV samples to measure the HR↔HRV relationship and cross-check it against the patch.</T>
              )}
            </Card>
          </Section>
        ) : null}

        <Card style={{ gap: space[2] }}>
          <Row>
            <View style={{ flex: 1 }}>
              <T v="label">Record the patch continuously</T>
              <T v="small">While the patch is on your skin, Telomy saves rolling 2-hour ECG records (not just the live view), hands over to the overnight recording when you fall asleep, and keeps raw records for 14 days. Per-minute summaries are kept for good.</T>
            </View>
            <Button kind={autoRec ? 'primary' : 'secondary'} title={autoRec ? 'On' : 'Off'} onPress={() => { Band.setAutoRecord(!autoRec); setAutoRec(!autoRec); }} />
          </Row>
        </Card>

        {Platform.OS === 'android' ? (
          <Card onPress={() => router.push('/galaxy' as any)} accessibilityLabel="Galaxy Watch">
            <Row gap={space[2]} style={{ alignItems: 'center' }}>
              <Icon name="applewatch" size={20} color={p.teal} />
              <View style={{ flex: 1 }}>
                <T v="label">Galaxy Watch</T>
                <T v="small" color={p.muted}>Heart rate, SpO₂, sleep, steps, VO₂max and body composition from Samsung Health.</T>
              </View>
              <Icon name="chevron.right" size={13} color={p.faint} />
            </Row>
          </Card>
        ) : null}

        <Card onPress={() => router.push('/jcvital' as any)} accessibilityLabel="JCVital V8 band">
          <Row gap={space[2]} style={{ alignItems: 'center' }}>
            <Icon name="dot.radiowaves.left.and.right" size={20} color={p.teal} />
            <View style={{ flex: 1 }}>
              <T v="label">JCVital V8 band</T>
              <T v="small" color={p.muted}>Connect the JCVital/JSTYLE band — live vitals + raw ECG/PPG via its official SDK.</T>
            </View>
            <Icon name="chevron.right" size={13} color={p.faint} />
          </Row>
        </Card>

        <Card>
          <T v="label">How sources are ranked</T>
          <T v="small">Heart rate & HRV: ECG patch is most accurate, then the ring (optical), then phone health (Apple Health / Health Connect). SpO₂ & skin temperature: the ring. Steps, workouts & VO₂max: phone health. Rhythm screening & sleep stages: the ECG patch. When two devices disagree a lot, Telomy flags the lower-quality one.</T>
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
