// Emergency & home care — one tap to an ambulance, and on-demand home-assistance services (nursing, elder and
// child care, physiotherapy, lab pickup, medicine delivery, a doctor home visit). Requests are logged to the
// Vault and surface to the member's clinic/centre to fulfil (same orders/bookings pipeline the console uses).
import { router } from 'expo-router';
import React, { useState } from 'react';
import { Linking, Pressable, View } from 'react-native';

import { api } from '@/lib/api';
import { localIso } from '@/lib/events';
import { radius, space, type, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';
import type { SFSymbol } from 'expo-symbols';

const AMBULANCE = '108';   // India national emergency medical number

type Svc = { id: string; icon: SFSymbol; title: string; sub: string };
const HOME_CARE: Svc[] = [
  { id: 'doctor_home', icon: 'stethoscope', title: 'Doctor home visit', sub: 'A GP or physician at your door' },
  { id: 'nursing', icon: 'cross.case.fill', title: 'Home nursing', sub: 'Injections, wound care, post-op, IV' },
  { id: 'elder_care', icon: 'figure.roll', title: 'Elder / old-age care', sub: 'Trained attendant, day or live-in' },
  { id: 'baby_care', icon: 'figure.and.child.holdinghands', title: 'Baby & child care', sub: 'Postnatal nurse, nanny, paediatric' },
  { id: 'physio_home', icon: 'figure.walk', title: 'Physiotherapy at home', sub: 'Rehab and mobility sessions' },
  { id: 'lab_pickup', icon: 'testtube.2', title: 'Lab sample pickup', sub: 'Phlebotomist comes to you' },
  { id: 'medicine', icon: 'pills.fill', title: 'Medicine delivery', sub: 'Your prescriptions, delivered' },
  { id: 'attendant', icon: 'person.fill.checkmark', title: 'Attendant / caregiver', sub: 'Hourly or full-day support' },
];

export default function Assistance() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [requested, setRequested] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState<string | null>(null);

  const request = async (s: Svc) => {
    setBusy(s.id);
    // record it to the Vault; the clinic/centre picks it up to fulfil. queue:true so a flaky network never loses it.
    api('/events', { body: { kind: 'life', label: `Requested: ${s.title}`, ts: localIso(), data: { service: s.id, request: 'home_assistance' } }, queue: true }).catch(() => {});
    setRequested((r) => ({ ...r, [s.id]: true }));
    setBusy(null);
    show(`${s.title} requested — the clinic will call to confirm time and address.`, 'success');
  };

  return (
    <Screen edges={[]}>
      <T v="h1">Emergency & home care</T>
      <T v="small" color={p.muted}>An ambulance in one tap, and trained help at home when you need it.</T>

      {/* Emergency */}
      <Card style={{ gap: space[3], borderWidth: 1, borderColor: p.danger, backgroundColor: p.dangerSoft }}>
        <Row gap={8}><Icon name="cross.circle.fill" size={18} color={p.danger} /><T v="label" color={p.danger} style={{ flex: 1 }}>Emergency</T></Row>
        <T v="body">If this is a medical emergency, call an ambulance now.</T>
        <Pressable onPress={() => Linking.openURL(`tel:${AMBULANCE}`)} accessibilityRole="button"
          style={({ pressed }) => ({ backgroundColor: p.danger, borderRadius: 999, paddingVertical: 16, alignItems: 'center', transform: [{ scale: pressed ? 0.98 : 1 }] })}>
          <Row gap={8}><Icon name="phone.fill" size={18} color={p.onAccent} /><T v="body" color={p.onAccent} style={{ fontWeight: '700' }}>Call ambulance · {AMBULANCE}</T></Row>
        </Pressable>
        <Pressable onPress={() => router.push('/emergency')} accessibilityRole="button">
          <T v="small" color={p.teal} style={{ textAlign: 'center' }}>Your emergency card — blood type, allergies, contacts →</T>
        </Pressable>
      </Card>

      {/* Home assistance */}
      <Section title="Home assistance">
        <View style={{ gap: space[2] }}>
          {HOME_CARE.map((s) => (
            <Card key={s.id} style={{ gap: space[2] }}>
              <Row gap={10}>
                <Icon name={s.icon} size={18} color={p.teal} />
                <View style={{ flex: 1 }}>
                  <T v="body">{s.title}</T>
                  <T v="small" color={p.muted}>{s.sub}</T>
                </View>
                {requested[s.id]
                  ? <Row gap={4}><Icon name="checkmark.circle.fill" size={16} color={p.teal} /><T v="small" color={p.teal}>Requested</T></Row>
                  : <Button kind="secondary" title={busy === s.id ? '…' : 'Request'} onPress={() => request(s)} />}
              </Row>
            </Card>
          ))}
        </View>
      </Section>
      <T v="small" color={p.faint} style={{ textAlign: 'center' }}>Requests go to your clinic/centre to confirm timing, address and payment. Not for emergencies — call {AMBULANCE}.</T>
      <View style={{ height: space[8] }} />
      {toast}
    </Screen>
  );
}
