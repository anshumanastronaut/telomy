// Centre team performance — per staff: booked vs delivered (utilisation), revenue and no-shows.
import { Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { BackButton, Card, ErrorState, Loading, Row, Screen, T } from '@/ui/core';

const inr = (v: number) => `₹${Math.round(v || 0).toLocaleString('en-IN')}`;

export default function CentrePerformance() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<any[]>(`/mgmt/centre/performance?org=${encodeURIComponent(staffOrg())}`);
  if (error) return <Screen edges={['top']}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={['top']}><Loading what="Loading performance…" /></Screen>;

  return (
    <Screen edges={['top']} onRefresh={reload} refreshing={loading}>
      <BackButton fallback="/centre" />
      <Stack.Screen options={{ title: 'Team performance' }} />
      <T v="h1">Team performance</T>
      <View style={{ gap: space[2], marginTop: space[2] }}>
        {data.map((s: any) => {
          const util = Math.round((100 * (s.delivered || 0)) / Math.max(1, s.booked || 0));
          return (
            <Card key={s.staff_id}>
              <Row style={{ justifyContent: 'space-between' }}>
                <View style={{ flex: 1 }}>
                  <T v="h3">{s.name}</T>
                  <T v="small" color={p.faint}>{s.label ?? s.role}</T>
                </View>
                <T v="h3">{inr(s.revenue)}</T>
              </Row>
              <View style={{ height: 7, borderRadius: 4, backgroundColor: p.surfaceAlt, marginTop: space[2], overflow: 'hidden' }}>
                <View style={{ height: '100%', width: `${util}%`, backgroundColor: p.teal, borderRadius: 4 }} />
              </View>
              <Row style={{ justifyContent: 'space-between', marginTop: 4 }}>
                <T v="small" color={p.muted}>{s.delivered}/{s.booked} delivered · {util}%</T>
                {s.no_show ? <T v="small" color={p.copper}>{s.no_show} no-show</T> : null}
              </Row>
            </Card>
          );
        })}
      </View>
      <View style={{ height: space[6] }} />
    </Screen>
  );
}
