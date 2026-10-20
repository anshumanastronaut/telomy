// Telomy Report — the trained-model picture of your most recent blood/body panel, served by the backend
// /me/report endpoint (NHANES-trained clocks + the disease/mortality/muscle engines). It is shown ALONGSIDE
// the app's existing guideline bioage (/longevity, /age), clearly labelled "trained" vs "clinical", never
// silently overriding it. Everything is a model estimate for discussion with a clinician — not a diagnosis.
import { router, Stack } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Dial } from '@/ui/charts';
import { Card, Empty, ErrorState, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';

const COND = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function ReportScreen() {
  const p = usePalette();
  const { data, error, reload } = useApi<any>('/me/report');

  if (error) return <Screen edges={[]}><Stack.Screen options={{ title: 'Telomy Report' }} /><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Stack.Screen options={{ title: 'Telomy Report' }} /><Loading what="Running your models…" /></Screen>;

  if (data.status === 'need_more_data') {
    return (
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Telomy Report' }} />
        <Empty
          title="Not enough to model yet"
          body={data.note || 'Upload a blood report and we’ll generate your trained-model report.'}
          actions={[{ title: 'Upload a report', onPress: () => router.push('/upload') }]}
        />
      </Screen>
    );
  }

  const t = data.trained ?? {};
  const ba = t.blood_age ?? {};
  const bio = t.biological_age ?? {};
  const mus = t.muscular_age ?? {};
  const mort = t.mortality_10y ?? {};
  const ranked: any[] = (t.disease_screen?.ranked ?? []).filter((d: any) => d?.probability != null);
  const flagged = ranked.filter((d) => d.probability >= 0.5);

  const bloodAge = ba.predicted_age_years != null ? Math.round(ba.predicted_age_years) : null;
  const chrono = bio.age ?? ba.age ?? null; // calendar age if the engine echoed it

  const accColor = (a: number | null | undefined) => (a == null ? p.muted : a <= -1 ? p.teal : a >= 2 ? p.copper : p.text);
  const accText = (a: number | null | undefined) =>
    a == null ? '—' : a === 0 ? 'on track' : `${a > 0 ? '+' : ''}${a}y ${a > 0 ? 'older' : 'younger'}`;

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Telomy Report' }} />

      <View style={{ alignItems: 'center' }}>
        <Dial value={bloodAge} chrono={chrono} size={240} />
      </View>
      <T v="small" color={p.muted} style={{ textAlign: 'center' }}>
        Blood age from the trained clock{ba.typical_error_years ? ` · ±${Math.round(ba.typical_error_years)}y typical error` : ''}
      </T>

      {t.summary ? (
        <Section title="In plain terms">
          <Card><T v="body">{t.summary}</T></Card>
        </Section>
      ) : null}

      <Section title="Your ages, by model">
        <Card>
          <Row>
            <Stat label="Biological (PhenoAge)" value={bio.phenoage_years != null ? Math.round(bio.phenoage_years) : null} unit="y" />
            <Stat label="Acceleration" value={accText(bio.age_acceleration_years)} color={accColor(bio.age_acceleration_years)} />
          </Row>
          {mus.muscular_age_years != null ? (
            <Row>
              <Stat label="Muscular / body comp" value={Math.round(mus.muscular_age_years)} unit="y" />
              <Stat label="vs calendar" value={accText(mus.muscular_age_acceleration_years)} color={accColor(mus.muscular_age_acceleration_years)} />
            </Row>
          ) : null}
          {mort.risk_10y != null ? (
            <Stat label="Modelled 10-year mortality risk (population ranking, not a prognosis)" value={`${Math.round(mort.risk_10y * 100)}%`} />
          ) : null}
        </Card>
      </Section>

      {ranked.length ? (
        <Section title="Disease screen">
          <Card>
            <T v="small">Ranked model signals from your routine markers. A high number is a reason to look with your doctor — not a diagnosis.</T>
            {ranked.slice(0, 5).map((d) => {
              const pct = Math.round(d.probability * 100);
              const hot = d.probability >= 0.5;
              return (
                <Row key={d.condition}>
                  <T v="body" style={{ flex: 1 }}>{COND(d.condition)}</T>
                  <View style={{ width: 110, height: 8, backgroundColor: p.surfaceAlt, borderRadius: 4, overflow: 'hidden' }}>
                    <View style={{ width: `${pct}%`, height: 8, backgroundColor: hot ? p.copper : p.graphite }} />
                  </View>
                  <T v="num" style={{ fontSize: 14, width: 44, textAlign: 'right', color: hot ? p.copper : p.text }}>{pct}%</T>
                </Row>
              );
            })}
          </Card>
        </Section>
      ) : null}

      <Section title="How to read this">
        <Card>
          <T v="small">
            {data.note || 'trained = NHANES-trained clocks + engines; clinical = the app’s guideline model. Shown side by side.'}
          </T>
          {data.panel_markers_used?.length ? (
            <T v="small" color={p.muted} style={{ marginTop: 8 }}>Markers used: {data.panel_markers_used.length} ({data.panel_markers_used.slice(0, 8).map(COND).join(', ')}{data.panel_markers_used.length > 8 ? '…' : ''})</T>
          ) : null}
          <Pressable onPress={() => router.push('/longevity')} style={{ marginTop: 10 }}>
            <T v="small" color={p.teal}>See the clinical PhenoAge breakdown →</T>
          </Pressable>
        </Card>
      </Section>

      {t.disclaimer ? (
        <T v="small" color={p.muted} style={{ textAlign: 'center', marginTop: 8, marginBottom: 24 }}>{t.disclaimer}</T>
      ) : null}
    </Screen>
  );
}
