import { router } from 'expo-router';
import { SFSymbol } from 'expo-symbols';
import React, { useState } from 'react';
import { Pressable, View } from 'react-native';

import { ago, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Dial, Ring, Sparkline } from '@/ui/charts';
import { Card, Chip, ErrorState, Icon, Loading, Prov, Row, Screen, Section, Spacer, StatusChip, T } from '@/ui/core';
import { InsightCard } from '@/ui/insight';
import { Logo } from '@/ui/logo';

const REWIND = [
  { label: 'Today', days: 0 },
  { label: '1 wk ago', days: 7 },
  { label: '1 mo ago', days: 30 },
  { label: '3 mo ago', days: 90 },
];

function shift(day: string, days: number) {
  const d = new Date(day + 'T12:00:00');
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function Home() {
  const p = usePalette();
  const [rewind, setRewind] = useState(0);
  const base = useApi('/home');
  const asOf = base.data && rewind ? shift(base.data.as_of, rewind) : null;
  const past = useApi(asOf ? `/home?as_of=${asOf}` : null, [asOf]);
  const h = rewind && past.data ? past.data : base.data;

  if (base.error) return <Wrap><ErrorState message={base.error} onRetry={base.reload} /></Wrap>;
  if (!h) return <Wrap><Loading what="Reading your Vault…" /></Wrap>;
  const la = h.longevity;
  const today = new Date(h.as_of + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });

  return (
    <Wrap onRefresh={base.reload} refreshing={base.loading}>
      <Row>
        <Logo kind="mark" width={46} />
        <Logo kind="word" width={86} />
      </Row>
      <Row>
        <View style={{ flex: 1 }}>
          <T v="small">{rewind ? `Rewound to ${today}` : today}</T>
          <T v="h1">{greet()}, {h.first_name}</T>
        </View>
        <Pressable onPress={() => router.push('/notifications')} accessibilityLabel="Notifications" hitSlop={8} style={{ marginRight: 14 }}>
          <Icon name="bell" size={22} color={p.teal} />
        </Pressable>
        <Pressable onPress={() => router.push('/queue')} accessibilityLabel="Clinician review queue" hitSlop={8}>
          <Icon name="stethoscope" size={22} color={p.teal} />
          {h.pending_reviews ? (
            <View style={{ position: 'absolute', top: -6, right: -8, backgroundColor: p.copper, borderRadius: 8, paddingHorizontal: 5 }}>
              <T v="small" color="#fff" style={{ fontSize: 10 }}>
                {h.pending_reviews}
              </T>
            </View>
          ) : null}
        </Pressable>
      </Row>

      {h.is_test_profile ? <Chip label="Test profile · dummy data" fg={p.copper} bg={p.copperSoft} icon="flask" /> : null}

      <Card onPress={() => router.push('/longevity')} testID="dial" accessibilityLabel="Longevity age details">
        <Row>
          <T v="label">Longevity age</T>
          <Spacer />
          <T v="small" color={p.teal} style={{ fontWeight: '600' }}>
            How this is calculated
          </T>
        </Row>
        <View style={{ alignItems: 'center' }}>
          <Dial value={la.value} chrono={la.chronological} confidence={la.confidence} />
        </View>
        <Row style={{ justifyContent: 'space-around' }}>
          <MiniStat label="Pace of ageing" value={la.pace ? `${la.pace}×` : '—'} />
          <MiniStat label="Lab PhenoAge" value={la.clocks?.phenoage_lab?.value ?? '—'} />
          <MiniStat label="GrimAge" value={la.clocks?.grimage?.value ?? '—'} />
        </Row>
        <Prov source={la.method ? 'PhenoAge · blood panel' : undefined} when={la.as_of ? fmtDate(la.as_of, true) : null} confidence={la.confidence} />
      </Card>

      <Row gap={space[3]}>
        {h.cards.map((c: any) => (
          <DataCard key={c.id} c={c} asOf={h.as_of} />
        ))}
      </Row>
      <Row gap={space[3]}>
        {h.key_biomarker ? (
          <Card style={{ flex: 1 }} onPress={() => router.push(`/marker/${h.key_biomarker.id}`)}>
            <T v="label">{h.key_biomarker.label}</T>
            <Row gap={4} style={{ alignItems: 'baseline' }}>
              <T v="num">{h.key_biomarker.value}</T>
              <T v="small">{h.key_biomarker.unit}</T>
            </Row>
            <StatusChip status={h.key_biomarker.status} />
            {h.key_biomarker.trend ? (
              <T v="small">
                was {h.key_biomarker.trend.from} on {fmtDate(h.key_biomarker.trend.from_day)}
              </T>
            ) : null}
          </Card>
        ) : null}
        <Card style={{ flex: 1 }} tone="copper" onPress={() => router.push('/(tabs)/sessions')}>
          <T v="label">Next action</T>
          <T v="h3">{h.next_action.title}</T>
          <T v="small">{h.next_action.when}</T>
          {h.next_action.protocol ? <T v="small">{h.next_action.protocol}</T> : null}
        </Card>
      </Row>

      {h.insight ? (
        <Section title="Sinc's read today" action="All insights" onAction={() => router.push('/(tabs)/vault?tab=insights')}>
          <InsightCard i={h.insight} />
        </Section>
      ) : null}

      <Card onPress={() => router.push('/activity')} testID="activity-card">
        <Row>
          <Icon name="figure.walk" color={p.teal} />
          <View style={{ flex: 1 }}>
            <T v="body" style={{ fontWeight: '600' }}>Activity & recovery</T>
            <T v="small">Rings, recovery, strain, vitals vs your baseline</T>
          </View>
          <Icon name="chevron.right" size={13} color={p.faint} />
        </Row>
      </Card>

      <Row gap={space[2]}>
        <Quick icon="plus.circle" label="Log event" onPress={() => router.push('/log')} />
        <Quick icon="fork.knife" label="Log meal" onPress={() => router.push('/log?kind=meal')} />
        <Quick icon="bubble.left" label="Ask Sinc" onPress={() => router.push('/(tabs)/sinc')} />
        <Quick icon="wind" label="Breathe" onPress={() => router.push('/breathe')} />
      </Row>

      <Section title="Domains">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space[3] }}>
          {Object.entries(h.domains).map(([k, d]: any) => (
            <Card key={k} style={{ width: '47.5%' as any }} onPress={() => router.push(`/domain/${k}`)} testID={`domain-${k}`}>
              <Row>
                <Ring value={d.score} size={44} stroke={5} color={d.score == null ? p.faint : d.score >= 80 ? p.success : d.score >= 60 ? p.warn : p.danger} />
                <View style={{ flex: 1 }}>
                  <T v="body" style={{ fontWeight: '600' }} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.7}>{d.title.replace(' & gut', '')}</T>
                  <T v="small">{d.status ?? 'Not enough data'}</T>
                </View>
              </Row>
              <T v="small">{Math.round(d.confidence * 100)}% confidence · {Math.round(d.coverage * 100)}% coverage</T>
            </Card>
          ))}
        </View>
      </Section>

      <Section title="Pinned" action="Edit" onAction={() => router.push('/pins')}>
        <Card style={{ paddingVertical: space[1] }}>
          {h.pinned.map((c: any, i: number) => (
            <Pressable key={c.id} onPress={() => router.push(`/signal/${c.id}`)} style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: space[3], borderTopWidth: i ? 1 : 0, borderTopColor: p.border, gap: space[3] }}>
              <View style={{ flex: 1 }}>
                <T v="body">{c.label}</T>
                <T v="small">{c.value == null ? c.reason : `${c.source ?? ''} · ${ago(c.day, h.as_of)}`}</T>
              </View>
              <Sparkline data={c.spark ?? []} />
              <T v="num" style={{ fontSize: 18, minWidth: 64, textAlign: 'right' }}>
                {c.value == null ? '—' : c.value.toLocaleString('en-IN')}
                <T v="small"> {c.unit}</T>
              </T>
            </Pressable>
          ))}
        </Card>
      </Section>

      <Section title="Last 7 days">
        <Card>
          <T v="body">
            Sleep averaged <B>{h.last7.sleep_avg ?? '—'} h</B>, steps <B>{h.last7.steps_avg ? Math.round(h.last7.steps_avg).toLocaleString() : '—'}</B>, HRV{' '}
            <B>{h.last7.hrv_avg ?? '—'} ms</B>
            {h.last7.hrv_prev ? ` (${h.last7.hrv_avg >= h.last7.hrv_prev ? 'up' : 'down'} from ${h.last7.hrv_prev} the week before)` : ''}. You logged {h.last7.events} events, with alcohol on {h.last7.alcohol_days}{' '}
            {h.last7.alcohol_days === 1 ? 'day' : 'days'}.
          </T>
        </Card>
      </Section>

      {h.appointment ? (
        <Card onPress={() => router.push('/care')}>
          <T v="label">Upcoming</T>
          <T v="h3">
            {h.appointment.clinician.name} · {fmtDate(h.appointment.ts)} {new Date(h.appointment.ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
          </T>
          <T v="small">{h.appointment.reason} · Prepare a pre-clinic brief</T>
        </Card>
      ) : null}

      <Section title="Vault Rewind">
        <Row gap={space[2]}>
          {REWIND.map((r) => (
            <Pressable
              key={r.days}
              onPress={() => setRewind(r.days)}
              accessibilityRole="button"
              accessibilityState={{ selected: rewind === r.days }}
              style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.pill, borderWidth: 1, borderColor: rewind === r.days ? p.teal : p.border, backgroundColor: rewind === r.days ? p.tealSoft : p.surface }}>
              <T v="small" color={rewind === r.days ? p.teal : p.muted}>
                {r.label}
              </T>
            </Pressable>
          ))}
        </Row>
        <T v="small">See your Home exactly as it was on an earlier day — dial, cards and insights recomputed from what was known then.</T>
      </Section>

      <Card onPress={() => router.push('/completeness')}>
        <Row>
          <Ring value={h.completeness} size={44} stroke={5} />
          <View style={{ flex: 1 }}>
            <T v="body" style={{ fontWeight: '600' }}>Vault completeness</T>
            <T v="small">What's missing and how to add it</T>
          </View>
          <Icon name="chevron.right" size={13} color={p.faint} />
        </Row>
      </Card>
    </Wrap>
  );
}

