import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffSync, staffOrg } from '@/lib/staff';
import { Card, ErrorState, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

const inr = (v: number) => `₹${Math.round(v || 0).toLocaleString('en-IN')}`;
const org = () => encodeURIComponent(staffOrg());

export default function CentreDashboard() {
  const { data: d, error, reload, loading } = useApi<any>(`/mgmt/centre/dashboard?org=${org()}`);
  const rev = useApi<any>(`/mgmt/centre/revenue?org=${org()}`);
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen><Loading what="Loading your centre…" /></Screen>;
  const schedule: any[] = d.schedule ?? [];
  return (
    <Screen onRefresh={() => { reload(); rev.reload(); }} refreshing={loading}>
      <Row gap={12}>
        <Logo kind="mark" width={34} />
        <View style={{ flex: 1 }}>
          <T v="label" numberOfLines={1}>{staffSync()?.label ? staffSync()?.org : 'Centre'}</T>
          <T v="h1">Dashboard</T>
        </View>
      </Row>
      <Card>
        <Row>
          <Stat label="Members" value={d.active_members} />
          <Stat label="Today" value={d.today_bookings} />
          <Stat label="Checked in" value={d.checked_in} />
        </Row>
        <Row>
          <Stat label="Revenue today" value={inr(d.revenue_today)} />
          <Stat label="Total revenue" value={rev.data ? inr(rev.data.total_revenue) : '—'} />
          <Stat label="Outstanding" value={inr(d.outstanding)} />
        </Row>
      </Card>
      <Section title={`Today · ${schedule.length} bookings`} action="Bookings" onAction={() => router.push('/centre/bookings')}>
        <Card>
          {schedule.length ? schedule.map((b: any) => (
            <Row key={b.id}>
              <T v="small" style={{ width: 48 }}>{b.start_ts?.slice(11, 16)}</T>
              <T v="body" style={{ flex: 1 }} numberOfLines={1}>{b.service_name}</T>
              <T v="small">{b.status}</T>
            </Row>
          )) : <T v="small">No bookings today.</T>}
        </Card>
      </Section>
    </Screen>
  );
}
