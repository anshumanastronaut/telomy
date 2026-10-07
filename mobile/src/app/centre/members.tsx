import React from 'react';
import { View } from 'react-native';

import { fmtDate, useApi } from '@/lib/api';
import { space } from '@/lib/theme';
import { ErrorState, Loading, Screen, T } from '@/ui/core';
import { PatientRow } from '@/ui/patient';

export default function Members() {
  const { data, error, reload, loading } = useApi<any[]>('/centre/members');
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Members</T>
      <T v="small">{data?.length ?? 0} members, ranked by health priority.</T>
      {!data ? <Loading what="Loading members…" /> : null}
      <View style={{ gap: space[3] }}>
        {data?.map((m) => (
          <View key={m.id} style={{ gap: 4 }}>
            <PatientRow p={m} />
            <T v="small" style={{ paddingLeft: 4 }}>{m.visits_30d} visits in 30 days · last visit {m.last_visit ? fmtDate(m.last_visit) : '—'}</T>
          </View>
        ))}
      </View>
    </Screen>
  );
}
