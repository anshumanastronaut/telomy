// Drug reference — FDA label (openFDA/DailyMed) + RxNorm + FAERS adverse-event counts. Reference only: dose and
// interactions come from the label/FAERS, never from an LLM. Search by generic name for best results.
import { Stack } from 'expo-router';
import React, { useState } from 'react';
import { ActivityIndicator, Linking, Pressable, TextInput, View } from 'react-native';

import { api } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, T } from '@/ui/core';

type Drug = {
  query?: string; name?: string; brand?: string; rxcui?: string | null; route?: string;
  label?: Record<string, string>; faers_top?: { term: string; count: number }[];
  sources?: { label: string; url: string }[]; notice?: string; disclaimer?: string; error?: string;
};

const SECTIONS: { key: string; label: string; warn?: boolean }[] = [
  { key: 'boxed_warning', label: 'Boxed warning', warn: true },
  { key: 'indications', label: 'Indications' },
  { key: 'dosing', label: 'Dosage & administration' },
  { key: 'contraindications', label: 'Contraindications', warn: true },
  { key: 'warnings', label: 'Warnings & precautions', warn: true },
  { key: 'interactions', label: 'Drug interactions', warn: true },
  { key: 'pregnancy', label: 'Pregnancy' },
];

export default function DrugRef() {
  const p = usePalette();
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Drug | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  async function look(name: string) {
    const text = name.trim();
    if (!text || busy) return;
    setQ(text); setBusy(true); setRes(null); setOpen({});
    try {
      const r = await api<Drug>(`/clinical/drug?name=${encodeURIComponent(text)}`, { timeoutMs: 40000 });
      setRes(r);
    } catch (e: any) {
      setRes({ error: e.message });
    } finally {
      setBusy(false);
    }
  }

  const lab = res?.label ?? {};
  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Drug reference' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Drug reference</T>
        <T v="small" color={p.muted}>FDA label + RxNorm + real-world adverse-event reports. Reference only — verify against the current label and the patient's medication list.</T>
      </View>

      <Card style={{ gap: space[3] }}>
        <Row gap={space[2]} style={{ alignItems: 'center' }}>
          <Icon name="pills" size={18} color={p.teal} />
          <TextInput value={q} onChangeText={setQ} placeholder="Generic name, e.g. atorvastatin" placeholderTextColor={p.faint}
            autoCapitalize="none" onSubmitEditing={() => look(q)} style={{ flex: 1, color: p.text, fontSize: 16, paddingVertical: 8 }} />
        </Row>
        <Button title={busy ? 'Looking up…' : 'Look up'} icon="magnifyingglass" onPress={() => look(q)} disabled={busy || !q.trim()} loading={busy} />
      </Card>

      {busy ? <Row style={{ justifyContent: 'center', paddingVertical: space[5] }}><ActivityIndicator color={p.teal} /></Row> : null}
      {res?.error ? <Card><T v="body" color={p.danger}>{res.error}</T></Card> : null}

      {res && !res.error ? (
        <View style={{ gap: space[3] }}>
          <Card style={{ gap: 4 }}>
            <T v="h2">{res.name}</T>
            {res.brand ? <T v="small" color={p.muted}>Brand: {res.brand}</T> : null}
            <Row gap={space[3]} style={{ flexWrap: 'wrap', marginTop: 4 }}>
              {res.route ? <T v="small" color={p.muted}>Route: {res.route}</T> : null}
              {res.rxcui ? <T v="small" color={p.muted}>RxCUI {res.rxcui}</T> : null}
            </Row>
          </Card>

          {res.notice ? <Card><T v="small" color={p.muted}>{res.notice}</T></Card> : null}

          {SECTIONS.filter((s) => lab[s.key]).map((s) => {
            const isOpen = open[s.key];
            const body = lab[s.key];
            return (
              <Pressable key={s.key} onPress={() => setOpen((o) => ({ ...o, [s.key]: !o[s.key] }))}>
                <Card style={{ gap: isOpen ? space[2] : 0 }}>
                  <Row style={{ alignItems: 'center' }}>
                    {s.warn ? <Icon name="exclamationmark.triangle.fill" size={14} color={s.key === 'boxed_warning' ? p.danger : '#C98A1B'} /> : null}
                    <T v="h3" style={{ flex: 1, marginLeft: s.warn ? 6 : 0, color: s.key === 'boxed_warning' ? p.danger : p.text }}>{s.label}</T>
                    <Icon name={isOpen ? 'chevron.up' : 'chevron.down'} size={13} color={p.faint} />
                  </Row>
                  {isOpen ? <T v="small" style={{ lineHeight: 20 }}>{body}</T> : <T v="small" color={p.muted} numberOfLines={1}>{body}</T>}
                </Card>
              </Pressable>
            );
          })}

          {res.faers_top?.length ? (
            <Card style={{ gap: space[2] }}>
              <T v="h3">Most-reported adverse events</T>
              <T v="small" color={p.faint}>FAERS spontaneous reports — frequency of reporting, not incidence or causation.</T>
              {res.faers_top.map((f) => (
                <Row key={f.term} style={{ alignItems: 'center' }}>
                  <T v="body" style={{ flex: 1 }}>{f.term}</T>
                  <T v="small" color={p.muted}>{f.count.toLocaleString()}</T>
                </Row>
              ))}
            </Card>
          ) : null}

          {res.sources?.length ? (
            <Row gap={space[3]} style={{ flexWrap: 'wrap' }}>
              {res.sources.map((s) => (
                <Pressable key={s.url} onPress={() => Linking.openURL(s.url)}>
                  <Row gap={4} style={{ alignItems: 'center' }}><T v="small" color={p.teal}>{s.label}</T><Icon name="arrow.up.right" size={11} color={p.teal} /></Row>
                </Pressable>
              ))}
            </Row>
          ) : null}

          {res.disclaimer ? (
            <Row style={{ alignItems: 'flex-start', paddingHorizontal: space[1] }}>
              <Icon name="exclamationmark.shield" size={14} color={p.faint} />
              <T v="small" color={p.faint} style={{ flex: 1, marginLeft: space[2] }}>{res.disclaimer}</T>
            </Row>
          ) : null}
        </View>
      ) : null}
    </Screen>
  );
}
