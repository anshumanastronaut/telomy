// Activity & recovery — one source of truth. The four scores are the SAME on-device engine as Home (recovery from
// overnight HRV + lowest HR vs your own 30 nights, strain from heart-rate-zone TRIMP on a 0–21 scale, sleep and stress),
// movement is your real Apple Health day, and every vital is compared with YOUR own last 30 days — never a demo
// dashboard. Nothing here invents a number: a tile appears only when its signal has data.
import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';
import { useApi } from '@/lib/api';
import { useHealth } from '@/lib/health';
import { data, radius, space, type, usePalette } from '@/lib/theme';
import { fmtDur, useWellness } from '@/lib/wellness';
import { Button, Card, Chip, Icon, Row, Screen, Section, T } from '@/ui/core';
import { ScoreRing, StrainColumns } from '@/ui/wellness';

const GOALS = { steps: 10000, kcal: 500, exercise: 30 };

/** Today vs your own history: usual range = mean ± 1.5 SD of up to 30 previous values (needs 5+). */
function vsBaseline(today: number | null | undefined, history: (number | null | undefined)[]) {
  if (today == null) return null;
  const h = history.filter((x): x is number => x != null && isFinite(x)).slice(-30);
  if (h.length < 5) return { today, state: 'learning' as const, lo: null, hi: null };
  const m = h.reduce((a, b) => a + b, 0) / h.length, sd = Math.sqrt(h.reduce((a, b) => a + (b - m) ** 2, 0) / (h.length - 1)) || 0.0001;
  const lo = m - 1.5 * sd, hi = m + 1.5 * sd;
  return { today, state: today > hi ? ('above' as const) : today < lo ? ('below' as const) : ('usual' as const), lo, hi };
}

