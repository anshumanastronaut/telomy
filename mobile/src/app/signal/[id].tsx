import { router, Stack, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { LineChart } from '@/ui/charts';
import { Button, Card, Chip, ErrorState, Loading, Prov, Row, Screen, Section, Segmented, Stat, T, useToast } from '@/ui/core';
import { confLabel } from '@/ui/insight';

const RANGES = ['W', 'M', '6M', 'Y'] as const;

export default function Signal() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const [range, setRange] = useState<(typeof RANGES)[number]>('M');
  const { data: s, error, reload } = useApi<any>(`/signals/${id}?range=${range}`, [id, range]);
  const [manual, setManual] = useState('');
  const { toast, show } = useToast();
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!s) return <Screen edges={[]}><Loading what="Loading signal…" /></Screen>;
  const dec = s.points.some((x: any) => Math.abs(x.value) < 10) ? 1 : 0;
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: s.label }} />
        <T v="h1">{s.label}</T>
        <Segmented options={RANGES.map((k) => ({ key: k, label: k === 'W' ? 'Week' : k === 'M' ? 'Month' : k }))} value={range} onChange={setRange} />
        <Card>
          <Row>
            <Stat label="Average" value={s.stats.avg} unit={s.unit} />
            <Stat label="Low" value={s.stats.min != null ? Number(s.stats.min.toFixed(dec)) : null} unit={s.unit} />
            <Stat label="High" value={s.stats.max != null ? Number(s.stats.max.toFixed(dec)) : null} unit={s.unit} />
          </Row>
          <LineChart
            points={s.points.map((x: any) => ({ x: x.day, y: x.value }))}
            band={s.target}
            events={s.events.map((e: any) => ({ x: e.ts.slice(0, 10), label: e.label }))}
            unit={s.unit}
            decimals={dec}
            caption={`n = ${s.stats.n} days · copper lines = logged events · teal band = target`}
          />
          <Prov source={s.sources.join(', ')} when={`${s.start} → ${s.end}`} />
          {s.baseline ? <T v="small">30-day baseline {s.baseline.mean} ± {s.baseline.sd} {s.unit}</T> : null}
        </Card>

        {s.effects?.length ? (
          <Section title="What moves it, in your data">
            {s.effects.map((e: any) => (
              <Card key={e.id} onPress={() => router.push(`/insight/${e.id}`)}>
                <Row>
                  <T v="h3" style={{ flex: 1 }}>{e.title}</T>
                  <Chip label={e.direction === 'harmful' ? 'Lowers' : e.direction === 'helpful' ? 'Helps' : 'Linked'} fg={e.direction === 'harmful' ? p.danger : p.success} bg={e.direction === 'harmful' ? p.dangerSoft : p.successSoft} />
                </Row>
                <T v="small">{confLabel(e.confidence)} · n = {e.n} · d = {e.receipts.effect_d}</T>
              </Card>
            ))}
          </Section>
        ) : null}

        <Section title="Add a reading manually">
          <Row>
            <TextInput
              value={manual}
              onChangeText={setManual}
              keyboardType="decimal-pad"
              placeholder={`Value in ${s.unit || 'units'}`}
              placeholderTextColor={p.faint}
              style={{ flex: 1, borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, fontFamily: 'Inter_400Regular', backgroundColor: p.surface }}
            />
            <Button
              title="Save"
              disabled={!manual}
              onPress={async () => {
                await api('/signals', { body: { metric: id, value: Number(manual) } });
                setManual('');
                show('Saved. Marked as manual entry.', 'success');
                reload();
              }}
            />
          </Row>
        </Section>
      </Screen>
      {toast}
    </View>
  );
}
