// Peptide library — MEMBER view. Clinician-gated by design: name, class, evidence grade and the regulatory reality
// only, with a "discuss with your doctor" frame. No mechanism-as-how-to, no dosing, no sourcing, never a recommendation.
// Backend: GET /me/peptides (returns the safe field set). The full clinician reference lives in the doctor app.
import { Stack } from 'expo-router';
import React, { useMemo, useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Card, Icon, Row, Screen, T } from '@/ui/core';

type Pep = { id: string; name: string; pclass: string; family: string; grade: string; regulatory: string; claim: string; flag: string | null };
type Lib = { peptides: Pep[]; count: number; note: string; disclaimer: string };

function gradeColor(g: string, p: any) {
  return g === 'A' ? '#2F8F6B' : g === 'B' ? '#4FD08F' : g === 'C' ? '#C98A1B' : p.faint;
}

export default function MemberPeptides() {
  const p = usePalette();
  const { data, loading } = useApi<Lib>('/me/peptides');
  const [q, setQ] = useState('');
  const [fam, setFam] = useState<string | null>(null);

  const families = useMemo(() => Array.from(new Set((data?.peptides ?? []).map((x) => x.family))).sort(), [data]);
  const items = useMemo(() => {
    const all = data?.peptides ?? [];
    const query = q.trim().toLowerCase();
    return all.filter((x) => (!fam || x.family === fam) &&
      (!query || x.name.toLowerCase().includes(query) || x.id.includes(query) || x.family.toLowerCase().includes(query)));
  }, [data, q, fam]);

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Peptide library' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Peptides</T>
        <T v="small" color={p.muted}>Information to discuss with your doctor — not advice. We show each peptide's evidence grade and its approval status, and never recommend, dose or source any of them.</T>
      </View>

      <Card tone="copper" style={{ gap: 4 }}>
        <Row gap={6}><Icon name="stethoscope" size={14} color={p.copper} /><T v="label">Clinician-gated</T></Row>
        <T v="small">{data?.note ?? 'Any peptide you have read about is shown by name so you can raise it with a doctor on your care team. Many are unapproved or illegal to sell in India.'}</T>
      </Card>

      <Card style={{ gap: space[2] }}>
        <Row gap={space[2]} style={{ alignItems: 'center' }}>
          <Icon name="magnifyingglass" size={16} color={p.teal} />
          <TextInput value={q} onChangeText={setQ} placeholder="Search a peptide…" placeholderTextColor={p.faint}
            autoCapitalize="none" style={{ flex: 1, color: p.text, fontSize: 16, paddingVertical: 6 }} />
        </Row>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
          {['All', ...families].map((c) => {
            const on = (c === 'All' && !fam) || c === fam;
            return (
              <Pressable key={c} onPress={() => setFam(c === 'All' ? null : c)}
                style={{ paddingHorizontal: 10, paddingVertical: 5, borderRadius: 14, borderWidth: 1, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.teal + '22' : 'transparent' }}>
                <T v="small" color={on ? p.teal : p.muted}>{c}</T>
              </Pressable>
            );
          })}
        </View>
      </Card>

      {loading ? <Card><T v="small" color={p.muted}>Loading…</T></Card> : null}

      {items.map((x) => (
        <Card key={x.id} style={{ gap: 6 }}>
          <Row gap={space[2]} style={{ alignItems: 'center' }}>
            <View style={{ backgroundColor: gradeColor(x.grade, p) + '22', borderRadius: radius.sm, paddingVertical: 3, paddingHorizontal: 8 }}>
              <T v="small" style={{ fontWeight: '700', color: gradeColor(x.grade, p) }}>{x.grade}</T>
            </View>
            <T v="h3" style={{ flex: 1 }}>{x.name}</T>
            {x.flag ? <Icon name="exclamationmark.triangle.fill" size={13} color="#C98A1B" /> : null}
          </Row>
          <T v="small" color={p.muted}>{x.family}</T>
          <T v="small" style={{ lineHeight: 19 }}>{x.claim}</T>
          <T v="small" color={p.faint}>{x.regulatory}</T>
          {x.flag ? <T v="small" color="#C98A1B">{x.flag}</T> : null}
        </Card>
      ))}

      {data?.disclaimer ? <T v="small" color={p.faint} style={{ marginTop: space[2] }}>{data.disclaimer}</T> : null}
    </Screen>
  );
}
