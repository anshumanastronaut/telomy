import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, Loading, Row, Screen, Section, T } from '@/ui/core';

export default function Consult() {
  const p = usePalette();
  const plans = useApi<any>('/plans');
  const list = useApi<any[]>('/consults');
  const [kind, setKind] = useState('gp');
  const [mode, setMode] = useState('video');
  const [reason, setReason] = useState('');
  const [done, setDone] = useState<string | null>(null);
  if (!plans.data) return <Screen edges={[]}><Loading what="Loading…" /></Screen>;
  const sub = plans.data.subscription;
  return (
    <Screen edges={[]}>
      <Card tone="teal">
        <T v="h3">{sub.plan_detail.name} plan</T>
        <T v="small">{sub.plan_detail.consults_month >= 99 ? 'Unlimited GP consults' : `${sub.consults_left_month} of ${sub.plan_detail.consults_month} included consults left this month`}</T>
      </Card>
      <Section title="Who would you like to see?">
        {Object.entries(plans.data.on_demand).map(([k, v]: any) => (
          <Pressable key={k} onPress={() => setKind(k)} style={{ padding: space[4], borderRadius: radius.lg, borderWidth: kind === k ? 2 : 1, borderColor: kind === k ? p.teal : p.border, backgroundColor: p.surface }}>
            <Row><T v="h3" style={{ flex: 1 }}>{v.name}</T><T v="body" style={{ fontWeight: '600' }}>₹{v.price}</T></Row>
            <T v="small">{v.minutes} minutes · {k === 'gp' ? 'usually within 30 minutes' : 'next day'}</T>
          </Pressable>
        ))}
      </Section>
      <Row>{['video', 'audio', 'chat'].map((m) => <Pressable key={m} onPress={() => setMode(m)}><Chip label={m} fg={mode === m ? '#fff' : p.text} bg={mode === m ? p.teal : p.surfaceAlt} /></Pressable>)}</Row>
      <TextInput value={reason} onChangeText={setReason} placeholder="What would you like to discuss?" placeholderTextColor={p.faint} multiline
        style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, minHeight: 70, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular' }} />
      {done ? <Card tone="teal"><T v="body">{done}</T></Card> : null}
      <Button title="Book consultation" testID="book-consult" onPress={async () => { const r = await api('/consults', { body: { kind, mode, reason } }); setDone(r.message); list.reload(); plans.reload(); }} />
      <Section title="Your consultations">
        <Card style={{ paddingVertical: 2 }}>
          {(list.data ?? []).map((c, i) => (
            <View key={c.id}>{i ? <Divider /> : null}
              <View style={{ paddingVertical: 10, gap: 2 }}>
                <Row><T v="body" style={{ flex: 1, fontWeight: '600' }}>{c.doctor} · {c.mode}</T><Chip label={c.status} fg={c.status === 'completed' ? p.success : p.warn} bg={c.status === 'completed' ? p.successSoft : p.warnSoft} /></Row>
                <T v="small">{c.scheduled_at.replace('T', ' ')} · {c.covered ? 'covered by plan' : `₹${c.price}`}</T>
                {c.notes ? <T v="body">Doctor's notes: {c.notes}</T> : null}
              </View>
            </View>
          ))}
          {list.data && !list.data.length ? <T v="small" style={{ paddingVertical: 10 }}>None yet.</T> : null}
        </Card>
      </Section>
    </Screen>
  );
}
