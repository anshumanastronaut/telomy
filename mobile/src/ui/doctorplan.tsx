// "From your doctor" — what the clinician configured for this patient (focus areas, targets, what to track, a
// note). Shows the member exactly what their doctor wants them to aim for, with their current value next to each
// target. Renders nothing until a doctor has set a plan.
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, Chip, Row, T } from './core';

const FOCUS_LBL: Record<string, string> = { heart: 'Heart & lipids', metabolic: 'Blood sugar', bp: 'Blood pressure', liver: 'Liver', kidney: 'Kidney', inflammation: 'Inflammation', weight: 'Weight', sleep: 'Sleep', recovery: 'Recovery', muscle: 'Muscle' };
const TRACK_LBL: Record<string, string> = { bp: 'Blood pressure', glucose: 'Glucose', weight: 'Weight', steps: 'Steps', sleep: 'Sleep', symptoms: 'Symptoms', meals: 'Meals', mood: 'Mood', pain: 'Pain' };
const T_LBL: Record<string, { label: string; unit: string; lowerBetter: boolean }> = {
  ldl: { label: 'LDL', unit: ' mg/dL', lowerBetter: true }, apob: { label: 'ApoB', unit: ' mg/dL', lowerBetter: true },
  hba1c: { label: 'HbA1c', unit: '%', lowerBetter: true }, sbp: { label: 'Systolic BP', unit: ' mmHg', lowerBetter: true },
  hscrp: { label: 'hs-CRP', unit: ' mg/L', lowerBetter: true }, weight: { label: 'Weight', unit: ' kg', lowerBetter: true }, steps: { label: 'Steps', unit: '/day', lowerBetter: false },
};

export function DoctorPlanCard() {
  const p = usePalette();
  const { data } = useApi<any>('/me/care-config');
  const pred = useApi<any>('/predict');
  if (!data || (!(data.focus?.length) && !(data.note) && !Object.keys(data.targets ?? {}).length && !(data.track?.length))) return null;
  const cur = pred.data?.inputs ?? {};
  const targets: Record<string, number> = data.targets ?? {};

  return (
    <Card tone="teal" style={{ gap: space[1] }}>
      <Row><T v="label" style={{ flex: 1 }}>From your doctor{data.set_by ? ` · ${data.set_by}` : ''}</T></Row>
      {data.note ? <T v="body" style={{ marginTop: 2 }}>{data.note}</T> : null}

      {(data.focus ?? []).length ? (
        <Row style={{ flexWrap: 'wrap', marginTop: 6 }} gap={6}>
          {data.focus.map((k: string) => <Chip key={k} label={FOCUS_LBL[k] ?? k} fg={p.teal} bg={p.surface} />)}
        </Row>
      ) : null}

      {Object.keys(targets).length ? (
        <View style={{ marginTop: 8, gap: 4 }}>
          <T v="label" color={p.muted}>Your targets</T>
          {Object.entries(targets).map(([k, tv]) => {
            const d = T_LBL[k]; if (!d) return null;
            const c = cur[k];
            const met = c == null ? null : d.lowerBetter ? c <= tv : c >= tv;
            return (
              <Row key={k} style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <T v="body">{d.label}</T>
                <Row gap={8} style={{ alignItems: 'center' }}>
                  {c != null ? <T v="small" color={met ? p.teal : p.copper}>you: {Math.round(c * 10) / 10}{d.unit}</T> : null}
                  <Chip label={`target ${tv}${d.unit}`} fg={met === false ? p.copper : p.teal} bg={p.surface} />
                </Row>
              </Row>
            );
          })}
        </View>
      ) : null}

      {(data.track ?? []).length ? (
        <View style={{ marginTop: 8 }}>
          <T v="label" color={p.muted}>Track for your doctor</T>
          <Row style={{ flexWrap: 'wrap', marginTop: 4 }} gap={6}>
            {data.track.map((k: string) => <Chip key={k} label={TRACK_LBL[k] ?? k} fg={p.muted} bg={p.surface} />)}
          </Row>
        </View>
      ) : null}
    </Card>
  );
}
