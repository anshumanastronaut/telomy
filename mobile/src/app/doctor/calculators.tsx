// Clinical calculators — point-of-care scores, computed server-side (deterministic, cited, no LLM). Pick a score,
// fill the inputs, get the result with its usual interpretation and a risk colour. Decision support, not a directive.
import { Stack } from 'expo-router';
import React, { useMemo, useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Loading, Row, Screen, Segmented, T } from '@/ui/core';

type Input = { key: string; label: string; type: 'number' | 'bool' | 'enum'; unit?: string; options?: string[] };
type Calc = { id: string; name: string; cat: string; about: string; ref: string; inputs: Input[] };
type CalcResult = { result?: number | null; unit?: string; interpretation?: string; risk?: string; detail?: string; ref?: string; disclaimer?: string; error?: string };

function riskColor(r: string | undefined, p: any) {
  return r === 'critical' || r === 'high' ? p.danger : r === 'moderate' ? '#C98A1B' : r === 'low' ? '#2F8F6B' : p.muted;
}

export default function Calculators() {
  const p = usePalette();
  const list = useApi<{ calculators: Calc[] }>('/clinical/calcs');
  const [sel, setSel] = useState<Calc | null>(null);
  const [vals, setVals] = useState<Record<string, any>>({});
  const [res, setRes] = useState<CalcResult | null>(null);
  const [busy, setBusy] = useState(false);

  const groups = useMemo(() => {
    const g: Record<string, Calc[]> = {};
    for (const c of list.data?.calculators ?? []) (g[c.cat] ??= []).push(c);
    return g;
  }, [list.data]);

  function open(c: Calc) {
    setSel(c);
    const init: Record<string, any> = {};
    for (const i of c.inputs) init[i.key] = i.type === 'bool' ? false : i.type === 'enum' ? (i.options?.[0] ?? '') : '';
    setVals(init);
    setRes(null);
  }

  async function compute() {
    if (!sel) return;
    setBusy(true);
    try {
      const r = await api<CalcResult>('/clinical/calc', { body: { id: sel.id, values: vals } });
      setRes(r);
    } catch (e: any) {
      setRes({ error: e.message });
    } finally {
      setBusy(false);
    }
  }

  if (!list.data) return <Screen><Stack.Screen options={{ title: 'Calculators' }} /><Loading what="Loading calculators…" /></Screen>;

  // ---- detail / form view
  if (sel) {
    return (
      <Screen edges={['top']}>
        <Stack.Screen options={{ title: sel.name }} />
        <Pressable onPress={() => setSel(null)}><Row gap={6} style={{ alignItems: 'center' }}><Icon name="chevron.left" size={16} color={p.teal} /><T v="small" color={p.teal}>All calculators</T></Row></Pressable>
        <View style={{ gap: space[1] }}>
          <T v="h1">{sel.name}</T>
          <T v="small" color={p.muted}>{sel.about} · {sel.ref}</T>
        </View>

        <Card style={{ gap: space[4] }}>
          {sel.inputs.map((i) => (
            <View key={i.key} style={{ gap: 6 }}>
              <T v="small" color={p.muted}>{i.label}{i.unit ? ` (${i.unit})` : ''}</T>
              {i.type === 'bool' ? (
                <Pressable onPress={() => setVals((v) => ({ ...v, [i.key]: !v[i.key] }))}
                  style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 10, paddingHorizontal: 14, borderRadius: radius.md, backgroundColor: vals[i.key] ? p.teal + '22' : p.surfaceAlt }}>
                  <T v="body" color={vals[i.key] ? p.teal : p.text}>{vals[i.key] ? 'Yes' : 'No'}</T>
                  <Icon name={vals[i.key] ? 'checkmark.circle.fill' : 'circle'} size={20} color={vals[i.key] ? p.teal : p.faint} />
                </Pressable>
              ) : i.type === 'enum' ? (
                <Segmented options={(i.options ?? []).map((o) => ({ key: o, label: o }))} value={vals[i.key]} onChange={(k) => setVals((v) => ({ ...v, [i.key]: k }))} />
              ) : (
                <TextInput value={String(vals[i.key] ?? '')} onChangeText={(t) => setVals((v) => ({ ...v, [i.key]: t }))}
                  keyboardType="decimal-pad" placeholder="0" placeholderTextColor={p.faint}
                  style={{ paddingVertical: 10, paddingHorizontal: 14, borderRadius: radius.md, backgroundColor: p.surfaceAlt, color: p.text, fontSize: 16 }} />
              )}
            </View>
          ))}
          <Button title={busy ? 'Calculating…' : 'Calculate'} onPress={compute} disabled={busy} loading={busy} />
        </Card>

        {res && !res.error ? (
          <Card tone="teal" style={{ gap: space[2] }}>
            {res.result != null ? (
              <Row style={{ alignItems: 'baseline' }} gap={8}>
                <T v="display" style={{ color: riskColor(res.risk, p) }}>{res.result}</T>
                {res.unit ? <T v="small" color={p.muted}>{res.unit}</T> : null}
              </Row>
            ) : null}
            <T v="body">{res.interpretation}</T>
            {res.detail ? <T v="small" color={p.muted}>{res.detail}</T> : null}
            {res.disclaimer ? <T v="small" color={p.faint}>{res.disclaimer}</T> : null}
          </Card>
        ) : null}
        {res?.error ? <Card><T v="body" color={p.danger}>{res.error}</T></Card> : null}
      </Screen>
    );
  }

  // ---- list view
  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Calculators' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Clinical calculators</T>
        <T v="small" color={p.muted}>{list.data.calculators.length} point-of-care scores — computed locally on your server, with the primary reference.</T>
      </View>
      {Object.entries(groups).map(([cat, cs]) => (
        <View key={cat} style={{ gap: space[2] }}>
          <T v="label">{cat.toUpperCase()}</T>
          {cs.map((c) => (
            <Card key={c.id} onPress={() => open(c)}>
              <Row style={{ alignItems: 'center' }}>
                <View style={{ flex: 1 }}>
                  <T v="h3">{c.name}</T>
                  <T v="small" color={p.muted} numberOfLines={1}>{c.about}</T>
                </View>
                <Icon name="chevron.right" size={13} color={p.faint} />
              </Row>
            </Card>
          ))}
        </View>
      ))}
    </Screen>
  );
}
