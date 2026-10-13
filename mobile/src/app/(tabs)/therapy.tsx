import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { fmtDate, useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ErrorState, Icon, Loading, Row, Screen, Section, T } from '@/ui/core';
import { HsaiCard, VerdictChip, inr } from '@/ui/therapy';
import { BandTools } from '@/ui/ecg';

export default function Therapy() {
  const p = usePalette();
  const { data: d, error, reload, loading } = useApi<any>('/therapy');
  if (error) return <Screen><T v="h1">Therapy</T><BandTools /><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!d) return <Screen><T v="h1">Therapy</T><BandTools /><Loading what="Loading your centre…" /></Screen>;
  const working = d.working.filter((w: any) => w.verdict === 'helped' || w.verdict === 'promising');
  const rest = d.working.filter((w: any) => w.verdict !== 'helped' && w.verdict !== 'promising');
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Therapy</T>
      <LinearGradient testID="centre-card" colors={['#121C18', '#0B1210']} style={{ borderRadius: 28, padding: space[5], gap: space[3], borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)' }}>
        <Row>
          <T v="label" color="rgba(255,255,255,0.6)" style={{ flex: 1 }}>Your centre</T>
          <View style={{ paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, backgroundColor: 'rgba(92,201,167,0.16)' }}>
            <T v="small" color="#5CC9A7" style={{ fontWeight: '600', fontSize: 12 }}>{d.membership.plan}</T>
          </View>
        </Row>
        <T v="h2" color="#fff">{d.centre.name}</T>
        <T v="small" color="rgba(255,255,255,0.6)">{d.centre.hours} · {d.centre.address}</T>
        <View style={{ gap: 6, marginTop: space[1] }}>
          <Row>
            <T v="num" color="#fff" style={{ fontSize: 28 }}>{d.membership.sessions_this_month}</T>
            <T v="small" color="rgba(255,255,255,0.6)" style={{ flex: 1 }}> of {d.membership.credits} sessions this month</T>
          </Row>
          <View style={{ height: 6, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <View style={{ width: `${Math.min(100, (100 * d.membership.sessions_this_month) / Math.max(1, d.membership.credits))}%`, height: 6, borderRadius: 3, backgroundColor: '#FF9A5A' }} />
          </View>
        </View>
        <Row gap={space[2]} style={{ marginTop: space[1] }}>
          <HeroAction icon="record.circle" label="Record" onPress={() => router.push('/capture')} />
          <HeroAction icon="calendar.badge.plus" label="Book" onPress={() => router.push('/therapies')} />
          <HeroAction icon="wand.and.stars" label="Plan" onPress={() => router.push('/therapy-plan')} />
          <HeroAction icon="folder" label="Sessions" onPress={() => router.push('/captures')} />
        </Row>
      </LinearGradient>

      <BandTools liveOnly />
      <HsaiCard h={d.hsai} />

      <Section title="What's working for you" action="All therapies" onAction={() => router.push('/therapies')}>
        <T v="small">Measured from your own sessions: what happens inside the machine, and what changes the next night.</T>
        {working.map((w: any) => <WorkingCard key={w.modality} w={w} />)}
      </Section>
      <Section title="No reliable signal yet">
        {rest.map((w: any) => <WorkingCard key={w.modality} w={w} compact />)}
      </Section>

      <Card tone="copper">
        <T v="h3">Build my therapy plan</T>
        <T v="small">Pick a goal; Telomy ranks therapies by what worked for you, the evidence and your safety screen. Your clinician signs it before anything is booked.</T>
        <Button kind="copper" title="Build a plan" icon="wand.and.stars" onPress={() => router.push('/therapy-plan')} testID="build-plan" />
        {d.plan ? <T v="small">Latest plan: {d.plan.goal} · {d.plan.state.replace('_', ' ')}{d.plan.doctor ? ` · ${d.plan.doctor}` : ''}</T> : null}
      </Card>

      {d.upcoming.length ? (
        <Section title="Upcoming at the centre">
          <Card style={{ paddingVertical: 4 }}>
            {d.upcoming.map((b: any, i: number) => (
              <Row key={b.id} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <T v="body" style={{ flex: 1 }}>{b.service}</T>
                <T v="small">{fmtDate(b.ts)} · {b.ts.slice(11, 16)}</T>
              </Row>
            ))}
          </Card>
        </Section>
      ) : null}

      <Section title="Recent sessions">
        <Card style={{ paddingVertical: 4 }}>
          {d.recent.map((s: any, i: number) => (
            <Row key={s.id} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
              <View style={{ flex: 1 }}>
                <T v="body" onPress={() => router.push(`/session/${s.id}`)}>{s.name}</T>
                <T v="small">{fmtDate(s.ts)} · {s.ts.slice(11, 16)} · {s.safety}</T>
              </View>
              <Button kind="ghost" title="Inside" onPress={() => router.push(`/session/${s.id}`)} />
            </Row>
          ))}
        </Card>
      </Section>

      <Row>
        <Button kind="secondary" title="Tests & scans" icon="testtube.2" style={{ flex: 1 }} onPress={() => router.push('/tests')} />
        <Button kind="secondary" title="Supplements & Rx" icon="pills" style={{ flex: 1 }} onPress={() => router.push('/rx')} />
      </Row>
      <Button kind="ghost" title="Breathing session (resonance 6/min)" icon="wind" onPress={() => router.push('/breathe')} />
      <View style={{ height: space[2] }} />
    </Screen>
  );
}

function WorkingCard({ w, compact }: { w: any; compact?: boolean }) {
  const p = usePalette();
  const key = w.metrics[0];
  return (
    <Card onPress={() => router.push(`/therapy/${w.modality}`)} testID={`working-${w.modality}`}>
      <Row>
        <T v="h3" style={{ flex: 1 }}>{w.name}</T>
        <VerdictChip verdict={w.verdict} />
      </Row>
      {!compact ? <T v="body">{w.why}</T> : <T v="small" numberOfLines={2}>{w.why}</T>}
      {key && !compact ? (
        <T v="small">
          Inside the session: {key.label.toLowerCase()} {/delta|pct|change/.test(key.key) && key.mean > 0 ? '+' : ''}{Math.round(key.mean * 10) / 10} {key.unit}
          {key.literature ? ` (literature ${key.literature.range[0]}–${key.literature.range[1]})` : ''}
        </T>
      ) : null}
      <T v="small" color={p.muted}>{w.sessions} sessions · {inr(w.spend)} · evidence {w.evidence}</T>
    </Card>
  );
}

function HeroAction({ icon, label, onPress }: { icon: any; label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label}
      style={({ pressed }) => ({ flex: 1, alignItems: 'center', gap: 6, paddingVertical: 12, borderRadius: 18, backgroundColor: pressed ? 'rgba(255,255,255,0.14)' : 'rgba(255,255,255,0.07)' })}>
      <Icon name={icon} size={18} color="#fff" />
      <T v="small" color="rgba(255,255,255,0.85)" style={{ fontWeight: '600', fontSize: 12 }}>{label}</T>
    </Pressable>
  );
}
