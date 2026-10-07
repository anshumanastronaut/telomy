import { router, Stack, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Bars } from '@/ui/charts';
import { Button, Card, Chip, Divider, ErrorState, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';
import { SafetyChip, VerdictChip, inr } from '@/ui/therapy';

export default function TherapyDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: m, error, reload } = useApi<any>(`/therapy/catalogue/${id}`, [id]);
  const [busy, setBusy] = useState(false);
  const { toast, show } = useToast();
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!m) return <Screen edges={[]}><Loading what="Loading therapy…" /></Screen>;
  const r = m.response;
  const blocked = m.safety.status === 'not_suitable';

  async function book() {
    const d = new Date(Date.now() + 86400000 * 2).toISOString().slice(0, 10);
    try {
      const res = await api('/centre/bookings', { body: { patient_id: 1, service_id: m.id, ts: `${d}T18:00:00` } });
      show(`${res.message} ${d} 18:00`, 'success');
    } catch (e: any) { show(e.message, 'alert'); }
  }
  async function start() {
    setBusy(true);
    try {
      const s = await api('/therapy/sessions', { body: { modality: m.id, params: m.params } });
      router.push(`/session/${s.id}?live=1`);
    } catch (e: any) { show(e.message, 'alert'); } finally { setBusy(false); }
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: m.name }} />
        <T v="h1">{m.name}</T>
        <Row style={{ flexWrap: 'wrap' }}>
          <VerdictChip verdict={m.my_verdict} />
          <Chip label={`Evidence ${m.evidence}`} fg={p.teal} bg={p.tealSoft} />
          <SafetyChip status={m.safety.status} />
          <Chip label={`${m.minutes} min · ${inr(m.price)}`} />
        </Row>
        {m.safety.status !== 'ok' ? <Card tone="copper"><T v="body">{m.safety.summary}</T></Card> : null}
        <T v="body">{m.mechanism}</T>

        <Section title="What happens inside your body">
          <Card style={{ paddingVertical: 4 }}>
            {m.inside.map(([when, what]: [string, string], i: number) => (
              <View key={when} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border, gap: 2 }}>
                <T v="label" color={p.copper}>{when}</T>
                <T v="body">{what}</T>
              </View>
            ))}
          </Card>
        </Section>

        {r ? (
          <Section title="Your response, measured">
            <Card>
              <T v="body">{r.why}</T>
              <T v="small" color={p.teal}>{r.recommendation}</T>
            </Card>
            {r.metrics.length ? (
              <Card style={{ paddingVertical: 4 }}>
                <T v="label" style={{ paddingTop: 8 }}>Inside the session (mean of {r.sessions})</T>
                {r.metrics.map((x: any, i: number) => (
                  <View key={x.key} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                    <Row>
                      <T v="body" style={{ flex: 1 }}>{x.label}</T>
                      <T v="num" style={{ fontSize: 16 }}>{x.mean} <T v="small">{x.unit}</T></T>
                    </Row>
                    <T v="small">
                      {x.literature ? `Literature ${x.literature.range[0]} to ${x.literature.range[1]} (${x.literature.source}) · you are ${x.literature.verdict}` : `first ${x.first} → last ${x.last}`}
                      {x.trend_per_session != null ? ` · trend ${x.trend_per_session > 0 ? '+' : ''}${x.trend_per_session}/session` : ''}
                    </T>
                  </View>
                ))}
              </Card>
            ) : null}
            {r.next_day.length ? (
              <Card style={{ paddingVertical: 4 }}>
                <T v="label" style={{ paddingTop: 8 }}>The next night (adjusted for your other events)</T>
                {r.next_day.map((x: any, i: number) => (
                  <Row key={x.metric} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                    <T v="body" style={{ flex: 1 }}>{x.label}</T>
                    <T v="small" style={{ fontVariant: ['tabular-nums'] }} color={x.significant || x.nominal ? (x.helpful ? p.success : p.danger) : p.muted}>
                      {x.effect > 0 ? '+' : ''}{x.effect} {x.unit} [{x.ci95[0]}, {x.ci95[1]}] {x.p_text}
                    </T>
                  </Row>
                ))}
              </Card>
            ) : null}
            {r.dose_response ? (
              <Card>
                <T v="label">Does the setting matter for you?</T>
                <Bars data={r.dose_response.rows.map((x: any) => ({ x: `${x.setting}`, y: Math.abs(x.mean), label: `${x.setting} ${r.dose_response.unit}` }))} height={90} unit={r.dose_response.outcome_unit} />
                <T v="small">{r.dose_response.note}</T>
              </Card>
            ) : null}
            {Object.keys(r.subjective).length ? (
              <T v="small">How you felt after vs before: {Object.entries(r.subjective).map(([k, v]) => `${k} ${(v as number) > 0 ? '+' : ''}${v}`).join(' · ')} (0–10 scale)</T>
            ) : null}
          </Section>
        ) : (
          <Card><T v="body">You haven't tried this yet. Telomy will measure your in-session response and the next night from your first visit.</T></Card>
        )}

        <Row>
          <Button title="Book at the centre" icon="calendar.badge.plus" style={{ flex: 1 }} disabled={blocked} onPress={book} />
          <Button kind="secondary" title="Start now" icon="play.circle" style={{ flex: 1 }} disabled={blocked} loading={busy} onPress={start} testID="start-session" />
        </Row>
        <T v="small">"Start now" declares the session to Telomy, so it loads your expected response curve and can merge your chest-strap, watch or machine data.</T>

        {m.sessions?.length ? (
          <Section title={`Your sessions · ${m.sessions.length}`}>
            <Card style={{ paddingVertical: 4 }}>
              {m.sessions.slice(0, 12).map((s: any, i: number) => (
                <View key={s.id}>
                  {i ? <Divider /> : null}
                  <Row style={{ paddingVertical: 8 }}>
                    <View style={{ flex: 1 }}>
                      <T v="body" onPress={() => router.push(`/session/${s.id}`)}>{fmtDate(s.ts)} · {s.ts.slice(11, 16)}</T>
                      <T v="small">{Object.entries(s.params).filter(([k]) => typeof s.params[k] !== 'object').slice(0, 2).map(([k, v]) => `${k.replace(/_/g, ' ')} ${v}`).join(' · ')}
                        {s.features.rebound_pct != null ? ` · HRV ${s.features.rebound_pct > 0 ? '+' : ''}${s.features.rebound_pct}%` : ''}</T>
                    </View>
                    <Button kind="ghost" title="Open" onPress={() => router.push(`/session/${s.id}`)} />
                  </Row>
                </View>
              ))}
            </Card>
          </Section>
        ) : null}

        <Section title="Research behind it">
          {m.refs.map((ref: string) => <T key={ref} v="small">• {ref}</T>)}
          {m.devices?.length ? <T v="small">Machines here: {m.devices.map((d: any) => `${d.name}${d.status !== 'available' ? ` (${d.status.replace(/_/g, ' ')})` : ''}`).join('; ')}</T> : null}
        </Section>
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
