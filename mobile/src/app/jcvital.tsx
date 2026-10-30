// JCVital V8 band — pairing + live status. The band now streams continuously into your longitudinal record (like
// the ring/patch): once paired it auto-connects whenever Telomy is open and its HR / SpO2 / skin-temp / steps go to
// the vault via lib/vitalsync.ts. No manual capture. Source: lib/jcvitalsource.ts.
import { Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';

import { JCVital, type JcSnapshot } from '@/lib/jcvitalsource';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

type Dev = { id: string; name: string };

export default function JCVitalScreen() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [jc, setJc] = useState<JcSnapshot>(JCVital.status());
  const [paired, setPaired] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [devices, setDevices] = useState<Dev[]>([]);

  useEffect(() => {
    const s = JCVital.on(setJc); setJc(JCVital.status());
    JCVital.isPaired().then(setPaired);
    JCVital.autoConnect();
    return () => { s.remove(); JCVital.stopScan(); };
  }, []);

  function scan() {
    setDevices([]); setScanning(true);
    JCVital.scan((d: any) => setDevices((prev) => prev.some((x) => x.id === d.id) ? prev : [...prev, { id: d.id, name: d.name || d.localName || '(band)' }]));
    setTimeout(() => { JCVital.stopScan(); setScanning(false); }, 8000);
  }
  async function connect(id: string) { await JCVital.connect(id); setPaired(true); setDevices([]); show('Paired — it will auto-connect from now on.'); }
  async function forget() { await JCVital.forget(); setPaired(false); show('Band forgotten.'); }

  const fresh = jc.connected && Date.now() - jc.at < 15000;

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'JCVital V8 band' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">JCVital V8</T>
        <T v="small" color={p.muted}>Streams continuously into your record like the ring — once paired it auto-connects whenever Telomy is open. Forget it from the JCVital app first (it pairs to one app at a time).</T>
      </View>

      <Card tone={jc.connected ? 'teal' : 'copper'}>
        <Row>
          <Icon name="dot.radiowaves.left.and.right" color={jc.connected ? p.teal : p.copper} />
          <View style={{ flex: 1 }}>
            <T v="label">{jc.connected ? (fresh ? 'Streaming' : 'Connected') : paired ? 'Paired — connecting…' : 'Not paired'}</T>
            <T v="small" color={p.muted}>{jc.connected ? 'HR, SpO₂, skin temp and steps are syncing to your vault.' : paired ? 'Put the band on and keep this app open.' : 'Scan and tap your band to pair.'}</T>
          </View>
          {!paired ? <Button kind="secondary" title={scanning ? 'Scanning…' : 'Scan'} onPress={scan} disabled={scanning} /> : null}
        </Row>
      </Card>

      {!paired && devices.length ? (
        <Section title="Found devices">
          {devices.map((d) => (
            <Pressable key={d.id} onPress={() => connect(d.id)}>
              <Card style={{ marginBottom: space[2] }}><Row><T v="body" style={{ flex: 1 }}>{d.name}</T><T v="small" color={p.faint}>{d.id.slice(0, 8)}</T></Row></Card>
            </Pressable>
          ))}
        </Section>
      ) : null}

      {jc.connected ? (
        <Card style={{ gap: space[2] }}>
          <T v="label">Live</T>
          <Row style={{ justifyContent: 'space-between' }}>
            <Metric label="Heart rate" value={jc.hr} unit="bpm" p={p} />
            <Metric label="SpO₂" value={jc.spo2} unit="%" p={p} />
            <Metric label="Skin temp" value={jc.temp} unit="°C" p={p} />
            <Metric label="Steps" value={jc.steps} unit="" p={p} />
          </Row>
          <T v="small" color={p.faint}>SpO₂ is shown as a rolling median (optical SpO₂ is noisy per reading).</T>
        </Card>
      ) : null}

      {paired ? <Button kind="secondary" title="Forget this band" onPress={forget} /> : null}
      {toast}
    </Screen>
  );
}

function Metric({ label, value, unit, p }: { label: string; value?: number; unit: string; p: any }) {
  return (
    <View style={{ alignItems: 'center', flex: 1 }}>
      <T v="small" color={p.muted}>{label}</T>
      <T v="num" style={{ fontSize: 22 }} color={value != null ? p.teal : p.faint}>{value ?? '—'}</T>
      {unit ? <T v="small" color={p.faint}>{unit}</T> : null}
    </View>
  );
}
