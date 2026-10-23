// Doctor's view of an assigned (care-graph) patient: the tenancy Patient-360 from /mgmt/clinic/patients/{id}/
// overview — the patient's OWN data (biomarkers, AI summary, organ ages, vitals/recovery/habits availability),
// resolved through the care graph. Distinct from the legacy /doctor/patients/{id} (seed-panel) detail.
import { Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, Chip, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';

export default function DoctorPatient() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: d, error, reload } = useApi<any>(`/mgmt/clinic/patients/${id}/overview`, [id]);
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen edges={[]}><Loading what="Opening patient…" /></Screen>;
  const pt = d.patient ?? {};
  const bm = d.biomarkers ?? {};
  const raw: any[] = bm.raw ?? [];
  const organs = d.organs?.organs ?? (Array.isArray(d.organs) ? d.organs : null);
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: pt.name ?? 'Patient' }} />
      <Card>
        <T v="h2">{pt.name ?? `#${id}`}</T>
        <T v="small">{[pt.age ? `${Math.round(pt.age)} y` : null, pt.sex, pt.city].filter(Boolean).join(' · ') || '—'}
          {pt.linked ? ' · live record' : ' · no linked record'}</T>
        {pt.conditions?.length ? <Row style={{ flexWrap: 'wrap' }}>{pt.conditions.map((c: string) => <Chip key={c} label={c} />)}</Row> : null}
      </Card>

      {d.ai_summary?.text ? (
        <Card tone="teal" testID="ai-summary">
          <Row><T v="label" style={{ flex: 1 }}>AI summary · Sinc draft</T><Chip label="Review" fg={p.teal} bg={p.surface} /></Row>
          <T v="body">{d.ai_summary.text}</T>
          {d.ai_summary.disclaimer ? <T v="small" color={p.muted}>{d.ai_summary.disclaimer}</T> : null}
        </Card>
      ) : null}

      {organs?.length ? (
        <Section title="Organ ages">
          <Card style={{ gap: space[2] }}>
            {organs.map((o: any) => (
              <Row key={o.organ ?? o.label}>
                <T v="body" style={{ flex: 1 }}>{o.label ?? o.organ}</T>
                <T v="body">{o.organ_age != null ? `${o.organ_age} y` : '—'}</T>
                {o.age_acceleration_years != null ? (
                  <T v="small" color={o.age_acceleration_years > 2 ? p.danger : o.age_acceleration_years < -2 ? p.teal : p.muted}>
                    {' '}{o.age_acceleration_years > 0 ? '+' : ''}{o.age_acceleration_years}y
                  </T>
                ) : null}
              </Row>
            ))}
          </Card>
        </Section>
      ) : null}

      <Section title={`Biomarkers · ${raw.length}`}>
        {raw.length ? (
          <Card style={{ gap: space[2] }}>
            {raw.map((r: any, i: number) => (
              <Row key={`${r.id ?? r.marker}-${i}`}>
                <T v="body" style={{ flex: 1 }}>{r.marker ?? r.id}</T>
                <T v="body">{r.value ?? '—'}</T>
              </Row>
            ))}
            {bm.note ? <T v="small" color={p.muted}>{bm.note}</T> : null}
          </Card>
        ) : <Card><T v="small">No lab results on file for this patient yet.</T></Card>}
      </Section>

      <Section title="Other data">
        <Card style={{ gap: space[1] }}>
          <T v="small">Vitals: {d.vitals?.available ? 'available' : (d.vitals?.note ?? 'none')}</T>
          <T v="small">Recovery & sleep: {d.recovery_sleep?.available ? 'available' : 'none'}</T>
          <T v="small">Habits: {d.habits?.available ? 'available' : 'none'}</T>
        </Card>
      </Section>
      <View style={{ height: space[8] }} />
    </Screen>
  );
}
