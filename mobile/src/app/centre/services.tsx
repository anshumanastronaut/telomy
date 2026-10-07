import React, { useState } from 'react';
import { View } from 'react-native';

import { api } from '@/lib/api';
import { useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, T } from '@/ui/core';

export default function Services() {
  const p = usePalette();
  const { data } = useApi<any[]>('/centre/services');
  const [out, setOut] = useState<Record<string, any>>({});
  return (
    <Screen>
      <T v="h1">Services</T>
      <T v="small">Price, capacity, evidence grade — and what each service does for members who share wearable data.</T>
      {!data ? <Loading what="Loading…" /> : null}
      {data?.map((s) => (
        <Card key={s.id}>
          <Row><T v="h3" style={{ flex: 1 }}>{s.name}</T><Chip label={`Evidence ${s.evidence}`} fg={p.teal} bg={p.tealSoft} /></Row>
          <T v="small">{s.category} · {s.minutes} min · ₹{s.price.toLocaleString('en-IN')} · {s.capacity} at a time</T>
          {out[s.id] ? (
            <View style={{ gap: 2 }}>
              {out[s.id].hrv_after != null ? (
                <T v="body">Next-night HRV {out[s.id].hrv_after} ms vs {out[s.id].hrv_other} ms on other nights (n = {out[s.id].n}, d = {out[s.id].d}).</T>
              ) : <T v="small">{out[s.id].message}</T>}
              <T v="small">{out[s.id].message}</T>
            </View>
          ) : <Button kind="ghost" title="See member outcomes" onPress={async () => setOut({ ...out, [s.id]: await api(`/centre/services/${s.id}/outcomes`) })} />}
        </Card>
      ))}
    </Screen>
  );
}
