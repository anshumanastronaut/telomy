import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, ErrorState, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';
import { Logo } from '@/ui/logo';
import { PatientRow } from '@/ui/patient';

const inr = (v: number) => `₹${Math.round(v).toLocaleString('en-IN')}`;

export default function CentreDashboard() {
  const p = usePalette();
  const { data: d, error, reload, loading } = useApi<any>('/centre/dashboard');
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen><Loading what="Loading your centre…" /></Screen>;
  const change = d.revenue_prev_month ? Math.round((100 * (d.revenue_month - d.revenue_prev_month)) / d.revenue_prev_month) : null;
  const done = d.today.filter((b: any) => ['completed', 'checked_in'].includes(b.status)).length;
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <Row><Logo kind="mark" width={46} /><Logo kind="word" width={86} /></Row>
      <T v="small">Halo Longevity Centre (test)</T>
      <T v="h1">Dashboard</T>
      <Card>
        <Row>
          <Stat label="Revenue this month" value={inr(d.revenue_month)} sub={change != null ? `${change >= 0 ? '+' : ''}${change}% vs ${d.revenue_compare}` : undefined} color={change != null && change < 0 ? p.danger : undefined} />
          <Stat label="Sessions" value={d.sessions_month} />
        </Row>
        <Row>
          <Stat label="Members" value={d.members} sub={`${d.active_30d} active in 30 days`} />
          <Stat label="No-shows (30 d)" value={d.no_shows_30d} color={d.no_shows_30d > 20 ? p.warn : undefined} />
        </Row>
      </Card>
      <Card onPress={() => router.push('/centre/bookings')}>
        <Row><T v="h3" style={{ flex: 1 }}>Today · {d.today.length} bookings</T><T v="small">{done} checked in or done</T></Row>
        {d.today.slice(0, 5).map((b: any) => (
          <Row key={b.id}><T v="small" style={{ width: 48 }}>{b.ts.slice(11, 16)}</T><T v="body" style={{ flex: 1 }} numberOfLines={1}>{b.service}</T><T v="small">{b.name.split(' ')[0]}</T></Row>
        ))}
      </Card>
      <Section title="Utilisation · last 30 days" action="Services" onAction={() => router.push('/centre/services')}>
        <Card>
          {d.utilisation.map((u: any) => (
            <View key={u.id} style={{ gap: 4 }}>
              <Row><T v="body" style={{ flex: 1 }}>{u.name}</T><T v="small">{u.sessions} sessions · {u.utilisation}%</T></Row>
              <View style={{ height: 6, borderRadius: 3, backgroundColor: p.surfaceAlt }}><View style={{ width: `${Math.min(100, u.utilisation)}%`, height: 6, borderRadius: 3, backgroundColor: p.teal }} /></View>
            </View>
          ))}
        </Card>
      </Section>
      <Section title="Members at risk" action="All members" onAction={() => router.push('/centre/members')}>
        <View style={{ gap: space[3] }}>{d.at_risk.map((x: any) => <PatientRow key={x.id} p={x} />)}</View>
        <T v="small">Risk comes from members' shared Vault data, with their consent. Suggest a doctor consult or a retest.</T>
      </Section>
      {d.lapsing.length ? (
        <Section title="Not seen in 30 days">
          <Card>{d.lapsing.map((x: any) => <T key={x.id} v="body">{x.name} · {x.plan}</T>)}</Card>
        </Section>
      ) : null}
    </Screen>
  );
}
