// Centre floor — every machine and room, grouped by room, with a live status (in use · available · servicing ·
// offline), what's running on it now, how loaded it is today and when it's next serviced. Tap a unit to expand.
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { Card, Chip, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';

type Machine = {
  id: string; name: string; modality: string; room: string; capacity: number;
  status: 'in_use' | 'available' | 'servicing' | 'offline';
  busy_with?: { member: string; until: string } | null; today_sessions: number;
  next?: { at: string; member: string } | null; next_service?: string; last_service?: string;
};

export default function Floor() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<Machine[]>(`/mgmt/centre/floor?org=${encodeURIComponent(staffOrg())}`);
  const [open, setOpen] = React.useState<Record<string, boolean>>({});
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen><Loading what="Reading the floor…" /></Screen>;

  const tone = (s: Machine['status']) =>
    s === 'in_use' ? { fg: p.copper, bg: p.copperSoft, label: 'In use' }
      : s === 'servicing' ? { fg: p.warn, bg: p.warnSoft, label: 'Servicing' }
        : s === 'offline' ? { fg: p.danger, bg: p.dangerSoft, label: 'Offline' }
          : { fg: p.teal, bg: p.tealSoft, label: 'Available' };

  const rooms = Array.from(new Set(data.map((m) => m.room || 'Floor')));
  const inUse = data.filter((m) => m.status === 'in_use').length;
  const down = data.filter((m) => m.status === 'servicing' || m.status === 'offline').length;

  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Floor</T>
      <T v="small" color={p.muted}>{data.length} units · {inUse} in use · {data.length - inUse - down} free{down ? ` · ${down} down` : ''}</T>

      {rooms.map((room) => (
        <Section key={room} title={room}>
          <View style={{ gap: space[2] }}>
            {data.filter((m) => (m.room || 'Floor') === room).map((m) => {
              const t = tone(m.status);
              const isOpen = !!open[m.id];
              return (
                <Card key={m.id} onPress={() => setOpen((s) => ({ ...s, [m.id]: !s[m.id] }))}>
                  <Row style={{ alignItems: 'flex-start' }}>
                    <View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: t.fg, marginTop: 6 }} />
                    <View style={{ flex: 1 }}>
                      <T v="h3" numberOfLines={isOpen ? undefined : 1}>{m.name}</T>
                      {m.status === 'in_use' && m.busy_with
                        ? <T v="small" color={p.copper}>{m.busy_with.member} · until {m.busy_with.until}</T>
                        : <T v="small" color={p.faint}>{m.today_sessions} session{m.today_sessions === 1 ? '' : 's'} today{m.next ? ` · next ${m.next.at}` : ''}</T>}
                    </View>
                    <Chip label={t.label} fg={t.fg} bg={t.bg} />
                  </Row>
                  {isOpen ? (
                    <View style={{ marginTop: 10, gap: 4 }}>
                      <Row style={{ justifyContent: 'space-between' }}><T v="small" color={p.muted}>Modality</T><T v="small">{m.modality}</T></Row>
                      <Row style={{ justifyContent: 'space-between' }}><T v="small" color={p.muted}>Capacity</T><T v="small">{m.capacity || 1}</T></Row>
                      <Row style={{ justifyContent: 'space-between' }}><T v="small" color={p.muted}>Today</T><T v="small">{m.today_sessions} booked</T></Row>
                      {m.next ? <Row style={{ justifyContent: 'space-between' }}><T v="small" color={p.muted}>Next</T><T v="small">{m.next.at} · {m.next.member}</T></Row> : null}
                      {m.last_service ? <Row style={{ justifyContent: 'space-between' }}><T v="small" color={p.muted}>Last service</T><T v="small">{m.last_service}</T></Row> : null}
                      {m.next_service ? <Row style={{ justifyContent: 'space-between' }}><T v="small" color={p.muted}>Next service</T><T v="small">{m.next_service}</T></Row> : null}
                    </View>
                  ) : null}
                </Card>
              );
            })}
          </View>
        </Section>
      ))}
      <View style={{ height: space[6] }} />
    </Screen>
  );
}
