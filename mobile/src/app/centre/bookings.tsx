import React, { useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

const STATUS: Record<string, [string, string]> = { booked: ['Booked', 'info'], checked_in: ['Checked in', 'awaiting'], completed: ['Done', 'optimal'], no_show: ['No-show', 'out_of_range'], cancelled: ['Cancelled', 'none'] };

function day(off: number) {
  const d = new Date('2026-10-06T12:00:00');
  d.setDate(d.getDate() + off);
  return d.toISOString().slice(0, 10);
}

export default function Bookings() {
  const p = usePalette();
  const [off, setOff] = useState(0);
  const list = useApi<any[]>(`/centre/bookings?day=${day(off)}`, [off]);
  const members = useApi<any[]>('/centre/members');
  const services = useApi<any[]>('/centre/services');
  const [m, setM] = useState<number | null>(null);
  const [s, setS] = useState<string | null>(null);
  const [hour, setHour] = useState(10);
  const { toast, show } = useToast();
  async function setStatus(id: number, status: string) {
    await api(`/centre/bookings/${id}/status`, { body: { status } });
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
                  <T v="body" style={{ width: 50, fontWeight: '600' }}>{b.ts.slice(11, 16)}</T>
                  <View style={{ flex: 1 }}><T v="body">{b.service}</T><T v="small">{b.name} · {b.minutes} min · ₹{b.price}</T></View>
                  <Chip label={STATUS[b.status]?.[0] ?? b.status} />
                </Row>
                {b.status === 'booked' ? (
                  <Row><Button style={{ flex: 1 }} kind="secondary" title="Check in" onPress={() => setStatus(b.id, 'checked_in')} /><Button kind="ghost" title="No-show" onPress={() => setStatus(b.id, 'no_show')} /></Row>
                ) : b.status === 'checked_in' ? <Button kind="secondary" title="Mark done" onPress={() => setStatus(b.id, 'completed')} /> : null}
              </View>
            </View>
          )) : <T v="small" style={{ paddingVertical: 10 }}>No bookings this day.</T>}
        </Card>
        <Section title="New booking">
          <Card>
            <T v="label">Member</T>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
              {members.data?.map((x) => <Pressable key={x.id} onPress={() => setM(x.id)}><Chip label={x.name} fg={m === x.id ? '#fff' : p.text} bg={m === x.id ? p.teal : p.surfaceAlt} /></Pressable>)}
            </ScrollView>
            <T v="label">Service</T>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {services.data?.map((x) => <Pressable key={x.id} onPress={() => setS(x.id)}><Chip label={x.name} fg={s === x.id ? '#fff' : p.text} bg={s === x.id ? p.teal : p.surfaceAlt} /></Pressable>)}
            </View>
            <T v="label">Time · {day(off)}</T>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {[7, 8, 9, 10, 11, 16, 17, 18, 19].map((h) => <Pressable key={h} onPress={() => setHour(h)}><Chip label={`${h}:00`} fg={hour === h ? '#fff' : p.text} bg={hour === h ? p.teal : p.surfaceAlt} /></Pressable>)}
            </View>
            <Button title="Book" disabled={!m || !s} onPress={async () => {
              try {
                const r = await api('/centre/bookings', { body: { patient_id: m, service_id: s, ts: `${day(off)}T${String(hour).padStart(2, '0')}:00:00` } });
                show(r.message, 'success'); list.reload();
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
