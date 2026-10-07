import React, { useState } from 'react';
import { Pressable, Switch, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { Button, Card, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';
import { PredictionCards } from '@/ui/predictions';

const LEVERS: { k: string; label: string; unit: string; step: number }[] = [
  { k: 'tc', label: 'Total cholesterol', unit: 'mg/dL', step: 10 },
  { k: 'hdl', label: 'HDL', unit: 'mg/dL', step: 2 },
  { k: 'sbp', label: 'Systolic BP', unit: 'mmHg', step: 5 },
  { k: 'bmi', label: 'BMI', unit: '', step: 0.5 },
  { k: 'hba1c', label: 'HbA1c', unit: '%', step: 0.1 },
];

export default function Predict() {
  const p = usePalette();
  const { data, error, reload } = useApi<any>('/predict');
  const [ch, setCh] = useState<Record<string, any>>({});
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Loading what="Running the risk models…" /></Screen>;
  const x = data.inputs;
  const val = (k: string) => (ch[k] ?? x[k]);
  const fmt = (k: string, v: number) => (v == null ? '—' : k === 'sbp' ? Math.round(v) : Math.round(v * 10) / 10);
  async function run() {
    setBusy(true);
    setRes(await api('/predict/what-if', { body: ch }));
    setBusy(false);
  }
  return (
    <Screen edges={[]}>
      <T v="body" color={p.muted}>Validated, published risk equations run on your own Vault. Each shows its model and citation. These are estimates for a conversation with your doctor — not a diagnosis.</T>
      <PredictionCards models={data.models} />
      <Section title="What if?">
        <Card>
          <T v="small">Change a value to see how your predicted risk moves.</T>
          {LEVERS.map((l) => (
            <Row key={l.k}>
              <T v="body" style={{ flex: 1 }}>{l.label}</T>
              <Pressable onPress={() => setCh({ ...ch, [l.k]: Math.round(((val(l.k) ?? 0) - l.step) * 10) / 10 })} style={stp(p)} accessibilityLabel={`Lower ${l.label}`}><T v="h3">−</T></Pressable>
              <T v="num" style={{ fontSize: 16, width: 64, textAlign: 'center' }} color={ch[l.k] != null ? p.teal : undefined}>{fmt(l.k, val(l.k))}</T>
              <Pressable onPress={() => setCh({ ...ch, [l.k]: Math.round(((val(l.k) ?? 0) + l.step) * 10) / 10 })} style={stp(p)} accessibilityLabel={`Raise ${l.label}`}><T v="h3">+</T></Pressable>
            </Row>
          ))}
          {[['smoker', 'Smoking'], ['statin', 'On a statin'], ['bp_treated', 'On BP medication']].map(([k, l]) => (
            <Row key={k}><T v="body" style={{ flex: 1 }}>{l}</T><Switch value={!!val(k)} onValueChange={(v) => setCh({ ...ch, [k]: v })} trackColor={{ true: p.teal }} /></Row>
          ))}
          <Row>
            <Button style={{ flex: 1 }} title="Recalculate" loading={busy} disabled={!Object.keys(ch).length} onPress={run} testID="what-if" />
            <Button kind="ghost" title="Reset" onPress={() => { setCh({}); setRes(null); }} />
          </Row>
          {res ? (
            <View style={{ gap: 6 }}>
              {Object.entries(res.delta).flatMap(([k, v]: any) =>
                k.startsWith('prevent') ? Object.entries(v).filter(([o]) => ['total_cvd', 'heart_failure'].includes(o)).map(([o, d]: any) =>
                  <Delta key={k + o} label={`${o === 'total_cvd' ? 'Any CVD' : 'Heart failure'} · ${k.includes('thirty') ? '30 y' : '10 y'}`} d={d} />)
                  : [<Delta key={k} label={k === 'cvd' ? 'Heart attack/stroke · 10 y (PCE)' : k === 'diabetes' ? 'Diabetes · 5 y' : 'Kidney failure · 5 y'} d={v} />])}
            </View>
          ) : null}
        </Card>
      </Section>
    </Screen>
  );
}

function Delta({ label, d }: { label: string; d: any }) {
  const p = usePalette();
  return (
    <Row>
      <T v="body" style={{ flex: 1 }}>{label}</T>
      <T v="small">{d.from}% → </T>
      <T v="body" style={{ fontWeight: '700' }} color={d.change < 0 ? p.success : d.change > 0 ? p.danger : p.text}>{d.to}%</T>
    </Row>
  );
}

const stp = (p: any) => ({ width: 36, height: 36, borderRadius: radius.md, borderWidth: 1, borderColor: p.border, alignItems: 'center' as const, justifyContent: 'center' as const });
