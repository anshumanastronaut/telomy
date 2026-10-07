import { Stack, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { LineChart } from '@/ui/charts';
import { Button, Card, Chip, ErrorState, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

const NICE: Record<string, string> = { hr_mean: 'Average heart rate', hr_max: 'Peak heart rate', hrv_mean: 'HRV during activity', calm_index: 'Calm index',
  workload: 'Workload', pressure_hr: 'Pressure response (late vs early HR)' };

export default function Activity() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: d, error, reload } = useApi<any>(`/activities/${id}`, [id]);
  const [vals, setVals] = useState<Record<string, string>>({});
  const { toast, show } = useToast();
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen edges={[]}><Loading what="Loading…" /></Screen>;
  const keys = Object.keys(d.series);

  async function log() {
    const values = Object.fromEntries(Object.entries(vals).filter(([, v]) => v !== '').map(([k, v]) => [k, Number(v)]));
    await api(`/activities/${id}/sessions`, { body: { values } });
    setVals({}); show('Session logged.', 'success'); reload();
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: d.type.name }} />
        <T v="h1">{d.type.name}</T>
        <Row><Chip label={d.type.category} /><Chip label={`${d.sessions.length} sessions`} fg={p.teal} bg={p.tealSoft} /></Row>
        {d.insights.length ? <Card tone="teal">{d.insights.map((i: string) => <T key={i} v="body">• {i}</T>)}</Card> : null}
        {keys.map((k) => {
          const s = d.series[k];
          const f = d.type.fields.find((x: any) => x.key === k);
          const label = f?.label ?? NICE[k] ?? k;
          return (
            <Card key={k}>
              <Row>
                <T v="h3" style={{ flex: 1 }}>{label}</T>
                <T v="num" style={{ fontSize: 16 }}>{s.last} <T v="small">{f?.unit ?? ''}</T></T>
              </Row>
              <LineChart points={s.points.map(([x, y]: [string, number]) => ({ x, y }))} height={110} unit={f?.unit ?? ''}
                band={s.baseline ? [s.baseline.median - 1.4826 * s.baseline.mad, s.baseline.median + 1.4826 * s.baseline.mad] : null} dots />
              {s.baseline ? <T v="small">Your baseline {s.baseline.median} ± {Math.round(1.4826 * s.baseline.mad * 10) / 10} (last {s.baseline.n}){s.latest_vs_baseline != null ? ` · latest ${s.latest_vs_baseline > 0 ? '+' : ''}${s.latest_vs_baseline} SD` : ''}</T> : <T v="small">Baseline after 3 sessions.</T>}
            </Card>
          );
        })}
        <Section title="Log a session">
          {d.type.fields.map((f: any) => (
            <Row key={f.key}>
              <T v="body" style={{ flex: 1 }}>{f.label}{f.unit ? ` (${f.unit})` : ''}</T>
              <TextInput value={vals[f.key] ?? ''} onChangeText={(v) => setVals({ ...vals, [f.key]: v })} keyboardType="decimal-pad" placeholder="—" placeholderTextColor={p.faint}
                style={{ width: 90, borderWidth: 1, borderColor: p.border, borderRadius: radius.sm, padding: 8, color: p.text, textAlign: 'right', fontFamily: 'Inter_400Regular' }} />
            </Row>
          ))}
          <Button title="Save session" onPress={log} disabled={!Object.values(vals).some(Boolean)} />
          <T v="small">Heart rate, HRV and calm index are added automatically when your watch, ring or band records the session.</T>
        </Section>
        <Section title="History">
          <Card style={{ paddingVertical: 4 }}>
            {d.sessions.slice(0, 12).map((s: any, i: number) => (
              <View key={s.id} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <T v="body">{fmtDate(s.ts)} · {s.source}</T>
                <T v="small">{Object.entries(s.values).map(([k, v]) => `${k.replace(/_/g, ' ')} ${v}`).join(' · ')}{s.vitals.calm_index != null ? ` · calm ${s.vitals.calm_index}` : ''}{s.vitals.hr_max ? ` · HR max ${s.vitals.hr_max}` : ''}</T>
              </View>
            ))}
          </Card>
        </Section>
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
