// JCVital V8 Pro band — Telomy integration (research/capture). Connects over BLE (react-native-ble-plx via the
// vendor's MIT BleManager) and decodes with the official @yhmedical/ms-data-sdk. This band's ECG lead is broken,
// so we use the OPTICAL path: heart rate (mode 2), SpO2 (mode 3) and live steps — the band streams these (and the
// raw PPG behind them). Shows live vitals + a HR trend and can capture a labelled session to /cal.
// The band bonds to ONE app at a time — forget it from the JCVital app before connecting here.
import { Stack } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { Pressable, View } from 'react-native';
import Svg, { Polyline } from 'react-native-svg';
import { BleSDK, DeviceKey, BleConst } from '@yhmedical/ms-data-sdk';

import { bleManager } from '@/lib/jcvital/BleManager';
import Constants from '@/lib/jcvital/constants';
import { api } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

type Dev = { id: string; name: string };
const MODE = { hrv: 1, hr: 2, spo2: 3 } as const;

export default function JCVital() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [ready, setReady] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [connected, setConnected] = useState(bleManager.isConnected());
  const [devices, setDevices] = useState<Dev[]>([]);
  const [vitals, setVitals] = useState<Record<string, any>>({});
  const [hrTrend, setHrTrend] = useState<number[]>([]);
  const [rawN, setRawN] = useState(0);
  const [lastRx, setLastRx] = useState(0);
  const [active, setActive] = useState<number | null>(null);   // mode currently measuring
  const [capturing, setCapturing] = useState(false);

  const session = useRef('');
  const buf = useRef<any[]>([]);
  const resend = useRef<any>(null);
  const spo2Buf = useRef<number[]>([]);

  useEffect(() => {
    bleManager.deviceType = 'V8';
    const onState = (c: boolean) => { setConnected(c); if (c) show('Band connected'); };
    const num = (v: any): number | null => typeof v === 'number' ? v : (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v)) ? Number(v) : null);
    const onParsed = (arg: any) => {
      try {
        // band payload: { data: { heart_rate, blood_oxygen, step, distance, calories, temp_data(×10), … }, data_type, end }
        const data = (arg && arg[DeviceKey.Data]) || arg || {};
        const upd: Record<string, any> = {};
        const hr = num(data[DeviceKey.HeartRate] ?? data.heart_rate);
        if (hr && hr > 0) { upd.heartRate = hr; setHrTrend((t) => [...t, hr].slice(-60)); }
        const sp = num(data[DeviceKey.Blood_oxygen] ?? data.blood_oxygen);
        if (sp && sp >= 70 && sp <= 100) {                       // SpO2 is noisy per-reading → show a rolling median
          spo2Buf.current = [...spo2Buf.current, sp].slice(-10);
          const s = [...spo2Buf.current].sort((a, b) => a - b);
          upd.spo2 = s[Math.floor(s.length / 2)];
        }
        for (const [k, v] of Object.entries(data)) {             // the band sends numbers as strings
          const n = num(v);
          if (n != null && !['heart_rate', 'blood_oxygen'].includes(k)) upd[k === 'temp_data' ? 'skin_temp_c' : k] = k === 'temp_data' ? Math.round(n / 10 * 10) / 10 : n;
        }
        if (Object.keys(upd).length) {
          setVitals((prev) => ({ ...prev, ...upd }));
          if (capturing && session.current) for (const [k, v] of Object.entries(upd)) if (typeof v === 'number') buf.current.push({ t: Date.now() / 1000, source: 'jcvital', channel: k, v });
        }
      } catch {}
    };
    const onRaw = (bytes: number[]) => {
      if (!bytes || !bytes.length) return;
      setRawN((n) => n + 1); setLastRx(Date.now());
      if (capturing && session.current) buf.current.push({ t: Date.now() / 1000, source: 'jcvital', channel: 'raw_frame', v: bytes.length, hex: bytes.slice(0, 40).map((b) => b.toString(16).padStart(2, '0')).join('') });
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
      if (resend.current) clearInterval(resend.current);
      bleManager.stopScan();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [capturing]);

  function safeWrite(cmd: number[]) { try { bleManager.writeData(cmd); } catch {} }
  async function uploadBuffer() {
    if (!session.current || !buf.current.length) return;
    const readings = buf.current.splice(0, buf.current.length);
    try { await api('/cal/ingest', { body: { session_id: session.current, readings }, queue: true }); } catch {}
  }

  function scan() {
    setDevices([]); setScanning(true);
    bleManager.startScan((d: any) => setDevices((prev) => prev.some((x) => x.id === d.id) ? prev : [...prev, { id: d.id, name: d.name || d.localName || '(band)' }]));
    setTimeout(() => { bleManager.stopScan(); setScanning(false); }, 8000);
  }
  function connect(id: string) { bleManager.stopScan(); setScanning(false); bleManager.connectDeviceById(id); }
  function stopMeasure() {
    if (resend.current) { clearInterval(resend.current); resend.current = null; }
    if (active != null) safeWrite(BleSDK.healthMeasurementWithDataType(active, false, null));
    try { safeWrite(BleSDK.realTimeStep(false, false)); } catch {}
    setActive(null);
  }
  function measure(mode: number, label: string) {
    if (active === mode) { stopMeasure(); return; }
    if (active != null) safeWrite(BleSDK.healthMeasurementWithDataType(active, false, null));
    // the band only streams once the real-time channel is open; then the measurement must be re-sent (~every 10s,
    // the demo re-sends on a 30s timer) or the band stops after one cycle.
    safeWrite(BleSDK.realTimeStep(true, false));
    safeWrite(BleSDK.healthMeasurementWithDataType(mode, true, null));
    if (resend.current) clearInterval(resend.current);
    resend.current = setInterval(() => safeWrite(BleSDK.healthMeasurementWithDataType(mode, true, null)), 10000);
    setActive(mode); show(`Measuring ${label}… keep the band snug on your wrist`);
  }
  function startCapture() {
    session.current = `jcvital-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}`;
    buf.current = []; setCapturing(true); show('Capturing to /cal…');
  }
  async function stopCapture() { setCapturing(false); await uploadBuffer(); show('Saved session to /cal.', 'success'); }

  const vk = Object.entries(vitals).filter(([, v]) => typeof v === 'number');

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'JCVital V8 band' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">JCVital V8</T>
        <T v="small" color={p.muted}>Optical path (HR · SpO₂ · steps) over the official SDK. ECG lead on this unit is broken, so ECG is skipped. Forget the band from the JCVital app first — it pairs to one app at a time.</T>
      </View>

      <Card tone={connected ? 'teal' : 'copper'}>
        <Row>
          <Icon name="dot.radiowaves.left.and.right" color={connected ? p.teal : p.copper} />
          <View style={{ flex: 1 }}>
            <T v="label">{connected ? 'Connected' : ready ? 'Ready' : 'Turn on Bluetooth'}</T>
            <T v="small" color={p.muted}>{connected ? 'Pick a measurement below.' : 'Scan and tap your band.'}</T>
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
            <Row style={{ justifyContent: 'space-between' }}>
              <View style={{ alignItems: 'center', flex: 1 }}><T v="small" color={p.muted}>Heart rate</T><T v="num" style={{ fontSize: 26 }} color={p.teal}>{vitals.heartRate ?? '—'}</T><T v="small" color={p.faint}>bpm</T></View>
              <View style={{ alignItems: 'center', flex: 1 }}><T v="small" color={p.muted}>SpO₂</T><T v="num" style={{ fontSize: 26 }} color={p.teal}>{vitals.spo2 ?? '—'}</T><T v="small" color={p.faint}>%</T></View>
              <View style={{ alignItems: 'center', flex: 1 }}><T v="small" color={p.muted}>Frames</T><T v="num" style={{ fontSize: 26 }}>{rawN}</T><T v="small" color={p.faint}>received</T></View>
            </Row>
            {hrTrend.length > 2 ? <Svg width="100%" height={48}><Polyline points={spark(hrTrend, 48)} fill="none" stroke={p.teal} strokeWidth={1.5} /></Svg> : null}
            <T v="small" color={rawN ? p.teal : (active != null ? p.copper : p.faint)}>
              {rawN ? `Streaming — ${rawN} frames, last ${Math.max(0, Math.round((Date.now() - lastRx) / 1000))}s ago`
                : active != null ? 'No data from the band yet — make sure it is snug on your wrist (optical sensor needs skin contact).'
                : 'Tap Heart rate to start.'}
            </T>
            <Row gap={space[2]} style={{ flexWrap: 'wrap' }}>
              <Button style={{ flex: 1 }} kind={active === MODE.hr ? 'copper' : 'primary'} title={active === MODE.hr ? 'Stop HR' : 'Heart rate'} onPress={() => measure(MODE.hr, 'heart rate')} />
              <Button style={{ flex: 1 }} kind={active === MODE.spo2 ? 'copper' : 'secondary'} title={active === MODE.spo2 ? 'Stop SpO₂' : 'SpO₂'} onPress={() => measure(MODE.spo2, 'SpO₂')} />
            </Row>
          </Card>

          {vk.length ? (
            <Section title="All data from the band">
              <Card style={{ gap: 4 }}>{vk.map(([k, v]) => <Row key={k}><T v="small" color={p.muted} style={{ flex: 1 }}>{k}</T><T v="num" style={{ fontSize: 15 }}>{String(v)}</T></Row>)}</Card>
            </Section>
          ) : null}

          <Card style={{ gap: space[2] }}>
            <T v="label">Capture to /cal</T>
            <T v="small" color={p.muted}>Record the band's vitals + raw frames under one session for engine training and benchmarking.</T>
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

function spark(vals: number[], h: number): string {
  const n = vals.length; if (n < 2) return '';
  const min = Math.min(...vals), max = Math.max(...vals), rng = max - min || 1, w = 320;
  return vals.map((v, i) => `${((i / (n - 1)) * w).toFixed(1)},${(h - ((v - min) / rng) * (h - 6) - 3).toFixed(1)}`).join(' ');
}
