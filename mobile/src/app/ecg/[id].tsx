// A saved ECG strip: full trace on ECG paper (scroll sideways), with the readings taken when it was saved.
import { Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { ScrollView } from 'react-native';
import { fmtDate, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Card, ErrorState, Loading, Row, Screen, Segmented, Stat, T } from '@/ui/core';
import { EcgStrip } from '@/ui/ecg';

export default function EcgStripScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data, error, reload } = useApi<any>(`/band/strips/${id}`, [id]);
  const [gain, setGain] = useState<'1' | '2'>('1');
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Loading what="Opening ECG…" /></Screen>;
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'ECG' }} />
      <T v="h1">{fmtDate(data.ts)} · {data.ts.slice(11, 16)}</T>
      <Card>
        <Row>
          <Stat label="Heart rate" value={data.hr ? Math.round(data.hr) : '–'} unit="bpm" />
          <Stat label="RMSSD" value={data.rmssd ? Math.round(data.rmssd) : '–'} unit="ms" />
          <Stat label="Length" value={Math.round(data.duration_s)} unit="s" />
        </Row>
        <T v="small">Signal at save time: {data.quality ?? 'unknown'} · {data.fs} Hz · {data.source}</T>
      </Card>
      <Card style={{ gap: 8 }}>
        <Row><T v="label" style={{ flex: 1 }}>25 mm/s · {10 * Number(gain)} mm/mV · scroll sideways</T>
          <Segmented options={[{ key: '1', label: '×1' }, { key: '2', label: '×2' }]} value={gain} onChange={setGain} /></Row>
        <ScrollView horizontal showsHorizontalScrollIndicator style={{ borderRadius: 10 }}>
          <EcgStrip samples={data.samples} fs={data.fs} gain={Number(gain)} />
        </ScrollView>
      </Card>
      <T v="small" color={p.muted}>Single-lead wellness ECG. It can show heart rhythm, but it can't rule out heart disease. Share it with your doctor if something worries you.</T>
    </Screen>
  );
}
