// Centre member detail — the front-desk record: contact, plan & membership (credits/cycle), status, join date,
// and a shortcut to book. Clinical data stays on the doctor side; this is the operational view.
import { router, Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { Linking, View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { BackButton, Button, Card, Chip, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';

export default function CentreMember() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: m, error, reload, loading } = useApi<any>(`/mgmt/centre/members/${id}?org=${encodeURIComponent(staffOrg())}`, [id]);
  if (error) return <Screen edges={['top']}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!m) return <Screen edges={['top']}><Loading what="Opening member…" /></Screen>;

  const plan = m.fields?.plan;
  const memberships: any[] = m.memberships ?? [];

  return (
    <Screen edges={['top']} onRefresh={reload} refreshing={loading}>
      <BackButton fallback="/centre/members" />
      <Stack.Screen options={{ title: m.name ?? 'Member' }} />
      <Card>
        <Row>
          <View style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: p.tealSoft, alignItems: 'center', justifyContent: 'center' }}>
            <T v="h2" color={p.teal}>{m.name?.[0] ?? '·'}</T>
          </View>
          <View style={{ flex: 1 }}>
            <T v="h2" numberOfLines={1}>{m.name}</T>
            <Row style={{ marginTop: 4, flexWrap: 'wrap' }}>
              {plan ? <Chip label={plan} fg={p.teal} bg={p.tealSoft} /> : null}
              <Chip label={m.status} fg={m.status === 'active' ? p.teal : p.muted} bg={m.status === 'active' ? p.tealSoft : p.surfaceAlt} />
            </Row>
          </View>
        </Row>
      </Card>

      <Section title="Contact">
        <Card style={{ gap: space[1] }}>
          {m.phone ? <Row style={{ justifyContent: 'space-between' }}><T v="body" color={p.muted}>Phone</T><T v="body" color={p.teal} onPress={() => Linking.openURL(`tel:${m.phone}`)}>{m.phone}</T></Row> : null}
          {m.email ? <Row style={{ justifyContent: 'space-between' }}><T v="body" color={p.muted}>Email</T><T v="body" numberOfLines={1}>{m.email}</T></Row> : null}
          {m.joined_on ? <Row style={{ justifyContent: 'space-between' }}><T v="body" color={p.muted}>Joined</T><T v="body">{m.joined_on}</T></Row> : null}
        </Card>
      </Section>

      <Section title="Membership">
        {memberships.length ? memberships.map((x: any, i: number) => (
          <Card key={i} style={{ marginBottom: space[2] }}>
            <Row style={{ justifyContent: 'space-between' }}>
              <T v="h3">{x.data?.plan ?? plan ?? 'Plan'}</T>
              {x.credits_left != null ? <Chip label={`${x.credits_left} credits`} fg={p.teal} bg={p.tealSoft} /> : <Chip label={x.status ?? 'active'} fg={p.muted} bg={p.surfaceAlt} />}
            </Row>
            {x.ends_on ? <T v="small" color={p.faint} style={{ marginTop: 4 }}>Renews / ends {x.ends_on}</T> : null}
          </Card>
        )) : <Card><T v="small" color={p.muted}>No active membership. Enrol them from a plan in Services.</T></Card>}
      </Section>

      {m.patient_id ? (
        <Section title="Clinical record">
          <Card><T v="small" color={p.muted}>This member has a linked Telomy Vault (patient #{m.patient_id}). Their labs, risks and care plan are on the doctor side.</T></Card>
        </Section>
      ) : null}

      <View style={{ marginTop: space[3] }}>
        <Button kind="primary" title="Book a session" onPress={() => router.push('/centre/bookings' as any)} />
      </View>
      <View style={{ height: space[8] }} />
    </Screen>
  );
}
