import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space } from '@/lib/theme';
import { Card, ErrorState, Loading, Row, Screen, T } from '@/ui/core';

export default function Floor() {
  const { data, error, reload, loading } = useApi<any[]>(`/mgmt/catalog?org=${encodeURIComponent(staffOrg())}&kind=resource`);
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Machines & rooms</T>
      <T v="small">{data?.length ?? 0} machines and rooms.</T>
      {!data ? <Loading what="Loading…" /> : null}
      {data && !data.length ? <T v="small">No machines or rooms yet.</T> : null}
      <View style={{ gap: space[3] }}>
        {data?.map((r) => (
          <Card key={r.id}><Row><T v="body" style={{ flex: 1 }}>{r.name}</T></Row></Card>
        ))}
      </View>
    </Screen>
  );
}
