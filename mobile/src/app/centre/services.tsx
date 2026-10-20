import React from 'react';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { usePalette } from '@/lib/theme';
import { Card, Chip, ErrorState, Loading, Row, Screen, T } from '@/ui/core';

export default function Services() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<any[]>(`/mgmt/catalog?org=${encodeURIComponent(staffOrg())}&kind=service_type`);
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Services</T>
      <T v="small">Your centre's service catalogue.</T>
      {!data ? <Loading what="Loading…" /> : null}
      {data && !data.length ? <T v="small">No services yet.</T> : null}
      {data?.map((s) => {
        const d = s.data ?? {};
        return (
          <Card key={s.id}>
            <Row><T v="h3" style={{ flex: 1 }}>{s.name}</T>{d.category ? <Chip label={d.category} fg={p.teal} bg={p.tealSoft} /> : null}</Row>
            <T v="small">{[d.minutes != null ? `${d.minutes} min` : null, d.price != null ? `₹${Number(d.price).toLocaleString('en-IN')}` : null].filter(Boolean).join(' · ') || '—'}</T>
            {d.desc ? <T v="body">{d.desc}</T> : null}
          </Card>
        );
      })}
    </Screen>
  );
}
