// Retest plan — the closed loop: what to re-measure now, what improved/worsened since your last draw, and when each
// marker is next due. Cadence is a suggestion, not a medical order. Backend: /retest (app/retest.py).
import { router, Stack } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Card, Empty, Icon, Loading, Row, Screen, Section, T } from '@/ui/core';

type Due = { id: string; name: string; unit: string; last_tested: string; days_old: number; overdue_days: number; interval_days: number; next_due: string; status: string; prep?: string | null };
type Change = { id: string; name: string; unit: string; from: number; to: number; delta: number; improved: boolean; from_day?: string };
type Sched = { id: string; name: string; next_due: string; last_tested: string; status: string };
type Plan = { due: Due[]; improving: Change[]; worsening: Change[]; schedule: Sched[]; counts: { due: number; improving: number; worsening: number }; note: string };

export default function Retest() {
  const p = usePalette();
  const r = useApi<Plan>('/retest');
  if (!r.data) return <Screen><Stack.Screen options={{ title: 'Retest plan' }} /><Loading what="Working out your retest plan…" /></Screen>;
  const d = r.data;
  const empty = !d.schedule.length && !d.improving.length && !d.worsening.length;

  const changeRow = (c: Change) => (
    <Row key={c.id} style={{ alignItems: 'center' }}>
      <Icon name={c.improved ? 'arrow.down.right.circle.fill' : 'arrow.up.right.circle.fill'} size={16} color={c.improved ? '#2F8F6B' : '#D3523F'} />
      <Pressable style={{ flex: 1, marginLeft: 8 }} onPress={() => router.push(`/marker/${c.id}` as any)}>
        <T v="body">{c.name}</T>
      </Pressable>
      <T v="small" color={p.muted}>{c.from} → </T>
      <T v="num" style={{ fontSize: 15, color: c.improved ? '#2F8F6B' : '#D3523F' }}>{c.to}</T>
      <T v="small" color={c.improved ? '#2F8F6B' : '#D3523F'}> ({c.delta > 0 ? '+' : ''}{c.delta})</T>
    </Row>
  );

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Retest plan' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Retest plan</T>
        <T v="small" color={p.muted}>Measure → act → re-measure. Cadence is sooner for out-of-range markers — act on those with your clinician, then re-measure to see what worked.</T>
      </View>

      {empty ? (
        <Empty title="Add a couple of reports" body="Once you have lab history, this shows what to retest, what changed, and when each marker is next due."
          actions={[{ title: 'Add a report', onPress: () => router.push('/upload') }]} />
      ) : (
        <>
          {d.due.length ? (
            <Section title={`Due to retest (${d.due.length})`}>
              {d.due.map((x) => (
                <Card key={x.id} onPress={() => router.push(`/marker/${x.id}` as any)} style={{ gap: space[1], marginBottom: space[2] }}>
                  <Row style={{ alignItems: 'center' }}>
                    <T v="h3" style={{ flex: 1 }}>{x.name}</T>
                    <View style={{ backgroundColor: '#C98A1B22', borderRadius: radius.sm, paddingVertical: 2, paddingHorizontal: 8 }}>
                      <T v="small" color="#C98A1B">{x.overdue_days === 0 ? 'due now' : `${x.overdue_days}d overdue`}</T>
                    </View>
                  </Row>
                  <T v="small" color={p.muted}>Last tested {fmtDate(x.last_tested, true)} · suggested every {Math.round(x.interval_days / 30)} mo</T>
                  {x.prep ? <T v="small" color={p.faint}>Before testing: {x.prep}</T> : null}
                </Card>
              ))}
            </Section>
          ) : (
            <Card tone="teal"><Row gap={8} style={{ alignItems: 'center' }}><Icon name="checkmark.circle.fill" size={18} color={p.teal} /><T v="body" style={{ flex: 1 }}>Nothing due to retest right now.</T></Row></Card>
          )}

          {d.improving.length ? (
            <Section title={`Improving since last time (${d.improving.length})`}>
              <Card style={{ gap: space[2] }}>{d.improving.map(changeRow)}</Card>
            </Section>
          ) : null}

          {d.worsening.length ? (
            <Section title={`Moved the wrong way (${d.worsening.length})`}>
              <Card style={{ gap: space[2] }}>{d.worsening.map(changeRow)}</Card>
            </Section>
          ) : null}

          {d.schedule.length ? (
            <Section title="Upcoming schedule">
              <Card style={{ gap: space[2] }}>
                {d.schedule.slice(0, 12).map((s) => (
                  <Row key={s.id} style={{ alignItems: 'center' }}>
                    <T v="body" style={{ flex: 1 }}>{s.name}</T>
                    <T v="small" color={p.muted}>{fmtDate(s.next_due, true)}</T>
                  </Row>
                ))}
              </Card>
            </Section>
          ) : null}

          <Row style={{ alignItems: 'flex-start', paddingHorizontal: space[1] }}>
            <Icon name="info.circle" size={14} color={p.faint} />
            <T v="small" color={p.faint} style={{ flex: 1, marginLeft: space[2] }}>{d.note}</T>
          </Row>
        </>
      )}
    </Screen>
  );
}
