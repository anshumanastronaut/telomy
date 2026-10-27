// Centre doctors — the clinicians affiliated with this centre. Each shows their role and contact; the floor's
// bookings and the members' care route to them. (Full onboarding/payouts live on the web console.)
import React from 'react';
import { Linking, View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { BackButton, Card, Chip, ErrorState, Loading, Row, Screen, T } from '@/ui/core';

type Doctor = { id: number; name: string; role: string; label?: string; email?: string; delivers?: boolean; active?: number };

export default function CentreDoctors() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<Doctor[]>(`/mgmt/centre/doctors?org=${encodeURIComponent(staffOrg())}`);
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen><Loading what="Loading doctors…" /></Screen>;

  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <BackButton fallback="/centre" />
      <T v="h1">Doctors</T>
      <T v="small" color={p.muted}>{data.length} clinician{data.length === 1 ? '' : 's'} at this centre</T>
      <View style={{ gap: space[2], marginTop: space[2] }}>
        {data.map((d) => (
          <Card key={d.id}>
            <Row>
              <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: p.tealSoft, alignItems: 'center', justifyContent: 'center' }}>
                <T v="h3" color={p.teal}>{d.name?.replace(/^Dr\.?\s*/, '')?.[0] ?? 'D'}</T>
              </View>
              <View style={{ flex: 1 }}>
                <T v="h3" numberOfLines={1}>{d.name}</T>
                {d.email ? <T v="small" color={p.teal} numberOfLines={1} onPress={() => Linking.openURL(`mailto:${d.email}`)}>{d.email}</T> : null}
              </View>
              <Chip label={d.label ?? d.role} fg={p.teal} bg={p.tealSoft} />
            </Row>
          </Card>
        ))}
        {!data.length ? <Card><T v="small" color={p.muted}>No doctors affiliated yet. Add them from the web console.</T></Card> : null}
      </View>
      <View style={{ height: space[6] }} />
    </Screen>
  );
}
