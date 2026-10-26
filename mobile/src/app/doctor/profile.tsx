// Doctor profile & settings hub. Identity, clinical defaults, prescribing, scheduling, consent, notifications,
// security, data — persisted per-org on the mgmt plane (/mgmt/clinic/settings). Reusable care templates live on
// their own screen. Everything here is the real signed-in staff account.
import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { useRole } from '@/lib/role';
import { staffLogout, staffSync } from '@/lib/staff';
import { setAppearance, useAppearance, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, ListRow, Loading, Row, Screen, Section, Segmented, T, useToast } from '@/ui/core';
import { Logo } from '@/ui/logo';
import { ChoiceRow, StepperRow, SwitchRow, TextRow } from '@/ui/settings';

const GOALS = [
  { key: 'longevity', label: 'Longevity' }, { key: 'metabolic', label: 'Metabolic' },
  { key: 'heart', label: 'Heart' }, { key: 'stress', label: 'Stress' }, { key: 'sleep', label: 'Sleep' },
];
const GRADES = [{ key: 'A', label: 'A only' }, { key: 'B', label: 'B+' }, { key: 'C', label: 'C+' }];
const UNITS = [{ key: 'metric', label: 'Metric' }, { key: 'imperial', label: 'Imperial' }];

export default function DoctorProfile() {
  const p = usePalette();
  const appearance = useAppearance();
  const { setRole } = useRole();
  const me = staffSync();
  const { show } = useToast();
  const { data, setData, loading } = useApi<any>('/mgmt/clinic/settings');

  const set = (k: string, v: any) => {
    setData((d: any) => ({ ...(d || {}), [k]: v }));
    api('/mgmt/clinic/settings', { method: 'PUT', body: { [k]: v } }).then(() => show('Saved', 'success')).catch((e: any) => show(e.message, 'alert'));
  };
  const signOut = async () => { await staffLogout(); await setRole(null); router.replace('/welcome' as any); };

  return (
    <Screen>
      <View style={{ alignItems: 'center', paddingVertical: 8 }}><Logo kind="full" width={130} /></View>
      <Card>
        <T v="h2">{data?.display_name || me?.name || '—'}</T>
        <Row style={{ alignItems: 'center', gap: 8, marginTop: 4 }}>
          <Chip label={me?.label ?? 'Doctor'} fg={p.teal} bg={p.tealSoft} />
          <T v="small" color={p.muted}>{me?.org}</T>
          {data?.specialty ? <T v="small" color={p.muted}>· {data.specialty}</T> : null}
        </Row>
      </Card>

      {!data && loading ? <Loading what="Loading your settings…" /> : null}
      {data ? (
        <>
          <Section title="Identity">
            <Card style={{ paddingVertical: 2 }}>
              <TextRow icon="person.text.rectangle" title="Display name" placeholder={me?.name} value={data.display_name} onChangeText={(v) => set('display_name', v)} />
              <Divider />
              <TextRow icon="stethoscope" title="Specialty" placeholder="e.g. Internal medicine" value={data.specialty} onChangeText={(v) => set('specialty', v)} />
              <Divider />
              <TextRow icon="number" title="Registration no." placeholder="State medical council no." value={data.registration_no} onChangeText={(v) => set('registration_no', v)} />
              <Divider />
              <TextRow icon="signature" title="Signature line" placeholder="Appears under your signature on signed documents" value={data.signature_line} onChangeText={(v) => set('signature_line', v)} multiline />
            </Card>
          </Section>

          <Section title="Clinical defaults">
            <Card style={{ paddingVertical: 2 }}>
              <ChoiceRow icon="target" title="Default care focus" subtitle="Where new patients start" options={GOALS} value={data.default_goal} onChange={(v) => set('default_goal', v)} />
              <Divider />
              <StepperRow icon="calendar" title="Default follow-up" value={data.followup_weeks} min={1} max={52} unit="wks" onChange={(v) => set('followup_weeks', v)} />
              <Divider />
              <ChoiceRow icon="ruler" title="Units" options={UNITS} value={data.units} onChange={(v) => set('units', v)} />
            </Card>
          </Section>

          <Section title="Prescribing">
            <Card style={{ paddingVertical: 2 }}>
              <ChoiceRow icon="checkmark.seal" title="Minimum evidence grade" subtitle="What shows in Longevity Rx by default" options={GRADES} value={data.evidence_threshold} onChange={(v) => set('evidence_threshold', v)} />
              <Divider />
              <SwitchRow icon="signature" title="Auto-sign my recommendations" subtitle="Off = review before anything reaches the patient" value={data.auto_sign} onValueChange={(v) => set('auto_sign', v)} />
              <Divider />
              <ListRow icon="square.stack.3d.up" title="Care templates" subtitle="Build reusable 'Cardiac' / 'Metabolic' presets, apply in one tap" onPress={() => router.push('/doctor/templates' as any)} />
            </Card>
          </Section>

          <Section title="Scheduling & consent">
            <Card style={{ paddingVertical: 2 }}>
              <StepperRow icon="clock" title="Consult length" value={data.consult_minutes} min={5} max={120} step={5} unit="min" onChange={(v) => set('consult_minutes', v)} />
              <Divider />
              <SwitchRow icon="hand.raised" title="Require consent before sharing" subtitle="Patient must consent before records are shared out" value={data.require_consent} onValueChange={(v) => set('require_consent', v)} />
            </Card>
          </Section>

          <Section title="Notifications">
            <Card style={{ paddingVertical: 2 }}>
              <SwitchRow icon="waveform.path.ecg" title="New findings to review" value={data.notify_findings} onValueChange={(v) => set('notify_findings', v)} />
              <Divider />
              <SwitchRow icon="calendar" title="New bookings" value={data.notify_bookings} onValueChange={(v) => set('notify_bookings', v)} />
              <Divider />
              <SwitchRow icon="testtube.2" title="Lab results in" value={data.notify_labs} onValueChange={(v) => set('notify_labs', v)} />
            </Card>
          </Section>

          <Section title="Security">
            <Card style={{ paddingVertical: 2 }}>
              <SwitchRow icon="faceid" title="Biometric lock" subtitle="Require Face ID / passcode to open the console" value={data.biometric_lock} onValueChange={(v) => set('biometric_lock', v)} />
              <Divider />
              <ListRow icon="qrcode" title="ABHA & data exchange" subtitle="ABDM linkage — status & setup" onPress={() => router.push('/abha' as any)} />
            </Card>
          </Section>
        </>
      ) : null}

      <Section title="Appearance">
        <Segmented options={[{ key: 'dark', label: 'Dark' }, { key: 'light', label: 'Light' }, { key: 'system', label: 'System' }]} value={appearance} onChange={setAppearance} />
      </Section>

      <Section title="Account">
        <Card>
          <Row><T v="body" style={{ flex: 1 }} color={p.muted}>Workspace</T><T v="body">{me?.workspace ?? 'doctor'}</T></Row>
          <Row><T v="body" style={{ flex: 1 }} color={p.muted}>Organisation</T><T v="body" numberOfLines={1}>{me?.org ?? '—'}</T></Row>
          <T v="small" color={p.faint} style={{ marginTop: 4 }}>Staff accounts and billing are managed on the web console.</T>
        </Card>
      </Section>

      <Button kind="secondary" title="Sign out · switch role" icon="arrow.left.arrow.right" testID="switch-role" onPress={signOut} />
      <View style={{ height: 24 }} />
    </Screen>
  );
}
