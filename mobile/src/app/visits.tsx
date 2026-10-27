// Your visits — plain-language recaps your clinician's consult scribe generated, newest first.
import { Stack } from 'expo-router';
import React from 'react';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, ErrorState, Loading, Row, Screen, T } from '@/ui/core';

export default function Visits() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<any[]>('/me/consults');
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Loading what="Loading your visits…" /></Screen>;
  return (
    <Screen edges={[]} onRefresh={reload} refreshing={loading}>
      <Stack.Screen options={{ title: '' }} />
      <T v="h1">Your visits</T>
      <T v="small" color={p.muted}>A plain-language recap of each clinic visit — what was discussed and what to do next. Anything your doctor ordered also appears in the relevant part of your app.</T>
      {data.length ? data.map((c) => (
        <Card key={c.id} style={{ gap: space[1] }}>
          <Row><T v="label" style={{ flex: 1 }}>{c.doctor ?? 'Your clinician'}</T><T v="small" color={p.faint}>{(c.ts ?? '').slice(0, 10)}</T></Row>
          <T v="body">{c.recap}</T>
        </Card>
      )) : <Card><T v="small" color={p.muted}>No visit recaps yet. After a clinic visit, your doctor's summary appears here.</T></Card>}
    </Screen>
  );
}