export default function Activity() {
  const p = usePalette();
  const prof = useApi<any>('/profile');
  const w = useWellness(prof.data?.age ?? null);
  const h = useHealth(63);
  const t = h.today;
  const days = h.data ?? [];
  const nights = w.nights ?? [];
  const prevNights = nights.slice(0, -1);

  // ---- the scores (same on-device engine as Home) — Energy ("body battery") leads, then recovery/strain/sleep/stress
  const scores = [
    { key: 'energy', label: 'Energy', v: w.energy.score, max: 100, text: w.energy.score != null ? `${w.energy.score}` : '—', color: data.activity, sub: w.energy.label },
    { key: 'recovery', label: 'Recovery', v: w.recovery.score, max: 100, text: w.recovery.score != null ? `${w.recovery.score}` : '—', color: data.recovery, sub: w.recovery.label },
    { key: 'strain', label: 'Strain', v: w.today.worn >= 10 ? w.today.strain : null, max: 21, text: w.today.worn >= 10 ? w.today.strain.toFixed(1) : '—', color: data.heart, sub: w.today.worn >= 10 ? `${w.today.activeMin} active min` : 'Wear the patch' },
    { key: 'sleep', label: 'Sleep', v: w.sleep?.score ?? null, max: 100, text: w.sleep?.score != null ? `${w.sleep.score}` : '—', color: data.sleep, sub: w.last ? fmtDur(w.last.tstMin) : 'No night yet' },
    { key: 'stress', label: 'Stress', v: w.today.stress.score, max: 100, text: w.today.stress.score != null ? `${w.today.stress.score}` : '—', color: data.stress, sub: w.today.stress.minutes ? `${w.today.stress.calmMin} calm min` : 'From the patch' },
  ];

  // ---- movement vs goals (bars, with "over goal" said in words instead of a 197 % ring)
  const move = [
    { key: 'steps', label: 'Steps', v: t?.steps, goal: GOALS.steps, unit: '', color: data.activity },
    { key: 'kcal', label: 'Active energy', v: t?.activeKcal, goal: GOALS.kcal, unit: 'kcal', color: data.temp },
    { key: 'exercise', label: 'Exercise', v: t?.exerciseMin, goal: GOALS.exercise, unit: 'min', color: data.hrv },
  ].filter((m) => m.v != null);

  // ---- vitals vs YOUR baseline (only those with data)
  const vitals = [
    { key: 'rhr', label: 'Resting heart rate', unit: 'bpm', dp: 0, r: vsBaseline(t?.restingHr ?? w.restingHr, days.slice(0, -1).map((d: any) => d.restingHr)), to: '/wellness/recovery' },
    { key: 'hrv', label: 'Night HRV', unit: 'ms', dp: 0, r: w.last?.sleepRmssd != null ? vsBaseline(w.last.sleepRmssd, prevNights.map((n) => n.sleepRmssd)) : vsBaseline(t?.hrvSdnn, days.slice(0, -1).map((d: any) => d.hrvSdnn)), to: '/wellness/recovery' },
    { key: 'low', label: 'Lowest night HR', unit: 'bpm', dp: 0, r: vsBaseline(w.last?.lowestHr, prevNights.map((n) => n.lowestHr)), to: '/wellness/sleep' },
    { key: 'resp', label: 'Breathing rate', unit: '/min', dp: 1, r: w.last?.respRate != null ? vsBaseline(w.last.respRate, prevNights.map((n) => n.respRate)) : vsBaseline(t?.respRate, days.slice(0, -1).map((d: any) => d.respRate)), to: '/wellness/sleep' },
    { key: 'spo2', label: 'Blood oxygen', unit: '%', dp: 0, r: vsBaseline(t?.spo2, days.slice(0, -1).map((d: any) => d.spo2)), to: '/ring' },
    { key: 'sleep', label: 'Sleep duration', unit: 'h', dp: 1, r: vsBaseline(w.last ? w.last.tstMin / 60 : null, prevNights.map((n) => n.tstMin / 60)), to: '/wellness/sleep' },
  ].filter((v) => v.r);

  // ---- last 7 days of steps, last 9 weeks of exercise minutes
  const week = days.slice(-7);
  const weekMax = Math.max(1, ...week.map((d: any) => d.steps ?? 0));
  const exDays = days.slice(-63);
  const exMax = Math.max(1, ...exDays.map((d: any) => d.exerciseMin ?? 0));

  return (
    <Screen edges={[]}>
      <View style={{ gap: space[1] }}>
        <T v="label">{new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}</T>
        <T v="small">The same scores as your Home, worked out on this phone from your own data.</T>
      </View>

      {/* what to do today — one clear call from energy, recovery and stress */}
      {w.guidance ? (
        <Card tone={w.guidance.tone}>
          <Row style={{ alignItems: 'flex-start' }}>
            <Icon name={w.guidance.action === 'sleep' ? 'moon.zzz' : w.guidance.action === 'breathe' ? 'wind' : 'figure.run'} size={18} color={w.guidance.tone === 'teal' ? p.teal : p.copper} />
            <View style={{ flex: 1, gap: 2 }}>
              <T v="h3">{w.guidance.title}</T>
              <T v="small">{w.guidance.body}</T>
            </View>
          </Row>
          {w.guidance.action === 'breathe' ? <Button kind="secondary" title="Start a breathing session" icon="wind" onPress={() => router.push('/breathe')} /> : null}
        </Card>
      ) : null}

      {/* the scores */}
      <View style={{ flexDirection: 'row', gap: space[2] }}>
        {scores.map((s) => (
          <Pressable key={s.key} onPress={() => router.push(`/wellness/${s.key}` as any)} accessibilityRole="button" accessibilityLabel={`${s.label} ${s.text}`}
            style={({ pressed }) => ({ flex: 1, alignItems: 'center', gap: space[1], paddingVertical: space[3], borderRadius: radius.lg, backgroundColor: p.surface, opacity: pressed ? 0.8 : 1 })}>
            <ScoreRing value={s.v} max={s.max} size={58} stroke={6} color={s.color} track={p.surfaceAlt} center={s.text} />
            <T v="small" color={p.text} style={{ fontWeight: '600' }}>{s.label}</T>
            <T v="small" style={{ fontSize: type.micro, textAlign: 'center' }} numberOfLines={1}>{s.sub}</T>
          </Pressable>
        ))}
      </View>

      <WhatAffectsYou />

      {move.length ? (
        <Section title="Movement today">
          <Card style={{ gap: space[4] }}>
            {move.map((m) => {
              const pct = (m.v as number) / m.goal;
              return (
                <View key={m.key} style={{ gap: 6 }}>
                  <Row>
                    <T v="body" style={{ flex: 1, fontWeight: '600' }}>{m.label}</T>
                    <T v="num" style={{ fontSize: type.lead }}>{Math.round(m.v as number).toLocaleString('en-IN')}</T>
                    <T v="small"> / {m.goal.toLocaleString('en-IN')} {m.unit}</T>
                  </Row>
                  <View style={{ height: 8, borderRadius: 4, backgroundColor: p.surfaceAlt, overflow: 'hidden' }}>
                    <View style={{ width: `${Math.min(100, pct * 100)}%`, height: 8, borderRadius: 4, backgroundColor: m.color }} />
                  </View>
                  <T v="small" style={{ fontSize: type.micro }} color={pct >= 1 ? m.color : p.faint}>
                    {pct >= 1 ? (pct >= 1.05 ? `Goal met · ${Math.round((pct - 1) * 100)} % over` : 'Goal met') : `${Math.round((1 - pct) * m.goal).toLocaleString('en-IN')} ${m.unit || 'steps'} to go`}
                  </T>
                </View>
              );
            })}
            <T v="small" style={{ fontSize: type.micro }} color={p.faint}>From your phone's health · goals {GOALS.steps.toLocaleString('en-IN')} steps, {GOALS.kcal} kcal, {GOALS.exercise} min</T>
          </Card>
        </Section>
      ) : null}

      {w.today.minutes.some((m) => m.hr) ? (
      <Section title="Today's load, hour by hour">
        <Card>
          <StrainColumns mins={w.today.minutes} age={w.age} />
          <T v="small">Height is each hour's training load; colours are minutes in each heart-rate zone. Strain {w.today.worn >= 10 ? w.today.strain.toFixed(1) : '—'} of 21 so far.</T>
        </Card>
      </Section>
      ) : null}

      {vitals.length ? (
        <Section title="Vitals vs your usual">
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -space[1] }}>
            {vitals.map((v) => {
              const r = v.r!;
              const col = r.state === 'usual' ? p.success : r.state === 'learning' ? p.muted : p.warn;
              const msg = r.state === 'usual' ? 'Within your usual range' : r.state === 'learning' ? 'Learning your normal' : r.state === 'above' ? 'Above your usual range' : 'Below your usual range';
              return (
                <View key={v.key} style={{ width: '50%', padding: space[1] }}>
                  <Pressable onPress={() => router.push(v.to as any)} accessibilityRole="button"
                    style={({ pressed }) => ({ padding: space[4], gap: 2, borderRadius: radius.lg, backgroundColor: p.surface, opacity: pressed ? 0.8 : 1 })}>
                    <T v="small" numberOfLines={1}>{v.label}</T>
                    <Row gap={3} style={{ alignItems: 'baseline' }}>
                      <T v="num" style={{ fontSize: type.h2 }}>{r.today.toFixed(v.dp)}</T>
                      <T v="small">{v.unit}</T>
                    </Row>
                    <T v="small" style={{ fontSize: type.micro }} color={col}>{msg}</T>
                    {r.lo != null && r.hi != null ? <T v="small" style={{ fontSize: type.micro }} color={p.faint}>Usual {r.lo.toFixed(v.dp)}–{r.hi.toFixed(v.dp)} {v.unit}</T> : null}
                  </Pressable>
                </View>
              );
            })}
          </View>
        </Section>
      ) : null}

      {week.length ? (
        <Section title="Your week">
          <Card style={{ gap: space[2] }}>
            <Row style={{ alignItems: 'flex-end', height: 110 }} gap={space[2]}>
              {week.map((d: any, i: number) => (
                <View key={d.date} style={{ flex: 1, alignItems: 'center', gap: 4 }}>
                  <View style={{ width: '70%', height: Math.max(3, ((d.steps ?? 0) / weekMax) * 84), borderRadius: 4, backgroundColor: i === week.length - 1 ? data.activity : p.surfaceAlt }} />
                  <T v="small" style={{ fontSize: type.micro }}>{new Date(d.date + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'narrow' })}</T>
                </View>
              ))}
            </Row>
            <T v="small">Steps each day · average {Math.round(week.reduce((a: number, d: any) => a + (d.steps ?? 0), 0) / week.length).toLocaleString('en-IN')}</T>
          </Card>
        </Section>
      ) : null}

      {exDays.some((d: any) => d.exerciseMin) ? (
        <Section title="Exercise · last 9 weeks">
          <Card>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
              {exDays.map((d: any) => (
                <View key={d.date} accessibilityLabel={`${d.date}: ${Math.round(d.exerciseMin ?? 0)} minutes`}
                  style={{ width: 34, height: 16, borderRadius: 3, backgroundColor: d.exerciseMin ? data.hrv : p.surfaceAlt, opacity: d.exerciseMin ? 0.2 + 0.8 * (d.exerciseMin / exMax) : 1 }} />
              ))}
            </View>
            <T v="small">Darker means more exercise minutes; seven squares per week.</T>
          </Card>
        </Section>
      ) : null}

      <Pressable onPress={() => router.push('/training' as any)} accessibilityRole="button"
        style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: space[3], padding: space[4], borderRadius: radius.lg, backgroundColor: p.surface, opacity: pressed ? 0.8 : 1 })}>
        <T v="h3" style={{ flex: 1 }}>Exercise & training</T>
        <T v="small" color={p.teal}>Sessions and load →</T>
      </Pressable>

      <Card>
        <T v="label">How these are worked out</T>
        <T v="small">Energy ("body battery") charges from your overnight recovery and sleep and drains with today's exertion and sustained stress. Recovery compares last night's HRV and lowest heart rate with your own previous 30 nights, adjusted for sleep, breathing and yesterday's strain (green 67+, amber 34–66, red 33 or less). Strain weights every minute by heart-rate zone (Edwards TRIMP) on a 0–21 scale. Stress compares daytime heart rate and HRV with your calm baseline. Usual ranges are your own mean ± 1.5 standard deviations.</T>
      </Card>
    </Screen>
  );
}

/** Welltory-style "what affects you" preview: the top event→signal effects from the correlation engine. */
function WhatAffectsYou() {
  const p = usePalette();
  const ins = useApi<any[]>('/insights');
  const items = (ins.data ?? []).filter((x) => x.kind === 'event_effect').slice(0, 3);
  if (!items.length) return null;
  return (
    <Section title="What affects you">
      <Card style={{ gap: space[2] }} onPress={() => router.push('/insights' as any)}>
        {items.map((x) => (
          <Row key={x.id} style={{ alignItems: 'flex-start' }}>
            <Icon name="sparkles" size={13} color={p.teal} />
            <View style={{ flex: 1 }}>
              <T v="body" style={{ fontWeight: '600' }}>{x.title}</T>
              {x.receipts ? <T v="small" color={p.muted}>{x.receipts.n} days · r {x.receipts.r} · p {x.receipts.p}</T> : null}
            </View>
          </Row>
        ))}
        <Row><T v="small" color={p.teal} style={{ flex: 1 }}>See all your correlations</T><Icon name="chevron.right" size={12} color={p.teal} /></Row>
      </Card>
    </Section>
  );
}
