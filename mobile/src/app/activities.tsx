import { router, Stack } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function Activities() {
  const p = usePalette();
  const { data, reload } = useApi<any>('/activities');
  const [name, setName] = useState('');
  const [fields, setFields] = useState('');
  const { toast, show } = useToast();
  if (!data) return <Screen edges={[]}><Loading what="Loading activities…" /></Screen>;

  async function create(template?: string) {
    const f = fields.split(',').map((s) => s.trim()).filter(Boolean).map((l) => ({ key: l.toLowerCase().replace(/[^a-z0-9]+/g, '_'), label: l, unit: '' }));
    try {
      const r = await api('/activities', { body: template ? { template } : { name, fields: f.length ? f : undefined } });
      show(`${r.name} created.`, 'success'); setName(''); setFields(''); reload(); router.push(`/activity/${r.id}`);
    } catch (e: any) { show(e.message, 'alert'); }
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'My activities' }} />
        <T v="h1">My activities</T>
        <T v="small">Track any activity the way you care about it — a bowling spell, a golf round, a padel match. Telomy builds your own baselines and shows what changes them.</T>
        {data.mine.map((a: any) => (
          <Card key={a.id} onPress={() => router.push(`/activity/${a.id}`)}>
            <Row><T v="h3" style={{ flex: 1 }}>{a.name}</T><Chip label={`${a.sessions} sessions`} /></Row>
            <T v="small">{a.category}{a.last ? ` · last ${fmtDate(a.last)}` : ''} · created {a.created_by === 'voice' ? 'by voice' : 'manually'}</T>
          </Card>
        ))}
        <Section title="Add from a template">
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
            {data.templates.filter((t: any) => !data.mine.some((m: any) => m.id === t.id)).map((t: any) => (
              <Pressable key={t.id} onPress={() => create(t.id)} accessibilityRole="button"><Chip label={`+ ${t.name}`} fg={p.teal} bg={p.tealSoft} /></Pressable>
            ))}
          </View>
        </Section>
        <Section title="Create your own">
          <TextInput value={name} onChangeText={setName} placeholder="Activity name (e.g. Padel match)" placeholderTextColor={p.faint}
            style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular' }} />
          <TextInput value={fields} onChangeText={setFields} placeholder="What to track, comma-separated (e.g. Games won, Unforced errors)" placeholderTextColor={p.faint}
            style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular' }} />
          <Button title="Create activity" disabled={!name.trim()} onPress={() => create()} />
          <Button kind="ghost" title="Or just tell Sinc: “bowled 6 overs, fastest 134”" icon="mic" onPress={() => router.push('/voice')} />
        </Section>
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
