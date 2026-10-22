import React, { useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

const STATUS: Record<string, string> = { booked: 'Booked', checked_in: 'Checked in', completed: 'Done', no_show: 'No-show', cancelled: 'Cancelled' };

function day(off: number) {
  const d = new Date();
  d.setDate(d.getDate() + off);
  return d.toISOString().slice(0, 10);
}

export default function Bookings() {
  const p = usePalette();
  const org = encodeURIComponent(staffOrg());
  const [off, setOff] = useState(0);
  const list = useApi<any[]>(`/mgmt/centre/schedule?org=${org}&day=${day(off)}`, [off]);
  const members = useApi<any[]>(`/mgmt/centre/people?org=${org}`);
  const services = useApi<any[]>(`/mgmt/catalog?org=${org}&kind=service_type`);
  const [m, setM] = useState<any>(null);
  const [s, setS] = useState<any>(null);
  const [hour, setHour] = useState(10);
  const { toast, show } = useToast();
  async function checkIn(id: any) {
    await api(`/mgmt/centre/bookings/${id}/checkin`, { method: 'POST' });
    list.reload();
  }
  async function setStatus(id: any, status: string) {
    await api(`/mgmt/centre/bookings/${id}/status`, { body: { status } });
    list.reload();
  }
  return (
    <View style={{ flex: 1 }}>
      <Screen onRefresh={list.reload} refreshing={list.loading}>
        <T v="h1">Bookings</T>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
          {[-1, 0, 1, 2, 3, 4, 5].map((o) => {
            const d = new Date(day(o) + 'T12:00:00');
            return (
              <Pressable key={o} onPress={() => setOff(o)} style={{ width: 56, alignItems: 'center', paddingVertical: 8, borderRadius: radius.lg, borderWidth: 1, borderColor: off === o ? p.teal : p.border, backgroundColor: off === o ? p.tealSoft : p.surface }}>
                <T v="label" color={off === o ? p.teal : p.muted}>{d.toLocaleDateString('en-GB', { weekday: 'short' })}</T>
                <T v="h3" color={off === o ? p.teal : p.text}>{d.getDate()}</T>
              </Pressable>
            );
          })}
        </ScrollView>
        {!list.data ? <Loading what="Loading…" /> : null}
        <Card style={{ paddingVertical: 4 }}>
          {list.data?.length ? list.data.map((b, i) => (
            <View key={b.id}>
              {i ? <Divider /> : null}
              <View style={{ paddingVertical: 10, gap: 6 }}>
                <Row>
                  <T v="body" style={{ width: 50, fontWeight: '600' }}>{b.start_ts?.slice(11, 16)}</T>
                  <View style={{ flex: 1 }}><T v="body">{b.service_name}</T><T v="small">{b.minutes} min · ₹{b.price}</T></View>
                  <Chip label={STATUS[b.status] ?? b.status} />
                </Row>
                {b.status === 'booked' ? (
                  <Row><Button style={{ flex: 1 }} kind="secondary" title="Check in" onPress={() => checkIn(b.id)} /><Button kind="ghost" title="No-show" onPress={() => setStatus(b.id, 'no_show')} /></Row>
                ) : b.status === 'checked_in' ? <Button kind="secondary" title="Mark done" onPress={() => setStatus(b.id, 'completed')} /> : null}
              </View>
            </View>
          )) : <T v="small" style={{ paddingVertical: 10 }}>No bookings this day.</T>}
        </Card>
        <Section title="New booking">
          <Card>
            <T v="label">Member</T>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
              {members.data?.map((x) => <Pressable key={x.id} onPress={() => setM(x.id)}><Chip label={x.name} fg={m === x.id ? p.onAccent : p.text} bg={m === x.id ? p.teal : p.surfaceAlt} /></Pressable>)}
            </ScrollView>
            <T v="label">Service</T>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {services.data?.map((x) => <Pressable key={x.id} onPress={() => setS(x.id)}><Chip label={x.name} fg={s === x.id ? p.onAccent : p.text} bg={s === x.id ? p.teal : p.surfaceAlt} /></Pressable>)}
            </View>
            <T v="label">Time · {day(off)}</T>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {[7, 8, 9, 10, 11, 16, 17, 18, 19].map((h) => <Pressable key={h} onPress={() => setHour(h)}><Chip label={`${h}:00`} fg={hour === h ? p.onAccent : p.text} bg={hour === h ? p.teal : p.surfaceAlt} /></Pressable>)}
            </View>
            <Button title="Book" disabled={!m || !s} onPress={async () => {
              try {
                await api('/mgmt/centre/book', { body: { org: staffOrg(), member_id: m, service_id: s, start_ts: `${day(off)}T${String(hour).padStart(2, '0')}:00:00` } });
                show('Booked.', 'success'); list.reload();
              } catch (e: any) { show(e.message, 'alert'); }
            }} />
          </Card>
        </Section>
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
