import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function Care() {
  const p = usePalette();
  const cl = useApi<any[]>('/clinicians');
  const ap = useApi<any[]>('/appointments');
  const [sel, setSel] = useState<string | null>(null);
  const [mode, setMode] = useState('video');
  const [slot, setSlot] = useState(0);
  const { toast, show } = useToast();
  const slots = [1, 2, 3].map((d) => { const t = new Date('2026-10-06T10:30:00'); t.setDate(t.getDate() + d); return t; });
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Section title="Upcoming">
          {(ap.data ?? []).filter((a) => a.status !== 'cancelled').map((a) => (
            <Card key={a.id}>
              <Row><T v="h3" style={{ flex: 1 }}>{a.clinician?.name}</T><Chip label={a.status} fg={p.success} bg={p.successSoft} /></Row>
              <T v="small">{fmtDate(a.ts, true)} {a.ts.slice(11, 16)} · {a.kind} · {a.reason}</T>
              <Button kind="secondary" icon="doc.richtext" title="Prepare pre-clinic brief" onPress={() => router.push(`/brief?specialty=${a.clinician?.title.includes('Cardio') ? 'cardiology' : a.clinician?.title.includes('Endo') ? 'endocrinology' : a.clinician?.title.includes('Sleep') ? 'sleep' : a.clinician?.title.includes('Gastro') ? 'gastroenterology' : 'general'}`)} />
            </Card>
          ))}
        </Section>
        <Section title="Telomy Care clinicians">
          {!cl.data ? <Loading what="Loading…" /> : null}
          {cl.data?.map((c) => (
            <Card key={c.id} onPress={() => setSel(sel === c.id ? null : c.id)}>
              <Row><T v="h3" style={{ flex: 1 }}>{c.name}</T><T v="small">★ {c.rating} · {c.years} y</T></Row>
              <T v="small">{c.title} · {c.clinic}</T>
              <T v="small">Next: {c.next} · ₹{c.fee}</T>
              {sel === c.id ? (
                <View style={{ gap: 8 }}>
                  <Row>{c.modes.map((m: string) => <Pressable key={m} onPress={() => setMode(m)}><Chip label={m} fg={mode === m ? '#fff' : p.text} bg={mode === m ? p.teal : p.surfaceAlt} /></Pressable>)}</Row>
                  <Row>{slots.map((s, i) => (
                    <Pressable key={i} onPress={() => setSlot(i)} style={{ flex: 1, padding: 10, borderRadius: radius.md, borderWidth: 1, borderColor: slot === i ? p.teal : p.border, alignItems: 'center' }}>
                      <T v="small" color={slot === i ? p.teal : p.text}>{fmtDate(s.toISOString())} 10:30</T>
                    </Pressable>
                  ))}</Row>
                  <Button title="Request appointment" onPress={async () => { const r = await api('/appointments', { body: { clinician_id: c.id, ts: slots[slot].toISOString().slice(0, 19), kind: mode, reason: 'Vault review' } }); show(r.message, 'success'); ap.reload(); setSel(null); }} />
                </View>
              ) : null}
            </Card>
          ))}
        </Section>
      </Screen>
      {toast}
    </View>
  );
}
