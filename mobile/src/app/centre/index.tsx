import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg, staffSync } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { Card, Chip, Divider, ErrorState, Icon, ListRow, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';
import { TelomyLoader } from '@/ui/loader';
import { Logo } from '@/ui/logo';

const inr = (v: number) => `₹${Math.round(v || 0).toLocaleString('en-IN')}`;
const org = () => encodeURIComponent(staffOrg());
const SVC: Record<string, string> = { redlight: 'Red-light', hbot: 'HBOT', hbot_mild: 'HBOT', blood: 'Blood draw', cryo: 'Cryotherapy', cold: 'Cold plunge', sauna: 'Infrared sauna', iv: 'IV drip', coach: 'Coaching', consult: 'Consult', dexa: 'DEXA', vo2: 'VO₂max', pemf: 'PEMF' };
const svc = (s: string, name?: string) => name || SVC[s] || (s ? s.replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : '—');

function statusTone(p: any, s: string) {
  s = (s || '').toLowerCase();
  if (s === 'completed') return { fg: p.teal, bg: p.tealSoft };
  if (s === 'checked_in') return { fg: p.copper, bg: p.copperSoft };
  if (s === 'no_show' || s === 'cancelled') return { fg: p.danger, bg: p.dangerSoft };
  return { fg: p.muted, bg: p.surfaceAlt };
}

export default function CentreDashboard() {
  const p = usePalette();
  const { data: d, error, reload, loading } = useApi<any>(`/mgmt/centre/dashboard?org=${org()}`);
  const rev = useApi<any>(`/mgmt/centre/revenue?org=${org()}`);
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen><Loading what="Loading your centre…" /></Screen>;
  const schedule: any[] = d.schedule ?? [];
  return (
    <Screen onRefresh={() => { reload(); rev.reload(); }} refreshing={loading}>
      <Row gap={12}>
        <TelomyLoader size="mark" />
        <View style={{ flex: 1 }}>
          <T v="label" numberOfLines={1}>{(staffSync()?.org ?? 'Centre').replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</T>
          <T v="h1">Today</T>
        </View>
      </Row>

      <Card>
        <Row>
          <Stat label="Members" value={d.active_members} />
          <Stat label="Booked today" value={d.today_bookings} />
          <Stat label="Checked in" value={d.checked_in} />
        </Row>
        <Divider />
        <Row>
          <Stat label="Revenue today" value={inr(d.revenue_today)} />
          <Stat label="Total" value={rev.data ? inr(rev.data.total_revenue) : '—'} />
          <Stat label="Outstanding" value={inr(d.outstanding)} />
        </Row>
      </Card>

      <Card tone="teal" onPress={() => router.push('/centre/copilot' as any)} accessibilityLabel="Ask Sinc">
        <Row style={{ alignItems: 'center' }} gap={space[3]}>
          <View style={{ width: 46, height: 28, alignItems: 'center', justifyContent: 'center' }}><TelomyLoader size="mark" /></View>
          <View style={{ flex: 1 }}>
            <T v="h3">Ask Sinc</T>
            <T v="small">Members, schedule, floor & revenue — ask in plain words, grounded in your data.</T>
          </View>
          <Icon name="chevron.right" size={13} color={p.faint} />
        </Row>
      </Card>

      <Section title={`Today's schedule · ${schedule.length}`} action="All bookings" onAction={() => router.push('/centre/bookings' as any)}>
        <View style={{ gap: space[2] }}>
          {schedule.length ? schedule.slice(0, 8).map((b: any) => {
            const t = statusTone(p, b.status);
            return (
              <Card key={b.id} onPress={() => router.push('/centre/bookings' as any)}>
                <Row>
                  <T v="body" style={{ width: 52, fontWeight: '600' }}>{b.start_ts?.slice(11, 16)}</T>
                  <View style={{ flex: 1 }}>
                    <T v="body" numberOfLines={1}>{svc(b.service_id, b.service_name)}</T>
                    <T v="small" color={p.faint}>{b.member_name ?? `Member #${b.member_id}`}{b.price ? ` · ₹${b.price}` : ''}</T>
                  </View>
                  <Chip label={(b.status || 'booked').replace(/_/g, ' ')} fg={t.fg} bg={t.bg} />
                </Row>
              </Card>
            );
          }) : <Card><T v="small" color={p.muted}>No bookings today.</T></Card>}
        </View>
      </Section>

      <Section title="Manage">
        <Card style={{ paddingVertical: 2 }}>
          <ListRow icon="stethoscope" title="Doctors" subtitle="Clinicians at this centre" onPress={() => router.push('/centre/doctors' as any)} />
          <Divider />
          <ListRow icon="chart.line.uptrend.xyaxis" title="Revenue & payments" subtitle={rev.data ? `${inr(rev.data.invoiced_paid)} invoiced · ${inr(rev.data.outstanding)} due` : 'Invoices, gateways, payouts'} onPress={() => router.push('/centre/revenue' as any)} />
          <Divider />
          <ListRow icon="person.3" title="Team performance" subtitle="Bookings, delivery and revenue by staff" onPress={() => router.push('/centre/performance' as any)} />
          <Divider />
          <ListRow icon="waveform.path.ecg.rectangle" title="Floor" subtitle="Machines & rooms, live status" onPress={() => router.push('/centre/floor' as any)} />
        </Card>
      </Section>
      <View style={{ height: space[6] }} />
    </Screen>
  );
}
