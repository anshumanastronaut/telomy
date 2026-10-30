// JCVital V8 Pro band — Telomy integration (research/capture). Connects over BLE (react-native-ble-plx via the
// vendor's MIT BleManager) and decodes with the official @yhmedical/ms-data-sdk (BleSDK). Shows the band's live
// parsed vitals AND its raw ECG/PPG, and can capture a labelled session to /cal — so we can train Telomy's engine
// against the band's raw signals and benchmark it against the vendor's own ECGSignalProcessor.
// The band bonds to ONE app at a time — forget it from the JCVital app before connecting here.
import { Stack } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { Pressable, View } from 'react-native';
import Svg, { Polyline } from 'react-native-svg';
import { BleSDK } from '@yhmedical/ms-data-sdk';

import { bleManager } from '@/lib/jcvital/BleManager';
import Constants from '@/lib/jcvital/constants';
import { api } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

type Dev = { id: string; name: string };

export default function JCVital() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [ready, setReady] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [connected, setConnected] = useState(bleManager.isConnected());
  const [devices, setDevices] = useState<Dev[]>([]);
  const [parsed, setParsed] = useState<Record<string, any>>({});
  const [ecgN, setEcgN] = useState(0);
  const [wave, setWave] = useState<number[]>([]);
  const [measuring, setMeasuring] = useState(false);
  const [capturing, setCapturing] = useState(false);

  const session = useRef('');
  const buf = useRef<any[]>([]);
  const measuringRef = useRef(false);

  useEffect(() => {
    bleManager.deviceType = 'V8';
    const onState = (c: boolean) => { setConnected(c); if (c) show('Band connected'); };
    const onParsed = (d: any) => {
      if (d && typeof d === 'object') {
        setParsed((prev) => ({ ...prev, ...d }));
        if (capturing && session.current) pushVitals(d);
      }
    };
    const onRaw = (bytes: number[]) => {
      if (!bytes || bytes.length < 2) return;
      const type = bytes[1];
      // 0x28 = ECG start ack → begin the waveform stream
      if (type === 0x28) { safeWrite(BleSDK.realECGWave(measuringRef.current)); return; }
      // 0x07 = ECG/PPG raw frame: 2-byte header, then 3 bytes per sample
      if (type === 0x07 && bytes.length > 2) {
        const samples: number[] = [];
        for (let b = 2; b + 2 < bytes.length; b += 3) {
          samples.push((bytes[b] << 16) | (bytes[b + 1] << 8) | bytes[b + 2]);
        }
        if (samples.length) {
          setEcgN((n) => n + samples.length);
          setWave((w) => [...w, ...samples].slice(-180));
          if (capturing && session.current) {
            for (const s of samples) buf.current.push({ t: Date.now() / 1000, source: 'jcvital', channel: 'ecg_raw', v: s });
          }
        }
      }
    };
    bleManager.on(Constants.BLUE_CONNECTION_STATE, onState);
    bleManager.on(Constants.BLUE_DATA_RECEIVED, onParsed);
    bleManager.on('dataByteCallBack', onRaw);
    bleManager.init().then((ok: boolean) => setReady(ok)).catch(() => setReady(false));
    const flush = setInterval(() => void uploadBuffer(), 2500);
    return () => {
      bleManager.off(Constants.BLUE_CONNECTION_STATE, onState);
      bleManager.off(Constants.BLUE_DATA_RECEIVED, onParsed);
      bleManager.off('dataByteCallBack', onRaw);
      clearInterval(flush);
      bleManager.stopScan();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [capturing]);

  function safeWrite(cmd: number[]) { try { bleManager.writeData(cmd); } catch {} }
  function pushVitals(d: any) {
    for (const [k, v] of Object.entries(d)) {
      if (typeof v === 'number') buf.current.push({ t: Date.now() / 1000, source: 'jcvital', channel: k, v });
    }
  }
  async function uploadBuffer() {
    if (!session.current || !buf.current.length) return;
    const readings = buf.current.splice(0, buf.current.length);
    try { await api('/cal/ingest', { body: { session_id: session.current, readings }, queue: true }); } catch {}
  }

  function scan() {
    setDevices([]); setScanning(true);
    bleManager.startScan((d: any) => {
      setDevices((prev) => prev.some((x) => x.id === d.id) ? prev : [...prev, { id: d.id, name: d.name || d.localName || '(band)' }]);
    });
    setTimeout(() => { bleManager.stopScan(); setScanning(false); }, 8000);
  }
  function connect(id: string) { bleManager.stopScan(); setScanning(false); bleManager.connectDeviceById(id); }
  function toggleMeasure() {
    const next = !measuring; setMeasuring(next); measuringRef.current = next;
    safeWrite(BleSDK.healthMeasurementWithDataType(0x04, next, null));   // 0x04 = ECG/PPG
    if (!next) setWave([]);
  }
  function startCapture() {
    session.current = `jcvital-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}`;
    buf.current = []; setCapturing(true); show('Capturing to /cal…');
  }
  async function stopCapture() { setCapturing(false); await uploadBuffer(); show('Saved session to /cal.', 'success'); }

  const metrics = Object.entries(parsed).filter(([, v]) => typeof v === 'number' || typeof v === 'string').slice(0, 12);

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'JCVital V8 band' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">JCVital V8</T>
        <T v="small" color={p.muted}>Official SDK (@yhmedical/ms-data-sdk) over BLE. Forget the band from the JCVital app first — it pairs to one app at a time.</T>
      </View>

      <Card tone={connected ? 'teal' : 'copper'}>
        <Row>
          <Icon name="dot.radiowaves.left.and.right" color={connected ? p.teal : p.copper} />
          <View style={{ flex: 1 }}>
            <T v="label">{connected ? 'Connected' : ready ? 'Ready' : 'Turn on Bluetooth'}</T>
            <T v="small" color={p.muted}>{connected ? 'Streaming — start a measurement below.' : 'Scan and tap your band.'}</T>
          </View>
          {!connected ? <Button kind="secondary" title={scanning ? 'Scanning…' : 'Scan'} onPress={scan} disabled={!ready || scanning} /> : null}
        </Row>
      </Card>

      {!connected && devices.length ? (
        <Section title="Found devices">
          {devices.map((d) => (
            <Pressable key={d.id} onPress={() => connect(d.id)}>
              <Card style={{ marginBottom: space[2] }}><Row><T v="body" style={{ flex: 1 }}>{d.name}</T><T v="small" color={p.faint}>{d.id.slice(0, 8)}</T></Row></Card>
            </Pressable>
          ))}
        </Section>
      ) : null}

      {connected ? (
        <>
          <Card style={{ gap: space[2] }}>
            <Row><T v="label" style={{ flex: 1 }}>Raw ECG / PPG</T><T v="small" color={p.muted}>{ecgN} samples</T></Row>
            {wave.length > 4 ? (
              <Svg width="100%" height={70}>
                <Polyline points={sparkline(wave, 70)} fill="none" stroke={p.teal} strokeWidth={1.5} />
              </Svg>
            ) : <T v="small" color={p.faint}>Start a measurement to stream the waveform.</T>}
            <Button title={measuring ? 'Stop measurement' : 'Start ECG/PPG measurement'} kind={measuring ? 'copper' : 'primary'} icon={measuring ? 'stop.circle' : 'waveform.path.ecg'} onPress={toggleMeasure} />
          </Card>

          {metrics.length ? (
            <Section title="Live data (parsed by the SDK)">
              <Card style={{ gap: 4 }}>
                {metrics.map(([k, v]) => (
                  <Row key={k}><T v="small" color={p.muted} style={{ flex: 1 }}>{k}</T><T v="num" style={{ fontSize: 15 }}>{String(v)}</T></Row>
                ))}
              </Card>
            </Section>
          ) : null}

          <Card style={{ gap: space[2] }}>
            <T v="label">Capture to /cal</T>
            <T v="small" color={p.muted}>Record raw ECG + parsed vitals under one session for engine training and benchmarking against the vendor algorithm.</T>
            {!capturing
              ? <Button kind="secondary" title="Start capture" icon="record.circle" onPress={startCapture} />
              : <Button kind="copper" title="Stop capture" icon="stop.circle" onPress={stopCapture} />}
          </Card>
          <Button kind="secondary" title="Disconnect" onPress={() => bleManager.disconnectDevice()} />
        </>
      ) : null}
      {toast}
    </Screen>
  );
}

function sparkline(vals: number[], h: number): string {
  const n = vals.length; if (n < 2) return '';
  const min = Math.min(...vals), max = Math.max(...vals), rng = max - min || 1;
  const w = 320;
  return vals.map((v, i) => `${((i / (n - 1)) * w).toFixed(1)},${(h - ((v - min) / rng) * (h - 6) - 3).toFixed(1)}`).join(' ');
}
