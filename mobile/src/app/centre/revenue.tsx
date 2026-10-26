// Centre revenue — the money view: total, invoiced/paid, session revenue, outstanding, and the payment-gateway
// breakdown (gross/net/fees per gateway) with MRR.
import { Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { BackButton, Card, ErrorState, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';

const inr = (v: number) => `₹${Math.round(v || 0).toLocaleString('en-IN')}`;
const org = () => encodeURIComponent(staffOrg());

export default function CentreRevenue() {
  const p = usePalette();
  const rev = useApi<any>(`/mgmt/centre/revenue?org=${org()}`);
  const bill = useApi<any>(`/mgmt/billing/summary?org=${org()}`);
  if (rev.error) return <Screen edges={['top']}><ErrorState message={rev.error} onRetry={rev.reload} /></Screen>;
  if (!rev.data) return <Screen edges={['top']}><Loading what="Totting up…" /></Screen>;
  const r = rev.data; const b = bill.data;
  const gw: any[] = b?.by_gateway ?? [];
  const gmax = Math.max(1, ...gw.map((g) => g.gross));

  return (
    <Screen edges={['top']} onRefresh={() => { rev.reload(); bill.reload(); }} refreshing={rev.loading}>
      <BackButton fallback="/centre" />
      <Stack.Screen options={{ title: 'Revenue' }} />
      <T v="h1">Revenue</T>
      <Card style={{ marginTop: space[2] }}>
        <Row><Stat label="Total revenue" value={inr(r.total_revenue)} /><Stat label="Outstanding" value={inr(r.outstanding)} /></Row>
        <Row style={{ marginTop: space[2] }}>
          <Stat label="Sessions" value={r.sessions_delivered ?? 0} />
          <Stat label="Session rev" value={inr(r.session_revenue)} />
          <Stat label="Invoiced" value={inr(r.invoiced_paid)} />
        </Row>
      </Card>

      {b ? (
        <Section title="Payments by gateway">
          <Card style={{ gap: space[2] }}>
            {gw.map((g) => (
              <View key={g.gateway}>
                <Row style={{ justifyContent: 'space-between' }}>
                  <T v="body" style={{ textTransform: 'capitalize' }}>{g.gateway}</T>
                  <T v="body">{inr(g.gross)}</T>
                </Row>
                <View style={{ height: 7, borderRadius: 4, backgroundColor: p.surfaceAlt, marginTop: 4, overflow: 'hidden' }}>
                  <View style={{ height: '100%', width: `${Math.round((100 * g.gross) / gmax)}%`, backgroundColor: p.teal, borderRadius: 4 }} />
                </View>
                <T v="small" color={p.faint} style={{ marginTop: 2 }}>{g.n} payments · net {inr(g.net)} · fees {inr(g.fees)}</T>
              </View>
            ))}
            <Row style={{ justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: p.border, paddingTop: space[2] }}>
              <T v="body" color={p.muted}>Net · MRR</T><T v="body">{inr(b.net)} · {inr(b.mrr)}</T>
            </Row>
          </Card>
        </Section>
      ) : null}
      <View style={{ height: space[6] }} />
    </Screen>
  );
}
