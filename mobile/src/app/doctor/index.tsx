import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg, staffSync } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { Card, ErrorState, Icon, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';
import { TelomyLoader } from '@/ui/loader';
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
        <TelomyLoader size="mark" />
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
      <Card tone="teal" onPress={() => router.push('/doctor/copilot' as any)} accessibilityLabel="Ask Sinc">
        <Row style={{ alignItems: 'center' }} gap={space[3]}>
          <View style={{ width: 46, height: 28, alignItems: 'center', justifyContent: 'center' }}><TelomyLoader size="mark" /></View>
          <View style={{ flex: 1 }}>
            <T v="h3">Ask Sinc</T>
            <T v="small">Summaries, analysis & next steps — grounded in your patients' records. You sign off.</T>
          </View>
          <Icon name="chevron.right" size={13} color={p.faint} />
        </Row>
      </Card>

      <Card onPress={() => router.push('/doctor/evidence' as any)} accessibilityLabel="Clinical evidence">
        <Row style={{ alignItems: 'center' }} gap={space[3]}>
          <View style={{ width: 46, height: 46, borderRadius: 23, backgroundColor: p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="books.vertical" size={22} color={p.teal} />
          </View>
          <View style={{ flex: 1 }}>
            <T v="h3">Clinical evidence</T>
            <T v="small">Ask a clinical question — cited, graded answers retrieved from PubMed. Decision support, you decide.</T>
          </View>
          <Icon name="chevron.right" size={13} color={p.faint} />
        </Row>
      </Card>

      <Row gap={space[3]}>
        <Card onPress={() => router.push('/doctor/calculators' as any)} accessibilityLabel="Clinical calculators" style={{ flex: 1 }}>
          <View style={{ alignItems: 'center', gap: 6, paddingVertical: space[1] }}>
            <Icon name="function" size={22} color={p.teal} />
            <T v="h3">Calculators</T>
            <T v="small" color={p.muted} style={{ textAlign: 'center' }}>Point-of-care scores</T>
          </View>
        </Card>
        <Card onPress={() => router.push('/doctor/drug' as any)} accessibilityLabel="Drug reference" style={{ flex: 1 }}>
          <View style={{ alignItems: 'center', gap: 6, paddingVertical: space[1] }}>
            <Icon name="pills" size={22} color={p.teal} />
            <T v="h3">Drug reference</T>
            <T v="small" color={p.muted} style={{ textAlign: 'center' }}>Label · interactions</T>
          </View>
        </Card>
      </Row>

      <Section title="Care review queue" action="Work queue" onAction={() => router.push('/doctor/work')}>
        {careN ? (
          d.care_queue.slice(0, 6).map((c: any) => (
            <Card key={`${c.patient_id}-${c.id}`} onPress={() => router.push(`/doctor/patient/${c.patient_id}` as any)} style={{ marginBottom: space[2] }}>
              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <T v="label" color={p.teal} numberOfLines={1} style={{ flex: 1 }}>{c.patient ?? 'Patient'}</T>
                {c.confidence != null ? <T v="small" color={p.muted}>{Math.round(c.confidence * 100)}%</T> : null}
              </Row>
              <T v="body" style={{ marginTop: 4 }} numberOfLines={2}>{c.title}</T>
            </Card>
          ))
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
