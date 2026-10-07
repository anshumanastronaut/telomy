import { router } from 'expo-router';
import React, { useEffect } from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Sparkline } from '@/ui/charts';
import { Button, Card, Chip, Empty, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';
import { phaseName } from '@/ui/therapy';

export default function Floor() {
  const p = usePalette();
  const { data: d, error, reload, loading } = useApi<any>('/centre/floor');
  useEffect(() => {
    const h = setInterval(reload, 15000); // refresh vitals every 15 s
    return () => clearInterval(h);
  }, [reload]);
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen><Loading what="Opening the therapy floor…" /></Screen>;
  const rooms = Array.from(new Set(d.devices.map((x: any) => x.room))) as string[];
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Therapy floor</T>
      <T v="small">Live at {d.now.slice(11, 16)} · {d.live.length} in session · updates every 15 s</T>
      {d.alerts.length ? (
        <Card tone="copper">
          <T v="h3">Needs a staff check</T>
          {d.alerts.map((a: any) => <T key={a.booking_id} v="body">⚠︎ {a.name} · {a.therapy}: {a.safety.reasons.join('; ')}</T>)}
        </Card>
      ) : null}
      <Section title="In session now">
        {d.live.length ? d.live.map((s: any) => (
          <Card key={s.booking_id} onPress={() => router.push(`/patient/${s.patient_id}`)}>
            <Row>
              <View style={{ flex: 1 }}>
                <T v="h3">{s.name}</T>
                <T v="small">{s.therapy} · {s.device?.name ?? ''}</T>
              </View>
              <Chip label={phaseName(s.phase)} fg={s.phase === 'recovery' ? p.teal : p.copper} bg={s.phase === 'recovery' ? p.tealSoft : p.copperSoft} />
            </Row>
            <Row>
              {[['hr', 'HR', 'bpm'], ['rmssd', 'HRV', 'ms'], ['skin', 'Skin', '°C'], ['spo2', 'SpO₂', '%']].map(([k, l, u]) => (
                <View key={k} style={{ flex: 1, gap: 2 }}>
                  <T v="small">{l}</T>
                  <T v="num" style={{ fontSize: 16 }}>{Math.round(s.now[k] * (k === 'skin' ? 10 : 1)) / (k === 'skin' ? 10 : 1)} <T v="small">{u}</T></T>
                  <Sparkline data={s.spark[k]} width={70} height={22} color={k === 'skin' ? p.copper : p.teal} />
                </View>
              ))}
            </Row>
            <Row>
              <View style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: p.surfaceAlt }}>
                <View style={{ width: `${Math.min(100, (100 * s.elapsed_s) / s.total_s)}%`, height: 4, borderRadius: 2, backgroundColor: p.teal }} />
              </View>
              <T v="small">{Math.floor(s.elapsed_s / 60)}/{Math.round(s.total_s / 60)} min</T>
            </Row>
            <T v="small" color={s.safety.tier ? p.danger : p.muted}>Safety: {s.safety.label} · {s.source}</T>
          </Card>
        )) : <Empty title="Nobody in a session right now" body="Sessions appear here five minutes before the booked slot." />}
      </Section>
      {d.next.length ? (
        <Section title="Up next">
          <Card style={{ paddingVertical: 4 }}>
            {d.next.map((n: any, i: number) => (
              <Row key={n.booking_id} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <T v="body" numberOfLines={1} style={{ flexShrink: 0, maxWidth: '45%' }}>{n.name}</T>
                <T v="small" style={{ flex: 1, textAlign: 'right' }}>{n.therapy} · {n.ts.slice(11, 16)}</T>
              </Row>
            ))}
          </Card>
        </Section>
      ) : null}
      <Section title={`Machines · ${d.devices.length}`}>
        {rooms.map((room) => (
          <Card key={room} style={{ paddingVertical: 4 }}>
            <T v="label" style={{ paddingTop: 8 }}>{room}</T>
            {d.devices.filter((x: any) => x.room === room).map((x: any) => (
              <Row key={x.id} style={{ paddingVertical: 6 }}>
                <T v="body" style={{ flex: 1 }}>{x.name}</T>
                <Chip label={x.status !== 'available' ? x.status.replace(/_/g, ' ') : x.in_use ? 'In use' : 'Free'}
                  fg={x.status === 'maintenance' ? p.warn : x.status !== 'available' ? p.muted : x.in_use ? p.copper : p.success}
                  bg={x.status === 'maintenance' ? p.warnSoft : x.status !== 'available' ? p.surfaceAlt : x.in_use ? p.copperSoft : p.successSoft} />
              </Row>
            ))}
            <T v="small" style={{ paddingBottom: 8 }}>Next service: {d.devices.filter((x: any) => x.room === room).map((x: any) => `${x.id} ${x.next_service}`).join(' · ')}</T>
          </Card>
        ))}
      </Section>
      <Button kind="secondary" title="Therapy outcomes & research" icon="chart.xyaxis.line" onPress={() => router.push('/centre-research')} />
      <View style={{ height: space[2] }} />
    </Screen>
  );
}
