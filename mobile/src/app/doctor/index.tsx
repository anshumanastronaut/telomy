import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg, staffSync } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { Card, ErrorState, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

export default function DoctorToday() {
  const p = usePalette();
  const org = staffOrg();
  const me = staffSync();
  const inbox = useApi<any>(`/mgmt/clinic/inbox?org=${encodeURIComponent(org)}`);
  const panel = useApi<any[]>('/mgmt/doctor/patients');
  if (inbox.error) return <Screen><ErrorState message={inbox.error} onRetry={() => { inbox.reload(); panel.reload(); }} /></Screen>;
  if (!inbox.data) return <Screen><Loading what="Preparing your day…" /></Screen>;
  const d = inbox.data;
  const careN = d.care_queue?.length ?? 0;
  const tasksN = d.open_tasks?.length ?? 0;
  const patientsN = panel.data?.length ?? d.patients?.length ?? 0;
  return (
    <Screen onRefresh={() => { inbox.reload(); panel.reload(); }} refreshing={inbox.loading}>
      <Row gap={12}>
        <Logo kind="mark" width={34} />
        <View style={{ flex: 1 }}>
          <T v="label" numberOfLines={1}>Telomy Care · {me?.name ?? 'Doctor'}</T>
          <T v="h1">Today</T>
        </View>
      </Row>
      <Card>
        <Row>
          <Stat label="Patients" value={patientsN} />
          <Stat label="To review" value={careN} color={careN ? p.copper : undefined} />
          <Stat label="Open tasks" value={tasksN} />
        </Row>
      </Card>
      <Section title="Care review queue" action="Work queue" onAction={() => router.push('/doctor/work')}>
        {careN ? (
          <Card style={{ paddingVertical: 4 }}>
            {d.care_queue.slice(0, 6).map((c: any, i: number) => (
              <Row key={c.id} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <T v="body" style={{ flex: 1 }} numberOfLines={2}>{c.title}</T>
              </Row>
            ))}
          </Card>
        ) : <Card><T v="small">Nothing awaiting review. Inbox zero.</T></Card>}
      </Section>
      <Section title="Open tasks" action="Patients" onAction={() => router.push('/doctor/patients')}>
        {tasksN ? (
          <Card style={{ paddingVertical: 4 }}>
            {d.open_tasks.slice(0, 6).map((t: any, i: number) => (
              <Row key={t.id} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <T v="body" style={{ flex: 1 }} numberOfLines={2}>{t.text}</T>
                <T v="small">{['', 'Low', 'Normal', 'High'][t.priority] ?? ''}</T>
              </Row>
            ))}
          </Card>
        ) : <Card><T v="small">No open tasks.</T></Card>}
      </Section>
    </Screen>
  );
}
