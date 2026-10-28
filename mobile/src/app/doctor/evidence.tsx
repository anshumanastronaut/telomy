// Clinical evidence — the doctor-facing "accurate like Vera" surface. A clinician asks a question; the backend
// (/clinical/ask) retrieves PubMed, grades each source, and the grounded model writes a short, cited answer.
// Every claim ties to a numbered source with its evidence grade, and nothing is a directive — decision support only.
import { Stack } from 'expo-router';
import React, { useState } from 'react';
import { ActivityIndicator, Linking, Pressable, TextInput, View } from 'react-native';

import { api } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, T } from '@/ui/core';

type Citation = { n: number; pmid: string; title: string; journal: string; year: string; grade: string; grade_label: string; url: string };
type Result = { answer?: string; citations?: Citation[]; used?: number[]; overall_grade?: { grade: string; label: string };
  confidence?: number; engine?: string; notice?: string; error?: string; disclaimer?: string };

const EXAMPLES = [
  'First-line antihypertensive in a 60-year-old with type 2 diabetes',
  'When to anticoagulate in atrial fibrillation (CHA₂DS₂-VASc)',
  'SGLT2 inhibitors in heart failure with preserved ejection fraction',
  'Antibiotic choice for uncomplicated community-acquired pneumonia',
];

function gradeColor(g: string, p: any) {
  return g === 'A' ? '#2F8F6B' : g === 'B' ? '#4FD08F' : g === 'C' ? '#C98A1B' : p.faint;
}

function GradeBadge({ grade, label, p }: { grade: string; label?: string; p: any }) {
  const c = gradeColor(grade, p);
  return (
    <Row gap={5} style={{ alignItems: 'center', backgroundColor: c + '22', borderRadius: radius.sm, paddingVertical: 3, paddingHorizontal: 8 }}>
      <T v="small" style={{ fontWeight: '700', color: c }}>{grade}</T>
      {label ? <T v="small" color={c}>{label}</T> : null}
    </Row>
  );
}

export default function Evidence() {
  const p = usePalette();
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Result | null>(null);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || busy) return;
    setQ(text);
    setBusy(true);
    setRes(null);
    try {
      const r = await api<Result>('/clinical/ask', { body: { question: text }, timeoutMs: 90000 });
      setRes(r);
    } catch (e: any) {
      setRes({ error: e.message ?? 'Could not reach the evidence service.' });
    } finally {
      setBusy(false);
    }
  }

  const cites = res?.citations ?? [];

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Clinical evidence' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Clinical evidence</T>
        <T v="small" color={p.muted}>Ask a clinical question. Answers are retrieved from PubMed, graded by study strength, and cited — decision support, not a directive.</T>
      </View>

      <Card style={{ gap: space[3] }}>
        <TextInput
          value={q}
          onChangeText={setQ}
          placeholder="e.g. Statin for primary prevention in a 75-year-old?"
          placeholderTextColor={p.faint}
          multiline
          style={{ minHeight: 48, maxHeight: 120, color: p.text, fontSize: 15 }}
          onSubmitEditing={() => ask(q)}
        />
        <Button title={busy ? 'Searching the evidence…' : 'Ask'} icon="magnifyingglass" onPress={() => ask(q)} disabled={busy || !q.trim()} loading={busy} />
      </Card>

      {!res && !busy ? (
        <View style={{ gap: space[2] }}>
          <T v="label">TRY</T>
          {EXAMPLES.map((e) => (
            <Pressable key={e} onPress={() => ask(e)} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}>
              <Card><Row style={{ alignItems: 'center' }}><Icon name="text.magnifyingglass" size={16} color={p.teal} /><T v="body" style={{ flex: 1 }}>{e}</T></Row></Card>
            </Pressable>
          ))}
        </View>
      ) : null}

      {busy ? <Row style={{ justifyContent: 'center', paddingVertical: space[5] }}><ActivityIndicator color={p.teal} /></Row> : null}

      {res?.error ? <Card tone="plain"><T v="body" color={p.danger}>{res.error}</T></Card> : null}

      {res && !res.error ? (
        <View style={{ gap: space[3] }}>
          {res.overall_grade ? (
            <Row style={{ alignItems: 'center' }}>
              <T v="label">STRENGTH OF EVIDENCE</T>
              <View style={{ flex: 1 }} />
              <GradeBadge grade={res.overall_grade.grade} label={res.overall_grade.label} p={p} />
            </Row>
          ) : null}

          {res.answer ? (
            <Card style={{ gap: space[2] }}>
              <T v="body" style={{ lineHeight: 23 }}>{res.answer}</T>
              {res.engine ? <T v="small" color={p.faint}>Synthesised by {res.engine} from the sources below.</T> : null}
            </Card>
          ) : null}

          {res.notice ? <Card tone="plain"><T v="small" color={p.muted}>{res.notice}</T></Card> : null}

          {cites.length ? (
            <View style={{ gap: space[2] }}>
              <T v="label">SOURCES ({cites.length})</T>
              {cites.map((c) => (
                <Pressable key={c.n} onPress={() => Linking.openURL(c.url)} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}>
                  <Card style={{ gap: space[2] }}>
                    <Row style={{ alignItems: 'flex-start' }}>
                      <T v="num" style={{ fontSize: 15, color: p.teal }}>{c.n}</T>
                      <View style={{ flex: 1, gap: 2 }}>
                        <T v="body" style={{ fontWeight: '600' }}>{c.title}</T>
                        <T v="small" color={p.muted}>{c.journal}{c.year ? ` · ${c.year}` : ''} · PMID {c.pmid}</T>
                      </View>
                    </Row>
                    <Row style={{ alignItems: 'center' }}>
                      <GradeBadge grade={c.grade} label={c.grade_label} p={p} />
                      <View style={{ flex: 1 }} />
                      <Row gap={4} style={{ alignItems: 'center' }}><T v="small" color={p.teal}>PubMed</T><Icon name="arrow.up.right" size={12} color={p.teal} /></Row>
                    </Row>
                  </Card>
                </Pressable>
              ))}
            </View>
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
