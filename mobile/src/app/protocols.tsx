// Protocols to discuss (B6) — evidence-graded longevity levers matched to your labs. Lifestyle & supplements shown
// fully; prescription/hormone/peptide options are clinician-gated (name only, routed to your doctor). Not a
// prescription — decision support to discuss with your care team. Backend: /me/protocols.
import { router, Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Empty, Icon, Loading, Row, Screen, Section, T } from '@/ui/core';

type Full = { id: string; name: string; category: string; status?: string; grade: string; scope: string; why: string[]; effect?: string; dose?: string; caution?: string; rationale?: string; doctor_gate?: boolean };
type Lite = { id: string; name: string; category: string; grade: string; scope: string; why: string[]; doctor_gate: boolean };
type Plan = { foundation: Full[]; supplements: Full[]; clinician_only: Lite[]; counts: Record<string, number>; disclaimer: string; note: string };

const gradeColor = (g: string) => (g === 'A' ? '#2F8F6B' : g === 'B' ? '#4FD08F' : g === 'C' ? '#C98A1B' : '#D3523F');

function Badge({ g, p }: { g: string; p: any }) {
  const c = gradeColor(g);
  return <Row gap={4} style={{ alignItems: 'center', backgroundColor: c + '22', borderRadius: radius.sm, paddingVertical: 2, paddingHorizontal: 7 }}>
    <T v="small" style={{ fontWeight: '700', color: c }}>{g}</T></Row>;
}

export default function Protocols() {
  const p = usePalette();
  const r = useApi<Plan>('/me/protocols');
  if (!r.data) return <Screen><Stack.Screen options={{ title: 'Protocols' }} /><Loading what="Matching protocols to your labs…" /></Screen>;
  const d = r.data;
  const none = !d.foundation.length && !d.supplements.length && !d.clinician_only.length;

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Protocols to discuss' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Protocols to discuss</T>
        <T v="small" color={p.muted}>Evidence-graded levers matched to your biomarkers. Decision support, not a prescription — discuss with your care team.</T>
      </View>

      {none ? (
        <Empty title="Add labs to get matched" body="Once you have results, we match evidence-graded lifestyle, supplement and clinician-led options to your biomarkers."
          actions={[{ title: 'Add a report', onPress: () => router.push('/upload') }]} />
      ) : (
        <>
          {d.foundation.length ? (
            <Section title="Foundation — do these first">
              {d.foundation.map((x) => (
                <Card key={x.id} style={{ gap: space[2], marginBottom: space[2] }}>
                  <Row style={{ alignItems: 'center' }}>
                    <T v="h3" style={{ flex: 1 }}>{x.name}</T>
                    <Badge g={x.grade} p={p} />
                  </Row>
                  <T v="small" color={p.muted}>{x.scope}</T>
                  {x.effect ? <T v="small">{x.effect}</T> : null}
                  {x.dose ? <T v="small" color={p.teal}>How: {x.dose}</T> : null}
                </Card>
              ))}
            </Section>
          ) : null}

          {d.supplements.length ? (
            <Section title="Supplements — biomarker-driven">
              {d.supplements.map((x) => (
                <Card key={x.id} style={{ gap: space[1], marginBottom: space[2] }}>
                  <Row style={{ alignItems: 'center' }}>
                    <T v="h3" style={{ flex: 1 }}>{x.name}</T>
                    <Badge g={x.grade} p={p} />
                  </Row>
                  <T v="small" color={p.muted}>{x.scope}</T>
                  {x.dose ? <T v="small" color={p.teal}>Typical: {x.dose}</T> : null}
                  {x.caution ? <T v="small" color={p.faint}>{x.caution}</T> : null}
                </Card>
              ))}
              <T v="small" color={p.faint} style={{ paddingHorizontal: space[1] }}>Run supplements past your clinician, especially if you take medication.</T>
            </Section>
          ) : null}

          {d.clinician_only.length ? (
            <Section title="Clinician-led options">
              <Card tone="copper" style={{ gap: space[2] }}>
                <Row gap={8} style={{ alignItems: 'flex-start' }}>
                  <Icon name="stethoscope" size={16} color={p.copper} />
                  <T v="small" style={{ flex: 1 }}>These prescription, hormone or peptide options may fit your biomarkers, but only a doctor on your care team can review and prescribe them. We show them by name only.</T>
                </Row>
                {d.clinician_only.map((x) => (
                  <Row key={x.id} style={{ alignItems: 'center' }}>
                    <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: p.copper, marginRight: 8 }} />
                    <T v="body" style={{ flex: 1 }}>{x.name}</T>
                    <Badge g={x.grade} p={p} />
                  </Row>
                ))}
                <Button kind="secondary" icon="message" title="Ask my care team" onPress={() => router.push('/consult')} />
              </Card>
            </Section>
          ) : null}

          <Row style={{ alignItems: 'flex-start', paddingHorizontal: space[1] }}>
            <Icon name="info.circle" size={14} color={p.faint} />
            <T v="small" color={p.faint} style={{ flex: 1, marginLeft: space[2] }}>{d.disclaimer}</T>
          </Row>
        </>
      )}
    </Screen>
  );
}
