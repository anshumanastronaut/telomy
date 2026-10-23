import { router } from 'expo-router';
import React from 'react';
import { Alert, View } from 'react-native';

import { api, authStatus, logout, useApi } from '@/lib/api';
import { useRole } from '@/lib/role';
import { setAppearance, useAppearance, usePalette } from '@/lib/theme';
import { Ring } from '@/ui/charts';
import { Card, Chip, Divider, Icon, ListRow, Row, Screen, Section, Segmented, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

export default function Profile() {
  const appearance = useAppearance();
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

      <Card tone="teal" onPress={() => router.push('/insurance' as any)} accessibilityLabel="Make yourself fully insured">
        <Row>
          <Icon name="shield.checkered" color={p.teal} />
          <View style={{ flex: 1 }}>
            <T v="h3">Make yourself fully insured</T>
            <T v="small">Cover matched to what your Vault shows — explained, not sold.</T>
          </View>
          <Icon name="chevron.right" size={13} color={p.faint} />
        </Row>
      </Card>

      <Group title="Take care of yourself">
        <ListRow icon="list.bullet.clipboard" title="Your trackers" subtitle="Pain, symptoms, supplements, habits — anything you told Sinc" onPress={() => router.push('/trackers' as any)} />
        <ListRow icon="pills.fill" title="Curated supplements" subtitle="Only what your labs support — dose, timing, evidence grade" onPress={() => router.push('/rx')} />
        <ListRow icon="figure.stand" title="Whole-body scan & tests" subtitle="Blood panels, imaging, genetics — what to test next" onPress={() => router.push('/tests')} />
        <ListRow icon="figure.run" title="Exercise & training" subtitle="Every workout, its load and your training status" onPress={() => router.push('/training' as any)} />
        <ListRow icon="bolt.heart" title="Therapy" subtitle="Sessions, plans and recorded therapies" onPress={() => router.push('/therapy' as any)} />
        <ListRow icon="waveform.path.ecg" title="Live ECG & devices" subtitle="Patch, ring, Apple Health — connect and monitor" onPress={() => router.push('/devices')} />
      </Group>

      <Group title="Plan & doctor">
        <ListRow icon="star" title={`Plan · ${plans.data?.subscription.plan_detail.name ?? '—'}`} subtitle="Compare Free, Essential, Plus and Longevity Pro" onPress={() => router.push('/plans')} />
        <ListRow icon="doc.text" title="Monthly reports" subtitle="Auto-generated each month, doctor-signed on Plus" onPress={() => router.push('/monthly')} />
        <ListRow icon="video" title="Consult a doctor now" subtitle="GP ₹699 · specialist ₹1,499 · included in your plan" onPress={() => router.push('/consult')} />
        <ListRow icon="waveform.path.ecg" title="Disease predictions" subtitle="PREVENT, PCE, diabetes, FIB-4, KFRE" onPress={() => router.push('/predict')} />
      </Group>

      <Group title="Care">
        <ListRow icon="cross.case.fill" title="Emergency & home care" subtitle="Ambulance, home nursing, elder & baby care, lab pickup" onPress={() => router.push('/assistance' as any)} />
        <ListRow icon="stethoscope" title="Clinicians & appointments" subtitle="Book, prepare a pre-clinic brief" onPress={() => router.push('/care')} />
        <ListRow icon="doc.richtext" title="Specialist pack" subtitle="PDF + FHIR for cardiology, endocrinology…" onPress={() => router.push('/brief')} />
        <ListRow icon="checkmark.seal" title="Review queue (Telomy Care)" subtitle="Sinc drafts awaiting sign-off" onPress={() => router.push('/queue')} />
        <ListRow icon="person.text.rectangle" title="About you" subtitle="Date of birth, sex, height, weight" onPress={() => router.push('/about' as any)} />
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

      <Section title="Appearance">
        <Segmented options={[{ key: 'dark', label: 'Dark' }, { key: 'light', label: 'Light' }, { key: 'system', label: 'System' }]} value={appearance} onChange={setAppearance} />
      </Section>

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
      <SignOut />
      <T v="small" style={{ textAlign: 'center', fontStyle: 'italic' }}>Where human biology becomes intelligent.</T>
    </Screen>
  );
}

function SignOut() {
  const p = usePalette();
  const [multi, setMulti] = React.useState(false);
  React.useEffect(() => { authStatus().then((st) => setMulti(st.accounts_enabled)).catch(() => {}); }, []);
  if (!multi) return null;   // only shown when the server is multi-user (there is an account to sign out of)
  return (
    <ListRow icon="rectangle.portrait.and.arrow.right" title="Sign out" subtitle="Lock this Telomy and switch accounts"
      onPress={() => Alert.alert('Sign out?', 'You will need to sign in again.', [{ text: 'Cancel', style: 'cancel' },
        { text: 'Sign out', style: 'destructive', onPress: () => logout() }])} />
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
