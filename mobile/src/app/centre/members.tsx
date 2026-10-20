import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space } from '@/lib/theme';
import { Card, ErrorState, Loading, Row, Screen, T } from '@/ui/core';

export default function Members() {
  const { data, error, reload, loading } = useApi<any[]>(`/mgmt/centre/people?org=${encodeURIComponent(staffOrg())}`);
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Members</T>
      <T v="small">{data?.length ?? 0} members.</T>
      {!data ? <Loading what="Loading members…" /> : null}
      {data && !data.length ? <T v="small">No members yet.</T> : null}
      <View style={{ gap: space[3] }}>
        {data?.map((m) => (
          <Card key={m.id}>
            <Row>
              <View style={{ flex: 1 }}>
                <T v="h3">{m.name}</T>
                <T v="small">{[m.age != null ? `${m.age}` : null, m.sex, m.city].filter(Boolean).join(' · ') || '—'}</T>
              </View>
              <T v="small">{m.doctor || 'unassigned'}</T>
            </Row>
          </Card>
        ))}
      </View>
    </Screen>
  );
}
