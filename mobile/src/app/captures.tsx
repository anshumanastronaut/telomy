// Saved therapy sessions on this phone: review, share with the research team, upload to Telomy, delete.
import { router, Stack, useFocusEffect } from 'expo-router';
import * as Sharing from 'expo-sharing';
import { useCallback, useState } from 'react';
import { View } from 'react-native';
import { api } from '@/lib/api';
import { Band, bandAvailable } from '@/lib/band';
import { usePalette } from '@/lib/theme';
import { Button, Card, Chip, Empty, Row, Screen, T, useToast } from '@/ui/core';
import type { CaptureMeta } from '../../modules/ky-ecg';

export default function Captures() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [list, setList] = useState<CaptureMeta[]>([]);
  const refresh = useCallback(() => setList(bandAvailable ? Band.listCaptures() : []), []);
  useFocusEffect(refresh);

  async function share(c: CaptureMeta) {
    if (!c.bundlePath) return show('This session has no export file yet.', 'alert');
    try {
      await Sharing.shareAsync(`file://${c.bundlePath}`, { mimeType: 'application/json', dialogTitle: `Telomy session ${c.id}`, UTI: 'public.json' });
    } catch (e: any) { show(e.message, 'alert'); }
  }

  async function upload(c: CaptureMeta) {
    try {
      const res = await fetch(`file://${c.bundlePath}`);
      const bundle = await res.json();
      await api('/band/captures', { body: bundle });
      show('Uploaded to Telomy.', 'success');
    } catch (e: any) { show(`Not uploaded: ${e.message}`, 'alert'); }
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]} onRefresh={refresh}>
        <Stack.Screen options={{ title: 'Saved sessions' }} />
        <T v="h1">Therapy sessions</T>
        <T v="small">Stored on this phone. Share sends one file per session (raw ECG, beats, HR/HRV every second, phases, settings, ratings, events), format telomy.capture/1.</T>
        {!list.length ? <Empty title="No sessions yet" body="Record one from Therapy capture." actions={[{ title: 'Record a session', onPress: () => router.push('/capture') }]} /> : null}
        {list.map((c) => {
          const dur = c.durationSec ?? 0;
          const s = (c.summary ?? {}) as any;
          return (
            <Card key={c.id}>
              <Row><T v="h3" style={{ flex: 1 }}>{c.therapy}</T><Chip label={`${Math.floor(dur / 60)} min`} /></Row>
              <T v="small">{new Date(c.startedAt * 1000).toLocaleString()} · {(c.phases ?? []).filter((x) => x.phase !== 'marker').map((x) => x.phase).join(' → ')}</T>
              <T v="small">{s.beats ?? 0} beats · {(c.bundleBytes ?? 0) > 0 ? `${((c.bundleBytes ?? 0) / 1e6).toFixed(1)} MB` : 'no export'}{s.events?.length ? ` · ${s.events.length} rhythm/signal events` : ''}</T>
              {c.notes ? <T v="small" color={p.muted}>“{c.notes}”</T> : null}
              <Row style={{ flexWrap: 'wrap' }}>
                <Button kind="primary" title="Share" icon="square.and.arrow.up" onPress={() => share(c)} />
                <Button kind="secondary" title="Upload" icon="icloud.and.arrow.up" onPress={() => upload(c)} />
                <Button kind="ghost" title="Delete" onPress={() => { Band.deleteCapture(c.id); refresh(); }} />
              </Row>
            </Card>
          );
        })}
      </Screen>
      {toast}
    </View>
  );
}
