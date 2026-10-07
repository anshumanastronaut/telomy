import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { fmtDate, useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, ErrorState, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';
import { Logo } from '@/ui/logo';
import { PatientRow } from '@/ui/patient';

export default function DoctorToday() {
  const p = usePalette();
  const t = useApi<any>('/doctor/today');
  const w = useApi<any>('/doctor/work');
  if (t.error) return <Screen><ErrorState message={t.error} onRetry={t.reload} /></Screen>;
  if (!t.data) return <Screen><Loading what="Preparing your day…" /></Screen>;
  const d = t.data;
  return (
    <Screen onRefresh={() => { t.reload(); w.reload(); }} refreshing={t.loading}>
      <Row><Logo kind="mark" width={46} /><Logo kind="word" width={86} /></Row>
      <T v="small">Telomy Care · Dr. Meera Rao</T>
      <T v="h1">Today</T>
      <Card>
        <Row>
          <Stat label="Patients" value={d.patients} />
          <Stat label="Drafts to review" value={d.awaiting_reviews} color={d.awaiting_reviews ? p.copper : undefined} />
          <Stat label="Overdue labs" value={d.overdue_reports} />
        </Row>
      </Card>
      <Row gap={space[3]}>
        <Card style={{ flex: 1 }} tone="copper" onPress={() => router.push('/doctor/work')}>
          <T v="label">Monthly reports</T>
          <T v="num">{w.data?.monthly_reports.length ?? '—'}</T>
          <T v="small">awaiting your signature</T>
        </Card>
        <Card style={{ flex: 1 }} onPress={() => router.push('/doctor/work')}>
          <T v="label">Consults</T>
          <T v="num">{w.data ? w.data.consults.length + d.consults.length : '—'}</T>
          <T v="small">on-demand + clinic</T>
        </Card>
      </Row>
      <Section title="Needs attention" action="All patients" onAction={() => router.push('/doctor/patients')}>
        <View style={{ gap: space[3] }}>{d.high_priority.map((x: any) => <PatientRow key={x.id} p={x} />)}</View>
      </Section>
      {d.consults.length ? (
        <Section title="Next clinic consultations">
          <Card style={{ paddingVertical: 4 }}>
            {d.consults.slice(0, 4).map((c: any, i: number) => (
              <Row key={c.id} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <T v="body" style={{ flex: 1 }}>{c.name}</T>
                <T v="small">{fmtDate(c.ts)} {c.ts.slice(11, 16)}</T>
              </Row>
            ))}
          </Card>
        </Section>
      ) : null}
    </Screen>
  );
}
