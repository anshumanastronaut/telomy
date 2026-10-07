import { Stack } from 'expo-router';
import React, { useState } from 'react';
import { View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ErrorState, Loading, Row, Screen, Section, Segmented, T, useToast } from '@/ui/core';
import { inr } from '@/ui/therapy';

export default function Tests() {
  const p = usePalette();
  const rec = useApi<any[]>('/tests/recommended');
  const cat = useApi<any[]>('/tests');
  const [tab, setTab] = useState<'next' | 'all'>('next');
  const [open, setOpen] = useState<string | null>(null);
  const { toast, show } = useToast();
  if (cat.error) return <Screen edges={[]}><ErrorState message={cat.error} onRetry={cat.reload} /></Screen>;
  if (!cat.data || !rec.data) return <Screen edges={[]}><Loading what="Loading tests…" /></Screen>;
  const cats = Array.from(new Set(cat.data.map((t) => t.category)));

  async function book(id: string) {
    const d = new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 10);
    try { show((await api('/tests/book', { body: { test_id: id, day: d } })).message, 'success'); } catch (e: any) { show(e.message, 'alert'); }
  }
  const stateChip = (s: any) => s.state === 'current' ? <Chip label={`Done ${fmtDate(s.last, true)}`} fg={p.success} bg={p.successSoft} />
    : s.state === 'due' ? <Chip label={`Due — last ${fmtDate(s.last, true)}`} fg={p.warn} bg={p.warnSoft} />
    : s.state === 'never' ? <Chip label="Not in your Vault" /> : null;

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Tests & scans' }} />
        <T v="h1">Tests & scans</T>
        <Segmented options={[{ key: 'next', label: `For you · ${rec.data.length}` }, { key: 'all', label: `Catalogue · ${cat.data.length}` }]} value={tab} onChange={setTab} />
        {tab === 'next' ? (
          <>
            <T v="small">Guideline screening for your age and sex, follow-ups your results call for, and gaps in your Vault.</T>
            {rec.data.map((t) => (
              <Card key={t.id}>
                <Row><T v="h3" style={{ flex: 1 }}>{t.name}</T><Chip label={t.priority} fg={t.priority === 'high' ? p.danger : p.teal} bg={t.priority === 'high' ? p.dangerSoft : p.tealSoft} /></Row>
                <T v="body">{t.reason}</T>
                <Row style={{ flexWrap: 'wrap' }}>{stateChip(t.status)}<Chip label={`Evidence ${t.evidence}`} /><Chip label={t.price ? inr(t.price) : 'Included'} /></Row>
                <T v="small">Prep: {t.prep}</T>
                <Button kind="secondary" title="Book at the centre" onPress={() => book(t.id)} />
              </Card>
            ))}
          </>
        ) : cats.map((c) => (
          <Section key={c} title={c}>
            {cat.data!.filter((t) => t.category === c).map((t) => (
              <Card key={t.id} onPress={() => setOpen(open === t.id ? null : t.id)}>
                <Row><T v="body" style={{ flex: 1, fontWeight: '600' }}>{t.name}</T><Chip label={t.evidence} fg={t.evidence === 'D' ? p.danger : p.teal} bg={t.evidence === 'D' ? p.dangerSoft : p.tealSoft} /></Row>
                <Row style={{ flexWrap: 'wrap' }}>{stateChip(t.status)}<Chip label={t.price ? inr(t.price) : 'Included'} /><Chip label={t.tat} /></Row>
                {open === t.id ? (
                  <>
                    <T v="body">{t.why}</T>
                    <T v="small">Sample: {t.sample} · How often: {t.freq} · Prep: {t.prep}</T>
                    {t.markers.length ? <T v="small">Measures: {t.markers.map((m: any) => m.name).join(', ')}</T> : null}
                    {t.evidence === 'D' ? <T v="small" color={p.danger}>Not recommended — Telomy will not book this.</T> : <Button kind="secondary" title="Book" onPress={() => book(t.id)} />}
                  </>
                ) : null}
              </Card>
            ))}
          </Section>
        ))}
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
