// Shared with you — documents (reports, scans, images) a clinician sent to your account. Nothing is added without
// your confirmation: review each, then Accept to keep it in your records or Decline. Backend: /me/shared-documents.
import { Image } from 'expo-image';
import { Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Empty, Icon, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

type Doc = { id: number; ts: string; from_name: string; from_org: string; title: string; kind: string; media_type?: string; note?: string; status: string; bytes: number };

function Thumb({ id, mediaType }: { id: number; mediaType?: string }) {
  const [uri, setUri] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api<{ data: string; media_type?: string }>(`/me/shared-documents/${id}/file`)
      .then((f) => { if (live && f?.data) setUri(`data:${f.media_type || mediaType || 'image/jpeg'};base64,${f.data}`); })
      .catch(() => {});
    return () => { live = false; };
  }, [id]);
  if (!uri) return <View style={{ height: 160, borderRadius: radius.md, backgroundColor: '#00000010', alignItems: 'center', justifyContent: 'center' }}><Icon name="photo" size={24} color="#8a978f" /></View>;
  return <Image source={{ uri }} style={{ width: '100%', height: 220, borderRadius: radius.md }} contentFit="cover" />;
}

export default function Shared() {
  const p = usePalette();
  const { show } = useToast();
  const r = useApi<{ documents: Doc[] }>('/me/shared-documents');
  const [busy, setBusy] = useState<Record<number, boolean>>({});

  async function act(id: number, action: 'accept' | 'reject') {
    setBusy((b) => ({ ...b, [id]: true }));
    try {
      await api(`/me/shared-documents/${id}/${action}`, { method: 'POST' });
      show(action === 'accept' ? 'Added to your records.' : 'Declined.', action === 'accept' ? 'success' : 'neutral');
      r.reload();
    } catch (e: any) { show(e.message, 'alert'); } finally { setBusy((b) => ({ ...b, [id]: false })); }
  }

  if (!r.data) return <Screen><Stack.Screen options={{ title: 'Shared with you' }} /><Loading what="Loading shared documents…" /></Screen>;
  const docs = r.data.documents ?? [];
  const pending = docs.filter((d) => d.status === 'pending');
  const done = docs.filter((d) => d.status !== 'pending');

  const card = (d: Doc) => (
    <Card key={d.id} style={{ gap: space[2], marginBottom: space[2] }}>
      <Row style={{ alignItems: 'center' }}>
        <View style={{ width: 38, height: 38, borderRadius: 19, backgroundColor: p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={d.kind === 'image' || d.kind === 'scan' ? 'photo' : 'doc.text'} size={18} color={p.teal} />
        </View>
        <View style={{ flex: 1 }}>
          <T v="h3" numberOfLines={1}>{d.title}</T>
          <T v="small" color={p.muted}>{d.from_name}{d.from_org ? ` · ${d.from_org}` : ''} · {fmtDate(d.ts, true)}</T>
        </View>
        {d.status !== 'pending' ? <T v="small" color={d.status === 'accepted' ? '#2F8F6B' : p.faint}>{d.status === 'accepted' ? 'In your records' : 'Declined'}</T> : null}
      </Row>
      {d.note ? <T v="small">{d.note}</T> : null}
      {(d.kind === 'image' || d.kind === 'scan') && (d.media_type || '').startsWith('image') ? <Thumb id={d.id} mediaType={d.media_type} /> : null}
      {d.status === 'pending' ? (
        <Row gap={space[2]}>
          <Button kind="primary" title="Accept" icon="checkmark" onPress={() => act(d.id, 'accept')} disabled={busy[d.id]} style={{ flex: 1 }} />
          <Button kind="secondary" title="Decline" onPress={() => act(d.id, 'reject')} disabled={busy[d.id]} style={{ flex: 1 }} />
        </Row>
      ) : null}
    </Card>
  );

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Shared with you' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Shared with you</T>
        <T v="small" color={p.muted}>Documents your clinician sent. Nothing is added to your records until you accept it.</T>
      </View>
      {docs.length === 0 ? (
        <Empty title="Nothing shared yet" body="When your doctor shares a report, scan or image with you, it'll appear here for you to review and confirm." />
      ) : (
        <>
          {pending.length ? <Section title={`Awaiting your confirmation (${pending.length})`}>{pending.map(card)}</Section> : null}
          {done.length ? <Section title="Reviewed">{done.map(card)}</Section> : null}
        </>
      )}
    </Screen>
  );
}
