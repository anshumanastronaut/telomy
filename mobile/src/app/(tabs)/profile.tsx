import { router } from 'expo-router';
import React from 'react';
import { Alert, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { useRole } from '@/lib/role';
import { usePalette } from '@/lib/theme';
import { Ring } from '@/ui/charts';
import { Card, Chip, Divider, ListRow, Row, Screen, Section, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

export default function Profile() {
  const p = usePalette();
  const prof = useApi<any>('/profile');
  const comp = useApi<any>('/completeness');
  const health = useApi<any>('/health');
  const plans = useApi<any>('/plans');
  const { setRole } = useRole();
  const pr = prof.data;
  return (
    <Screen onRefresh={() => { prof.reload(); comp.reload(); }} refreshing={prof.loading}>
      <Row>
        <View style={{ width: 56, height: 56, borderRadius: 28, backgroundColor: p.tealSoft, alignItems: 'center', justifyContent: 'center' }}>
          <T v="h2" color={p.teal}>{pr?.first_name?.[0] ?? '·'}</T>
        </View>
        <View style={{ flex: 1 }}>
          <T v="h2">{pr?.name ?? '—'}</T>
          <T v="small">{pr ? `${pr.age} y · ${pr.sex} · ${pr.city}` : ''}</T>
        </View>
        {pr?.is_test_profile ? <Chip label="Test profile" fg={p.copper} bg={p.copperSoft} /> : null}
      </Row>

      <Card onPress={() => router.push('/completeness')}>
        <Row>
          <Ring value={comp.data?.score ?? null} size={52} />
          <View style={{ flex: 1 }}>
            <T v="h3">Vault completeness</T>
            <T v="small">{comp.data ? `${comp.data.items.filter((i: any) => !i.done).length} things would make Sinc's reads sharper` : ''}</T>
          </View>
        </Row>
      </Card>

      <Group title="Plan & doctor">
        <ListRow icon="star" title={`Plan · ${plans.data?.subscription.plan_detail.name ?? '—'}`} subtitle="Compare Free, Essential, Plus and Longevity Pro" onPress={() => router.push('/plans')} />
        <ListRow icon="doc.text" title="Monthly reports" subtitle="Auto-generated each month, doctor-signed on Plus" onPress={() => router.push('/monthly')} />
        <ListRow icon="video" title="Consult a doctor now" subtitle="GP ₹699 · specialist ₹1,499 · included in your plan" onPress={() => router.push('/consult')} />
        <ListRow icon="waveform.path.ecg" title="Disease predictions" subtitle="PREVENT, PCE, diabetes, FIB-4, KFRE" onPress={() => router.push('/predict')} />
      </Group>

      <Group title="Care">
        <ListRow icon="stethoscope" title="Clinicians & appointments" subtitle="Book, prepare a pre-clinic brief" onPress={() => router.push('/care')} />
        <ListRow icon="doc.richtext" title="Specialist pack" subtitle="PDF + FHIR for cardiology, endocrinology…" onPress={() => router.push('/brief')} />
        <ListRow icon="checkmark.seal" title="Review queue (Telomy Care)" subtitle="Sinc drafts awaiting sign-off" onPress={() => router.push('/queue')} />
        <ListRow icon="cross.case" title="Emergency card" subtitle="Blood type, allergies, contacts" onPress={() => router.push('/emergency')} />
        <ListRow icon="pills" title="Medications" subtitle="Schedule, adherence, interactions" onPress={() => router.push('/meds')} />
        <ListRow icon="fork.knife" title="Nutrition" subtitle="Trends and meal history" onPress={() => router.push('/nutrition')} />
      </Group>

      <Group title="Your data">
        <ListRow icon="hand.raised" title="Consent centre" subtitle="Per-purpose, revocable, with history" onPress={() => router.push('/consent')} />
        <ListRow icon="person.2" title="Family Vault" subtitle="Scoped, time-boxed sharing" onPress={() => router.push('/family')} />
        <ListRow icon="brain" title="What Sinc remembers" subtitle="View and delete facts" onPress={() => router.push('/memory')} />
        <ListRow icon="chart.bar.doc.horizontal" title="Research contribution" subtitle="Studies your data helps" onPress={() => router.push('/research')} />
        <ListRow icon="target" title="Goals" subtitle="Activity and nutrition targets" onPress={() => router.push('/goals')} />
      </Group>

      <Group title="App">
        <ListRow icon="sparkles" title="Replay onboarding" onPress={() => router.push('/onboarding')} />
        <ListRow icon="arrow.left.arrow.right" title="Switch role" subtitle="User · Doctor · Wellness centre" onPress={async () => { await setRole(null); router.replace('/welcome' as any); }} testID="switch-role" />
        <ListRow
          icon="arrow.counterclockwise"
          title="Reset test data"
          subtitle="Reloads the dummy profile and reports"
          onPress={() =>
            Alert.alert('Reset test data?', 'This replaces everything with the dummy profile. Undo will not bring changes back.', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Reset', style: 'destructive', onPress: async () => { await api('/admin/reset', { method: 'POST' }); prof.reload(); comp.reload(); } },
            ])
          }
        />
      </Group>
      <View style={{ alignItems: 'center', paddingTop: 8 }}>
        <Logo kind="full" width={120} />
      </View>
      <T v="small" style={{ textAlign: 'center' }}>
        Telomy 0.1.0 · {health.data?.engine ?? ''} · Sinc: {health.data?.sinc ?? ''}
      </T>
      <T v="small" style={{ textAlign: 'center', fontStyle: 'italic' }}>Where human biology becomes intelligent.</T>
    </Screen>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  const kids = React.Children.toArray(children);
  return (
    <Section title={title}>
      <Card style={{ paddingVertical: 2 }}>
        {kids.map((c, i) => (
          <View key={i}>
            {i ? <Divider /> : null}
            {c}
          </View>
        ))}
      </Card>
    </Section>
  );
}
