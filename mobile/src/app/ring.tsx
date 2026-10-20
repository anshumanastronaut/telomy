// Smart ring (TK3040B9 / Yucheng YCBT) — clean-room local connection. Reads HR, SpO2, temperature and motion on the
// phone; uploads nothing. Blood pressure / glucose from this ring are not real measurements and are not shown.
import { Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Ring, type RingStatus } from '../../modules/ky-ecg';
import { space, usePalette, data } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function RingScreen() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [s, setS] = useState<RingStatus | null>(Ring.status());
  const [auto, setAuto] = useState(Ring.autoSleep());
  useEffect(() => {
    const a = Ring.onStatus(setS), b = Ring.onData(setS);
    setS(Ring.status());
    return () => { a.remove(); b.remove(); };
  }, []);
  const connected = s?.state === 'connected';

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Smart ring' }} />
        <Card tone={connected ? 'teal' : 'copper'}>
          <Row>
            <Icon name="circle.circle" color={connected ? p.teal : p.copper} />
            <View style={{ flex: 1 }}>
              <T v="h3">{connected ? `Connected${s?.battery >= 0 ? ` · ${s.battery}%` : ''}` : s?.state === 'scanning' ? 'Searching…' : 'Not connected'}</T>
              <T v="small">{connected ? 'Reading on this phone only. Nothing is uploaded.' : 'Take the ring off the other app first, then connect.'}</T>
            </View>
          </Row>
          <Row style={{ flexWrap: 'wrap' }}>
            {!connected ? <Button title={s?.state === 'scanning' ? 'Scanning…' : 'Connect ring'} icon="magnifyingglass" onPress={() => { Ring.scan(); show('Searching for your ring…'); }} /> : null}
            {connected ? <Button kind="secondary" title="Battery" icon="battery.50" onPress={() => Ring.readBattery()} /> : null}
            {s?.rememberedId ? <Button kind="ghost" title="Forget" onPress={() => Ring.forget()} /> : null}
          </Row>
        </Card>

        {connected ? (
          <Section title="Live readings">
            <Row gap={space[3]}>
              <Metric icon="heart.fill" color={p.danger} label="Heart rate" value={s?.hr ? `${s.hr}` : '—'} unit="bpm" onPress={() => { Ring.startMeasure(0); show('Measuring heart rate…'); }} />
              <Metric icon="drop.fill" color={data.spo2} label="SpO₂" value={s?.spo2 ? `${s.spo2}` : '—'} unit="%" onPress={() => { Ring.startMeasure(2); show('Measuring SpO₂…'); }} />
            </Row>
            <Row gap={space[3]}>
              <Metric icon="thermometer.medium" color={p.copper} label="Skin temp" value={s?.temp ? s.temp.toFixed(1) : '—'} unit="°C" onPress={() => { Ring.startMeasure(4); show('Measuring temperature…'); }} />
              <View style={{ flex: 1 }} />
            </Row>
            <T v="small">Tap a card to take a fresh reading (hold still ~30 s). These add extra signals to your Telomy scores; the ring's motion sensor will also sharpen sleep staging.</T>
          </Section>
        ) : null}

        {connected ? (
          <Section title="Tonight's sleep">
            <Card tone={s?.overnight ? 'teal' : undefined} style={{ gap: space[2] }}>
              <Row><Icon name="moon.stars.fill" color={p.teal} /><T v="h3" style={{ flex: 1 }}>{s?.overnight ? 'Tracking your sleep' : 'Track tonight with the ring'}</T></Row>
              <T v="small">Heart rate every few seconds and every movement, all night. When you've been still, the ring takes SpO₂ (every 15 min) and temperature (every 30 min) — still moments give the cleanest readings. Keeps running with the screen locked; stops itself at 9 am. Starting an Overnight sleep session on the patch starts this too.</T>
              {s?.overnight ? (
                <>
                  <T v="small" color={p.teal}>{[s?.hr ? `HR ${s.hr}` : null, s?.spo2 ? `SpO₂ ${s.spo2}%` : null, s?.temp ? `${s.temp.toFixed(1)} °C` : null, s?.rawCounts?.sport ? `${s.rawCounts.sport} motion frames` : null].filter(Boolean).join(' · ') || 'Waiting for first readings…'}</T>
                  <Button kind="secondary" title="Stop & sync the night" icon="sun.max" onPress={() => { Ring.stopOvernight(); show("Syncing the ring's night…", 'success'); }} />
                </>
              ) : <Button title="Start sleep tracking" icon="moon.zzz" onPress={() => { Ring.startOvernight(); show('Sleep tracking started. Good night.'); }} />}
              <Row>
                <View style={{ flex: 1 }}>
                  <T v="body" style={{ fontWeight: '600' }}>Detect sleep automatically</T>
                  <T v="small" color={p.muted}>Starts when the patch or ring sees you fall asleep after 9 pm, stops once you're up and moving in the morning.</T>
                </View>
                <Button kind={auto ? 'primary' : 'secondary'} title={auto ? 'On' : 'Off'} onPress={() => { Ring.setAutoSleep(!auto); setAuto(!auto); }} />
              </Row>
              {s?.battery != null && s.battery >= 0 && s.battery < 40 && !s?.overnight ? <T v="small" color={p.warn}>Ring battery {s.battery}% — charge it first so it lasts the night.</T> : null}
            </Card>
          </Section>
        ) : null}

        {connected ? (
          <Section title="Raw signal capture (research)">
            <Card style={{ gap: space[2] }}>
              <T v="small">Streams the ring's raw ECG, optical pulse (PPG + beat intervals) and motion sensor to a file on this phone, for validating the ring against the ECG patch. Sit still with the ring snug; for ECG, touch the ring's top electrode with a finger of the other hand.</T>
              <Row style={{ flexWrap: 'wrap' }}>
                {!s?.capturing ? (
                  <>
                    <Button title="Capture all" icon="record.circle" onPress={() => { Ring.startRaw({ ecg: true, imu: true, ppg: true }); show('Capturing raw streams…'); }} />
                    <Button kind="secondary" title="ECG only" onPress={() => Ring.startRaw({ ecg: true, imu: false, ppg: false })} />
                  </>
                ) : <Button kind="copper" title="Stop capture" icon="stop.circle" onPress={() => { Ring.stopRaw(); show('Saved to ring-raw on this phone.', 'success'); }} />}
              </Row>
              {s?.rawCounts ? (
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', rowGap: 6 }}>
                  {Object.entries(s.rawCounts).map(([k, n]) => (
                    <View key={k} style={{ width: '33%' }}><T v="small">{k}</T><T v="body" style={{ fontWeight: '600' }}>{n}</T></View>
                  ))}
                </View>
              ) : s?.capturing ? <T v="small" color={p.muted}>Waiting for frames… a stream that stays at zero isn't supported by this ring.</T> : null}
              {s?.capturing && s?.hrv ? <T v="small" color={p.teal}>Live HRV from the ring's beat intervals: {s.hrv} ms (RMSSD)</T> : null}
            </Card>
          </Section>
        ) : null}

        <Card>
          <T v="label">About this ring</T>
          <T v="small">Blood pressure and “blood glucose” shown by the ring’s own app are not real sensor measurements and are never stored or shown here. Telomy uses only heart rate, HRV, SpO₂, temperature and motion.</T>
        </Card>
      </Screen>
      {toast}
    </View>
  );
}

function Metric({ icon, color, label, value, unit, onPress }: { icon: any; color: string; label: string; value: string; unit: string; onPress: () => void }) {
  const p = usePalette();
  return (
    <Card style={{ flex: 1 }} onPress={onPress}>
      <Row gap={6}><Icon name={icon} size={14} color={color} /><T v="label" style={{ flex: 1 }}>{label}</T></Row>
      <Row gap={4} style={{ alignItems: 'baseline' }}><T v="num" style={{ fontSize: 26 }}>{value}</T><T v="small">{unit}</T></Row>
      <T v="small" color={p.teal}>Measure</T>
    </Card>
  );
}
