import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { useRole } from '@/lib/role';
import { usePalette } from '@/lib/theme';

import { Button, Card, Chip, Row, Screen, Section, T } from './core';
import { Logo } from './logo';

/** Profile for doctor / centre: who you are, plan, switch role. */
export function RoleProfile({ kind }: { kind: 'doctor' | 'centre' }) {
  const p = usePalette();
  const { setRole } = useRole();
  const acc = useApi<any[]>('/accounts');
  const plans = useApi<any>('/plans');
  const me = acc.data?.find((a) => a.role === kind);
  return (
    <Screen>
      <View style={{ alignItems: 'center', paddingVertical: 8 }}><Logo kind="full" width={130} /></View>
      <Card>
        <T v="h2">{me?.name ?? '—'}</T>
        <T v="small">{me?.org}</T>
        <Chip label="Demo account · test data" fg={p.copper} bg={p.copperSoft} />
      </Card>
      {kind === 'doctor' ? (
        <Section title="Your plan">
          <Card>
            <T v="h3">Telomy Care doctor seat</T>
            <T v="body">₹{plans.data?.doctor_seat?.toLocaleString('en-IN')}/month · unlimited patients · review queue · monthly report signing · consult tools</T>
            <T v="small">Consult earnings are paid out monthly. Payments are in test mode.</T>
          </Card>
        </Section>
      ) : (
        <Section title="Centre plans">
          {plans.data?.centre.map((c: any) => (
            <Card key={c.id}>
              <Row><T v="h3" style={{ flex: 1 }}>{c.name}</T><T v="num" style={{ fontSize: 17 }}>{c.price_month ? `₹${c.price_month.toLocaleString('en-IN')}` : 'Talk to us'}</T></Row>
              <T v="small">{c.members ? `Up to ${c.members} members · ${c.doctor_seats} doctor seat(s)` : 'Unlimited members, multi-location, API access'}</T>
            </Card>
          ))}
        </Section>
      )}
      <Button kind="secondary" title="Switch role" icon="arrow.left.arrow.right" testID="switch-role" onPress={async () => { await setRole(null); router.replace('/welcome' as any); }} />
    </Screen>
  );
}
