// Centre profile & settings hub. Keeps the operations/business nav, and adds real, persisted settings: identity &
// compliance, operations defaults, payments, delivery, consent, notifications, security — stored per-org on the
// mgmt plane (/mgmt/centre/settings).
import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { useRole } from '@/lib/role';
import { staffLogout, staffSync } from '@/lib/staff';
import { setAppearance, useAppearance, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, ListRow, Loading, Row, Screen, Section, Segmented, T, useToast } from '@/ui/core';
import { Logo } from '@/ui/logo';
import { StepperRow, SwitchRow, TextRow } from '@/ui/settings';

export default function CentreProfile() {
  const p = usePalette();
  const appearance = useAppearance();
  const { setRole } = useRole();
  const me = staffSync();
  const { show } = useToast();
  const { data, setData, loading } = useApi<any>('/mgmt/centre/settings');
  const org = (me?.org ?? 'Centre').replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  const set = (k: string, v: any) => {
    setData((d: any) => ({ ...(d || {}), [k]: v }));
    api('/mgmt/centre/settings', { method: 'PUT', body: { [k]: v } }).then(() => show('Saved', 'success')).catch((e: any) => show(e.message, 'alert'));
  };
  const signOut = async () => { await staffLogout(); await setRole(null); router.replace('/welcome' as any); };

  return (
    <Screen>
      <View style={{ alignItems: 'center', paddingVertical: 8 }}><Logo kind="full" width={130} /></View>
      <Card>
        <T v="h2">{data?.legal_name || org}</T>
        <Row style={{ alignItems: 'center', gap: 8, marginTop: 4 }}>
          <Chip label={me?.label ?? 'Wellness centre'} fg={p.teal} bg={p.tealSoft} />
          <T v="small" color={p.muted}>{me?.name}</T>
        </Row>
      </Card>

      <Section title="Operations">
        <Card style={{ paddingVertical: 2 }}>
          <ListRow icon="waveform.path.ecg.rectangle" title="Floor" subtitle="Machines & rooms, live status" onPress={() => router.push('/centre/floor' as any)} />
          <Divider />
          <ListRow icon="person.2" title="Members" subtitle="Roster, plans and records" onPress={() => router.push('/centre/members' as any)} />
          <Divider />
          <ListRow icon="calendar" title="Bookings" subtitle="Schedule, check-in and status" onPress={() => router.push('/centre/bookings' as any)} />
          <Divider />
          <ListRow icon="sparkles" title="Services & plans" subtitle="Catalog, pricing and memberships" onPress={() => router.push('/centre/services' as any)} />
          <Divider />
          <ListRow icon="stethoscope" title="Doctors" subtitle="Clinicians at this centre" onPress={() => router.push('/centre/doctors' as any)} />
        </Card>
      </Section>

      <Section title="Business">
        <Card style={{ paddingVertical: 2 }}>
          <ListRow icon="chart.line.uptrend.xyaxis" title="Revenue & payments" subtitle="Totals, gateways, outstanding" onPress={() => router.push('/centre/revenue' as any)} />
          <Divider />
          <ListRow icon="person.3" title="Team performance" subtitle="By staff: utilisation & revenue" onPress={() => router.push('/centre/performance' as any)} />
        </Card>
      </Section>

      {!data && loading ? <Loading what="Loading settings…" /> : null}
      {data ? (
        <>
          <Section title="Identity & compliance">
            <Card style={{ paddingVertical: 2 }}>
              <TextRow icon="building.2" title="Legal name" placeholder={org} value={data.legal_name} onChangeText={(v) => set('legal_name', v)} />
              <Divider />
              <TextRow icon="number" title="GST no." placeholder="GSTIN" value={data.gst_no} onChangeText={(v) => set('gst_no', v)} />
              <Divider />
              <TextRow icon="mappin.and.ellipse" title="Address" placeholder="Centre address" value={data.address} onChangeText={(v) => set('address', v)} multiline />
              <Divider />
              <TextRow icon="phone" title="Phone" placeholder="Front desk number" value={data.phone} onChangeText={(v) => set('phone', v)} keyboardType="phone-pad" />
            </Card>
          </Section>

          <Section title="Operations defaults">
            <Card style={{ paddingVertical: 2 }}>
              <StepperRow icon="clock" title="Default slot" value={data.slot_minutes} min={10} max={180} step={5} unit="min" onChange={(v) => set('slot_minutes', v)} />
              <Divider />
              <StepperRow icon="pause" title="Buffer between slots" value={data.buffer_minutes} min={0} max={60} step={5} unit="min" onChange={(v) => set('buffer_minutes', v)} />
              <Divider />
              <StepperRow icon="sunrise" title="Opens" value={data.open_hour} min={0} max={23} unit=":00" onChange={(v) => set('open_hour', v)} />
              <Divider />
              <StepperRow icon="sunset" title="Closes" value={data.close_hour} min={1} max={24} unit=":00" onChange={(v) => set('close_hour', v)} />
            </Card>
          </Section>

          <Section title="Payments">
            <Card style={{ paddingVertical: 2 }}>
              <StepperRow icon="percent" title="GST rate" value={data.gst_percent} min={0} max={28} step={1} unit="%" onChange={(v) => set('gst_percent', v)} />
              <Divider />
              <SwitchRow icon="creditcard" title="Online payments" subtitle="Cards / UPI / gateways" value={data.online_payments} onValueChange={(v) => set('online_payments', v)} />
              <Divider />
              <SwitchRow icon="indianrupeesign.circle" title="Cash accepted" value={data.cash_payments} onValueChange={(v) => set('cash_payments', v)} />
            </Card>
          </Section>

          <Section title="Delivery & consent">
            <Card style={{ paddingVertical: 2 }}>
              <StepperRow icon="shippingbox" title="Delivery / pickup radius" value={data.delivery_radius_km} min={0} max={50} step={1} unit="km" onChange={(v) => set('delivery_radius_km', v)} />
              <Divider />
              <SwitchRow icon="hand.raised" title="Require consent before sharing" value={data.require_consent} onValueChange={(v) => set('require_consent', v)} />
            </Card>
          </Section>

          <Section title="Notifications">
            <Card style={{ paddingVertical: 2 }}>
              <SwitchRow icon="calendar" title="New bookings" value={data.notify_bookings} onValueChange={(v) => set('notify_bookings', v)} />
              <Divider />
              <SwitchRow icon="calendar.badge.minus" title="Cancellations" value={data.notify_cancellations} onValueChange={(v) => set('notify_cancellations', v)} />
              <Divider />
              <SwitchRow icon="exclamationmark.circle" title="Outstanding payments" value={data.notify_outstanding} onValueChange={(v) => set('notify_outstanding', v)} />
            </Card>
          </Section>

          <Section title="Security">
            <Card style={{ paddingVertical: 2 }}>
              <SwitchRow icon="lock" title="PIN lock on this device" subtitle="Require a PIN to open the centre console" value={data.pin_lock} onValueChange={(v) => set('pin_lock', v)} />
            </Card>
          </Section>
        </>
      ) : null}

      <Section title="Appearance">
        <Segmented options={[{ key: 'dark', label: 'Dark' }, { key: 'light', label: 'Light' }, { key: 'system', label: 'System' }]} value={appearance} onChange={setAppearance} />
      </Section>

      <Section title="Account">
        <Card>
          <Row><T v="body" style={{ flex: 1 }} color={p.muted}>Workspace</T><T v="body">{me?.workspace ?? 'centre'}</T></Row>
          <Row><T v="body" style={{ flex: 1 }} color={p.muted}>Organisation</T><T v="body" numberOfLines={1}>{me?.org ?? '—'}</T></Row>
          <T v="small" color={p.faint} style={{ marginTop: 4 }}>Staff accounts and gateway credentials are managed on the web console.</T>
        </Card>
      </Section>

      <Button kind="secondary" title="Sign out · switch role" icon="arrow.left.arrow.right" testID="switch-role" onPress={signOut} />
      <View style={{ height: 24 }} />
    </Screen>
  );
}
