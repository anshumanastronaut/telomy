import { router, Stack } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Icon, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

const KIND_ICON: Record<string, any> = { wake: 'sunrise', sleep: 'moon', smoke: 'smoke', alcohol: 'wineglass', caffeine: 'cup.and.saucer', water: 'drop',
  supplement: 'pills', commute: 'car', work: 'briefcase', walk: 'figure.walk', meal: 'fork.knife', screen: 'iphone' };

export default function Routine() {
  const p = usePalette();
  const cur = useApi<any>('/routine');
  const [drinking, setDrinking] = useState(false);
  const today = useApi<any>(`/routine/today?drinking=${drinking}`, [drinking]);
  const [text, setText] = useState('');
  const [preview, setPreview] = useState<any>(null);
  const { toast, show } = useToast();
  const items = preview?.items ?? cur.data?.items;
  const metrics = preview?.metrics ?? cur.data?.metrics;

  async function parse() { setPreview(await api('/routine/parse', { body: { text } })); }
  async function save() {
    const r = await api('/routine', { body: { text } });
    show(r.profile_changes.length ? `Saved. Updated: ${r.profile_changes.join('; ')}` : 'Routine saved.', 'success');
    setPreview(null); setText(''); cur.reload(); today.reload();
  }
  async function mark(key: string, status: string) {
    today.setData(await api('/routine/mark', { body: { day: today.data.day, key, status } }));
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'My routine' }} />
        <T v="h1">My routine</T>
        <T v="small">Describe a normal day — typed here or spoken to Sinc. Telomy turns it into a schedule, quantifies it, and learns from the days that differ.</T>
        <TextInput value={text} onChangeText={setText} multiline placeholder="e.g. I wake up around 8, coffee at 11, lunch at 1 with dal and eggs, gym Mon/Wed/Fri at 7 pm, sleep around 12…"
          placeholderTextColor={p.faint} testID="routine-text" autoCorrect={false} spellCheck={false} autoCapitalize="sentences"
          style={{ minHeight: 110, borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular', textAlignVertical: 'top' }} />
        <Row>
          <Button kind="secondary" title="Preview" style={{ flex: 1 }} disabled={text.trim().length < 20} onPress={parse} />
          <Button title="Save routine" style={{ flex: 1 }} disabled={text.trim().length < 20} onPress={save} />
        </Row>
        <Button kind="ghost" title="Say it to Sinc instead" icon="mic" onPress={() => router.push('/voice')} />

        {!items ? (cur.loading ? <Loading what="Loading…" /> : null) : (
          <>
            {preview ? <Chip label="Preview — not saved yet" fg={p.copper} bg={p.copperSoft} /> : null}
            {metrics ? (
              <Card tone="teal">
                <T v="label">What your routine adds up to</T>
                <Row style={{ flexWrap: 'wrap' }}>
                  {metrics.cigarettes_per_day ? <Chip label={`${metrics.cigarettes_per_day} cigarettes/day`} fg={p.danger} bg={p.surface} /> : null}
                  {metrics.alcohol_g_week ? <Chip label={`${metrics.alcohol_g_week} g alcohol/week`} fg={p.copper} bg={p.surface} /> : null}
                  {metrics.sleep_hours ? <Chip label={`${metrics.sleep_hours} h in bed`} /> : null}
                  {metrics.water_litres ? <Chip label={`water ${metrics.water_litres[0]}–${metrics.water_litres[1]} L`} /> : null}
                  {metrics.caffeine_times?.length ? <Chip label={`coffee ${metrics.caffeine_times.join(', ')}`} /> : null}
                  {metrics.lunch_protein_g ? <Chip label={`lunch ~${metrics.lunch_protein_g} g protein`} /> : null}
                </Row>
              </Card>
            ) : null}
            {metrics?.flags?.map((f: any) => (
              <Card key={f.topic}>
                <Row><T v="h3" style={{ flex: 1 }}>{f.topic}</T><Chip label={`Evidence ${f.evidence}`} fg={f.severity === 'high' ? p.danger : p.teal} bg={f.severity === 'high' ? p.dangerSoft : p.tealSoft} /></Row>
                <T v="body">{f.text}</T>
              </Card>
            ))}
            {metrics?.flags?.length ? <Button kind="secondary" title="See it on your digital twin" icon="person.2.wave.2" onPress={() => router.push('/twin')} /> : null}
            <Section title={preview ? 'Your schedule (preview)' : 'Your schedule'}>
              <Card style={{ paddingVertical: 4 }}>
                {items.map((it: any, i: number) => (
                  <Row key={it.key + i} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                    <Icon name={KIND_ICON[it.kind] ?? 'circle'} size={18} color={p.teal} />
                    <T v="small" style={{ width: 82 }}>{it.window ? `${it.window[0]}–${it.window[1]}` : it.time ?? it.anchor ?? ''}</T>
                    <View style={{ flex: 1 }}>
                      <T v="body">{it.label}</T>
                      {it.days?.length < 7 || it.condition || it.note ? <T v="small">{[it.days?.length < 7 ? it.days.join(' ') : null, it.condition?.replace('_', ' '), it.note].filter(Boolean).join(' · ')}</T> : null}
                    </View>
                  </Row>
                ))}
              </Card>
            </Section>
          </>
        )}

        {today.data?.items?.length && !preview ? (
          <Section title={`Today · ${today.data.weekday}`}>
            <Row>
              <Pressable onPress={() => setDrinking(false)} style={{ flex: 1 }}><Chip label="Not drinking today" fg={!drinking ? '#fff' : p.text} bg={!drinking ? p.teal : p.surfaceAlt} /></Pressable>
              <Pressable onPress={() => setDrinking(true)} style={{ flex: 1 }}><Chip label="Drinking today" fg={drinking ? '#fff' : p.text} bg={drinking ? p.copper : p.surfaceAlt} /></Pressable>
            </Row>
            {today.data.items.filter((i: any) => ['smoke', 'alcohol', 'caffeine', 'supplement', 'walk', 'meal'].includes(i.kind)).map((it: any) => (
              <Card key={it.key}>
                <Row>
                  <T v="body" style={{ flex: 1 }}>{it.time ?? it.anchor ?? ''} · {it.label}</T>
                  <Chip label={it.status} fg={it.status === 'done' ? p.success : it.status === 'expected' ? p.muted : p.copper} bg={it.status === 'done' ? p.successSoft : p.surfaceAlt} />
                </Row>
                {it.status === 'expected' ? (
                  <Row>
                    <Button kind="secondary" title="Done" style={{ flex: 1 }} onPress={() => mark(it.key, 'done')} />
                    <Button kind="ghost" title="Skipped" style={{ flex: 1 }} onPress={() => mark(it.key, 'skipped')} />
                  </Row>
                ) : null}
              </Card>
            ))}
            <T v="small">Confirmed items become events in your Vault, so the correlation engine and your twin learn from real days, not just the plan.</T>
          </Section>
        ) : null}
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
