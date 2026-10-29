// Patch IMU capture — reverse-engineering + labelled capture of the chest patch's 6-axis accelerometer.
// The patch streams accel on vendor command 0x33 (ECG_ACC) which the app otherwise ignores; this screen forces the
// stream on (KYBand.startRawImu → 0x2E/0x2F), shows the live decoded x/y/z, writes every raw frame to Documents/band-raw
// for offline byte-layout decoding, and uploads labelled readings to /cal/ingest so the activity/steps/sleep models can
// be trained on ground-truth sessions ("Sitting", "Walking"…). Dev/research tool — reached from Devices.
import { Stack } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { Pressable, View } from 'react-native';

import { Band, type BandStatus, type ImuEvent } from '../../modules/ky-ecg';
import { api } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

const LABELS = ['Sitting', 'Standing', 'Lying down', 'Walking', 'Stairs', 'Arm raises', 'Deep breaths', 'Still (no patch move)'];

export default function ImuScreen() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [s, setS] = useState<BandStatus | null>(Band.getStatus());
  const [capturing, setCapturing] = useState(false);
  const [ev, setEv] = useState<ImuEvent | null>(null);
  const [label, setLabel] = useState('Sitting');
  const [startedAt, setStartedAt] = useState(0);

  const session = useRef<string>('');
  const buf = useRef<any[]>([]);
  const labelRef = useRef(label);
  labelRef.current = label;

  useEffect(() => {
    const st = Band.on('onStatus', setS);
    const im = Band.onImu((e) => {
      setEv(e);
      if (e.phase === 'started') { setCapturing(true); setStartedAt(Date.now()); }
      if (e.phase === 'stopped') setCapturing(false);
      if (e.phase === 'data' && e.ax != null) {
        buf.current.push({ t: Date.now() / 1000, source: 'patch', channel: 'imu', label: labelRef.current,
          ax: e.ax, ay: e.ay, az: e.az, hz: e.hz, n: e.count });
      }
    });
    setS(Band.getStatus());
    const flush = setInterval(() => void uploadBuffer(), 2500);
    return () => { st.remove(); im.remove(); clearInterval(flush); if (capturing) Band.stopRawImu(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function uploadBuffer() {
    if (!session.current || buf.current.length === 0) return;
    const readings = buf.current.splice(0, buf.current.length);
    try { await api('/cal/ingest', { body: { session_id: session.current, readings }, queue: true }); } catch {}
  }

  function start() {
    session.current = `imu-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}`;
    buf.current = [];
    Band.startRawImu(label.toLowerCase().replace(/\s+/g, '-'));
    show('Capturing patch IMU…');
  }
  async function stop() {
    Band.stopRawImu();
    await uploadBuffer();
    show('Saved to band-raw on this phone + /cal.', 'success');
  }
  function mark(l: string) {
    setLabel(l);
    if (capturing) buf.current.push({ t: Date.now() / 1000, source: 'patch', channel: 'imu_label', label: l });
  }

  const connected = s?.state === 'connected' || s?.state === 'streaming';
  const secs = startedAt ? Math.round((Date.now() - startedAt) / 1000) : 0;
  const noFrames = capturing && (ev?.count ?? 0) === 0 && secs > 6;
  const mag = ev?.ax != null ? Math.round(Math.sqrt(ev.ax ** 2 + (ev.ay ?? 0) ** 2 + (ev.az ?? 0) ** 2)) : null;

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Patch IMU capture' }} />

      <Card tone={connected ? 'teal' : 'copper'}>
        <Row>
          <Icon name="waveform.path.ecg" color={connected ? p.teal : p.copper} />
          <View style={{ flex: 1 }}>
            <T v="label">{connected ? 'Patch connected' : 'Patch not connected'}</T>
            <T v="small" color={p.muted}>{connected ? 'Wear it on your chest and keep this screen open while capturing.' : 'Put the patch on — it powers on at skin contact — then come back.'}</T>
          </View>
        </Row>
      </Card>

      <Card style={{ gap: space[2] }}>
        <Row>
          <T v="label" style={{ flex: 1 }}>Live accelerometer</T>
          <T v="small" color={p.muted}>{capturing ? `${secs}s · ${ev?.hz ?? 0} Hz` : 'idle'}</T>
        </Row>
        <Row style={{ justifyContent: 'space-between' }}>
          {(['ax', 'ay', 'az'] as const).map((k) => (
            <View key={k} style={{ alignItems: 'center', flex: 1 }}>
              <T v="small" color={p.muted}>{k.toUpperCase()}</T>
              <T v="num" style={{ fontSize: 22 }}>{ev?.[k] ?? '—'}</T>
            </View>
          ))}
          <View style={{ alignItems: 'center', flex: 1 }}>
            <T v="small" color={p.muted}>|a|</T>
            <T v="num" style={{ fontSize: 22 }} color={p.teal}>{mag ?? '—'}</T>
          </View>
        </Row>
        <T v="small" color={p.muted}>Frames: {ev?.count ?? 0}{ev?.perFrame ? ` · ${ev.perFrame}/pkt` : ''}</T>
        {ev?.raw ? <T v="small" color={p.faint} style={{ fontFamily: 'Menlo' as any }}>{ev.raw}</T> : null}
        {noFrames ? <T v="small" color={p.copper}>No 0x33 frames yet — the patch may not emit accel in this mode. The raw log in band-raw will show what it did send, so we can decode the right enable command.</T> : null}
      </Card>

      <Section title="Label what you're doing">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {LABELS.map((l) => {
            const on = label === l;
            return (
              <Pressable key={l} onPress={() => mark(l)}
                style={{ paddingHorizontal: 12, paddingVertical: 7, borderRadius: 16, borderWidth: 1, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.teal + '22' : 'transparent' }}>
                <T v="small" color={on ? p.teal : p.muted}>{l}</T>
              </Pressable>
            );
          })}
        </View>
        <T v="small" color={p.faint}>Tap the activity before you do it — each tap marks the stream so the models learn from labelled ground truth.</T>
      </Section>

      {!capturing
        ? <Button title="Start IMU capture" icon="record.circle" onPress={start} disabled={!connected} />
        : <Button kind="copper" title="Stop capture" icon="stop.circle" onPress={stop} />}

      <T v="small" color={p.faint}>Raw frames are saved to band-raw on this phone and uploaded to /cal under one session id for offline decoding. Nothing leaves your account.</T>
      {toast}
    </Screen>
  );
}