function greet() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

function B({ children }: { children: React.ReactNode }) {
  return <T v="body" style={{ fontWeight: '600' }}>{children}</T>;
}

function MiniStat({ label, value }: { label: string; value: any }) {
  return (
    <View style={{ alignItems: 'center' }}>
      <T v="num" style={{ fontSize: 17 }}>{value}</T>
      <T v="small">{label}</T>
    </View>
  );
}

function DataCard({ c, asOf }: { c: any; asOf: string }) {
  const p = usePalette();
  return (
    <Card style={{ flex: 1 }} onPress={() => router.push(`/signal/${c.id}`)} testID={`card-${c.id}`}>
      <T v="label">{c.label}</T>
      {c.value == null ? (
        <T v="small">{c.reason}</T>
      ) : (
        <>
          <Row gap={4} style={{ alignItems: 'baseline' }}>
            <T v="num">{c.value}</T>
            <T v="small">{c.unit}</T>
          </Row>
          <Sparkline data={c.spark} width={110} />
          {c.delta != null ? (
            <T v="small" color={c.delta >= 0 ? p.success : p.danger}>
              {c.delta >= 0 ? '+' : ''}
              {c.delta} vs 30-day baseline
            </T>
          ) : null}
          <Prov source={c.source} when={ago(c.day, asOf)} />
        </>
      )}
    </Card>
  );
}

function Quick({ icon, label, onPress }: { icon: SFSymbol; label: string; onPress: () => void }) {
  const p = usePalette();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label} style={({ pressed }) => ({ flex: 1, alignItems: 'center', gap: 6, paddingVertical: space[3], backgroundColor: p.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: p.border, opacity: pressed ? 0.8 : 1 })}>
      <Icon name={icon} size={22} color={p.teal} />
      <T v="small" style={{ fontSize: 12 }}>{label}</T>
    </Pressable>
  );
}

function Wrap({ children, onRefresh, refreshing }: { children: React.ReactNode; onRefresh?: () => void; refreshing?: boolean }) {
  return (
    <Screen onRefresh={onRefresh} refreshing={refreshing}>
      {children}
    </Screen>
  );
}
