// Peptide library — the doctor-facing reference. An evidence-graded, region-aware (FDA + India/CDSCO) catalogue of
// peptides, sorted best-evidence first. Reference only, never a recommender: Telomy does not sell, prescribe or
// facilitate access to any peptide. Backend: GET /clinical/peptides (clinician-gated). Member side is /me/peptides.
import { Stack } from 'expo-router';
import React, { useMemo, useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Card, Icon, Row, Screen, T } from '@/ui/core';

type Peptide = {
  id: string; name: string; aliases: string[]; pclass: string; mechanism: string; grade: string;
  fda: string; cdsco: string; human: boolean; advised: boolean; summary: string; safety: string; citations: string[];
};
type Lib = { peptides: Peptide[]; classes: string[]; count: number; disclaimer: string };

function gradeColor(g: string, p: any) {
  return g === 'A' ? '#2F8F6B' : g === 'B' ? '#4FD08F' : g === 'C' ? '#C98A1B' : p.faint;
}
function GradeBadge({ grade, p }: { grade: string; p: any }) {
  const c = gradeColor(grade, p);
  return (
    <View style={{ backgroundColor: c + '22', borderRadius: radius.sm, paddingVertical: 3, paddingHorizontal: 8 }}>
      <T v="small" style={{ fontWeight: '700', color: c }}>{grade}</T>
    </View>
  );
}

export default function Peptides() {
  const p = usePalette();
  const { data, loading } = useApi<Lib>('/clinical/peptides');
  const [q, setQ] = useState('');
  const [cls, setCls] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  const items = useMemo(() => {
    const all = data?.peptides ?? [];
    const query = q.trim().toLowerCase();
    return all.filter((x) =>
      (!cls || x.pclass === cls) &&
      (!query || x.id.includes(query) || x.name.toLowerCase().includes(query) ||
        x.aliases.some((a) => a.includes(query)) || x.pclass.toLowerCase().includes(query)));
  }, [data, q, cls]);

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Peptide library' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Peptide library</T>
        <T v="small" color={p.muted}>Evidence-graded, with FDA and India (CDSCO) status on every entry. Reference only — Telomy does not recommend, prescribe, dose or source peptides. Verify current regulatory status before any decision.</T>
      </View>

      <Card style={{ gap: space[2] }}>
        <Row gap={space[2]} style={{ alignItems: 'center' }}>
          <Icon name="magnifyingglass" size={16} color={p.teal} />
          <TextInput value={q} onChangeText={setQ} placeholder="Search name, class, alias…" placeholderTextColor={p.faint}
            autoCapitalize="none" style={{ flex: 1, color: p.text, fontSize: 16, paddingVertical: 6 }} />
        </Row>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
          {['All', ...(data?.classes ?? [])].map((c) => {
            const on = (c === 'All' && !cls) || c === cls;
            return (
              <Pressable key={c} onPress={() => setCls(c === 'All' ? null : c)}
                style={{ paddingHorizontal: 10, paddingVertical: 5, borderRadius: 14, borderWidth: 1, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.teal + '22' : 'transparent' }}>
                <T v="small" color={on ? p.teal : p.muted}>{c === 'All' ? 'All' : c.split(' (')[0]}</T>
              </Pressable>
            );
          })}
        </View>
      </Card>

      {loading ? <Card><T v="small" color={p.muted}>Loading…</T></Card> : null}

      {items.map((x) => {
        const isOpen = open === x.id;
        return (
          <Pressable key={x.id} onPress={() => setOpen(isOpen ? null : x.id)}>
            <Card style={{ gap: isOpen ? space[2] : 6 }}>
              <Row gap={space[2]} style={{ alignItems: 'center' }}>
                <GradeBadge grade={x.grade} p={p} />
                <T v="h3" style={{ flex: 1 }}>{x.name}</T>
                {!x.advised ? <Icon name="exclamationmark.triangle.fill" size={13} color="#C98A1B" /> : null}
                <Icon name={isOpen ? 'chevron.up' : 'chevron.down'} size={12} color={p.faint} />
              </Row>
              <T v="small" color={p.muted}>{x.pclass}</T>
              {isOpen ? (
                <>
                  <T v="small" style={{ lineHeight: 20 }}>{x.summary}</T>
                  <Line label="Mechanism" value={x.mechanism} p={p} />
                  <Line label="FDA" value={x.fda} p={p} />
                  <Line label="India (CDSCO)" value={x.cdsco} p={p} />
                  <Line label="Human data" value={x.human ? 'Yes' : 'No — preclinical/anecdotal only'} p={p} />
                  <Line label="Safety" value={x.safety} p={p} />
                  {!x.advised ? <T v="small" color="#C98A1B">Not an approved therapy — research-grade / not advised outside a trial.</T> : null}
                  {x.citations?.length ? <T v="small" color={p.faint}>Sources: {x.citations.join(' · ')}</T> : null}
                </>
              ) : (
                <T v="small" color={p.muted} numberOfLines={1}>{x.fda}</T>
              )}
            </Card>
          </Pressable>
        );
      })}

      {data?.disclaimer ? <T v="small" color={p.faint} style={{ marginTop: space[2] }}>{data.disclaimer}</T> : null}
    </Screen>
  );
}

function Line({ label, value, p }: { label: string; value: string; p: any }) {
  return (
    <View style={{ gap: 1 }}>
      <T v="small" style={{ fontWeight: '600' }}>{label}</T>
      <T v="small" color={p.muted} style={{ lineHeight: 19 }}>{value}</T>
    </View>
  );
}
