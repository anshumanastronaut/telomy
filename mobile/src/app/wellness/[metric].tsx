// Detail for Recovery · Sleep · Strain · Stress: score, contributors, charts, method and sources.
import { router, Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, type, usePalette, data } from '@/lib/theme';
import { fmtClock, fmtDur, hrMax, useWellness } from '@/lib/wellness';
import { Button, Card, Empty, Loading, Row, Screen, Section, Segmented, T } from '@/ui/core';
import { C, DetailHero } from '@/ui/today';
import { TrendChart } from '@/ui/trends';
import { nightSeries, normalBand, type Wellness } from '@/lib/wellness';
import { SOURCE_LABEL } from '@/lib/sleepfuse';
import { StageBreakdown, StrainColumns, ContributorList, Hypnogram, LastNightCard, MiniMetric, NightHrChart, NightTrend, recoveryColor, StressStrip, ZoneBar } from '@/ui/wellness';

const METHODS: Record<string, { title: string; how: string; sources: string[] }> = {
  recovery: {
    title: 'Recovery',
    how: 'Your overnight HRV (ln RMSSD) and lowest heart rate are compared with your own last 30 nights, together with breathing rate, sleep and yesterday’s strain. A normal day for you scores about 60; green is 67+, amber 34–66, red 33 or less. Until 3 nights are recorded it compares you with typical adults.',
    sources: ['Plews DJ et al. 2013, Sports Med: daily ln RMSSD vs rolling baseline', 'Buchheit M 2014, Front Physiol: monitoring with HR and HRV', 'Nunan D et al. 2010, PACE: normal short-term HRV values'],
  },
  sleep: {
    title: 'Sleep',
    how: 'Wake, light, deep and REM sleep are estimated every 30 s from your heart rhythm and ECG-derived breathing by a small neural network (convolution + bidirectional GRU) trained on 151 hospital sleep-lab nights with expert scoring. Tested on sleep-lab nights it never saw, it agrees with expert scoring about 6 epochs in 10 (κ 0.36), similar to consumer wearables: total sleep and timing are reliable, deep and REM minutes are estimates. The score combines duration, efficiency, time to fall asleep, time awake, wake-ups, overnight HRV vs your normal, the heart-rate drop in sleep and timing regularity. Breathing rate comes from your ECG and is shown only when two independent methods agree. Nights come from the best device you wore: the patch (ECG stages), then Apple Watch stages from Apple Health, then the ring (sleep and wake from its heart-rate log and your iPhone\u2019s motion, no stages), then any other Health sleep. Sleep need = baseline (8 h until 14 nights, then learnt from your longer nights, 7–9 h) + up to 45 min for a hard day + your sleep debt. Each night, 55 % of what you missed carries into the next night\u2019s target (a rule that tracked WHOOP\u2019s own sleep debt within 15 minutes on 93 % of 853 nights); extra sleep clears it but never banks. Regularity is the Sleep Regularity Index: how likely you are in the same state (asleep or awake) at the same clock time on consecutive days.',
    sources: ['Hirshkowitz M et al. 2015, Sleep Health: NSF sleep duration', 'Ohayon M et al. 2017, Sleep Health: NSF sleep-quality indicators', 'Phillips AJK et al. 2017, Sci Rep: sleep regularity', 'Sridhar N et al. 2020, npj Digit Med: sleep staging from instantaneous heart rate', 'Radha M et al. 2019, Sci Rep: sleep stages from HRV with LSTM', 'Alvarez-Estevez D, Rijsman R 2021, PLoS One: HMC sleep staging database', 'Ohayon M et al. 2004, Sleep: normative sleep architecture', 'Charlton PH et al. 2016, Physiol Meas: respiratory rate from the ECG', 'Van Dongen HPA et al. 2003, Sleep: cumulative cost of sleep restriction', 'Banks S et al. 2010, Sleep: recovery sleep dose response', 'Klerman EB, Dijk DJ 2005, Curr Biol: sleep need under extended sleep', 'Schyvens AM et al. 2025: six wearables vs polysomnography', 'de Zambotti M et al. 2019, Med Sci Sports Exerc: wearable sleep technology', 'Karlen W et al. 2013, IEEE TBME: smart fusion'],
  },
  strain: {
    title: 'Strain',
    how: 'During patch sessions, each minute\u2019s heart rate is placed in one of five zones of your maximum (208 − 0.7 × age), weighted 1–5 (Edwards TRIMP) and mapped to 0–21. When you wear a WHOOP all day, every minute counts in proportion to effort measured against your heart-rate reserve (Banister TRIMP), ignoring near-resting minutes, because fixed zones counted ordinary walking as training on all-day data. Workouts are detected when heart rate rises 15+ bpm above resting while your wrist is moving for 5+ minutes; calories use the Keytel 2005 equation. The all-day number is not yet calibrated against WHOOP\u2019s own Day Strain.',
    sources: ['Edwards S 1993, The Heart Rate Monitor Book: zone TRIMP', 'Tanaka H et al. 2001, JACC: age-predicted maximal HR', 'Banister EW 1991: training impulse', 'Karvonen MJ 1957: heart-rate reserve', 'Keytel LR et al. 2005, J Sports Sci: energy expenditure from heart rate'],
  },
  stress: {
    title: 'Stress',
    how: 'While you are awake and not exercising, each minute is classed as calm, neutral or stress from your heart rate above resting and your HRV compared with your own calm minutes. The score is the share of stress minutes.',
    sources: ['Firstbeat Technologies 2014: stress and recovery analysis based on 24-h HRV', 'Kim HG et al. 2018, Psychiatry Investig: stress and HRV meta-analysis', 'Task Force of ESC/NASPE 1996: HRV standards'],
  },
};

export default function WellnessDetail() {
  const { metric = 'recovery' } = useLocalSearchParams<{ metric: string }>();
  const p = usePalette();
  const prof = useApi<any>('/profile');
  const w = useWellness(prof.data?.age ?? null);
  const m = METHODS[metric] ?? METHODS.recovery;
  const [hrKind, setHrKind] = React.useState<'hr' | 'hrv'>('hr');
  if (w.loading) return <Screen edges={[]}><Stack.Screen options={{ title: m.title }} /><Loading what="Analysing your night on the phone… (about half a minute)" /></Screen>;

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: m.title }} />
      {metric === 'recovery' ? (
        <>
          <DetailHero dial value={w.recovery.score} label={w.recovery.score == null ? 'Wear the band tonight' : w.recovery.label} color={recoveryColor(p, w.recovery.score)} sub={w.recovery.calibrating ?? (w.recovery.confidence === 'building' ? 'Building your baseline (under 14 nights): treat as provisional' : undefined)} />
          {w.illness?.flagged ? (
            <Card tone="copper" style={{ gap: space[1] }}>
              <T v="label">Your body may be fighting something</T>
              <T v="small">{w.illness.signals.map((x) => `${x.label} (${x.detail})`).join(' · ')} over the last two nights compared with your normal. Rest, fluids and an early night help; see a doctor if you feel unwell. A pattern in your own numbers, not a diagnosis.</T>
            </Card>
          ) : null}
          {w.recovery.contributors.length ? <Section title="What moved it"><ContributorList items={w.recovery.contributors} /></Section>
            : <Empty title="No night yet" body="Wear the band to bed and start Overnight sleep. Recovery appears the next morning." actions={[{ title: 'Start Overnight sleep', onPress: () => router.push('/capture') }]} />}
          <Trends w={w} kind="recovery" />
          {w.restingHr ? (
            <Section title="Heart fitness">
              <Row gap={space[2]}>
                <MiniMetric icon="heart" color={p.danger} label="Resting HR (awake)" value={`${Math.round(w.restingHr)} bpm`} sub="10th percentile of calm minutes" />
                <MiniMetric icon="figure.run" label="VO₂max (estimate)" value={w.vo2 ? `${Math.round(w.vo2)}` : '—'} sub="ml/kg/min · Uth 2004 ±5" />
              </Row>
            </Section>
          ) : null}
        </>
      ) : null}

      {metric === 'sleep' ? (
        w.last ? (
          <>
            <DetailHero value={w.sleep?.score ?? null} unit="SLEEP SCORE" label={w.sleep?.label ?? ''} sub={`${fmtDur(w.last.tstMin)} asleep · ${fmtClock(w.last.start)} – ${fmtClock(w.last.end)}`} color={C.sleep} />
            <T v="small" color={p.faint}>From {SOURCE_LABEL[w.last.source ?? 'patch']}{w.last.sourceName && w.last.source === 'health' ? ` (${w.last.sourceName})` : ''}</T>
            <SleepNeedCard w={w} />
            <LastNightCard n={w.last} sleep={w.sleep} history={w.nights} embedded />
            {w.last.stages?.length ? <Section title="Sleep stages"><Card><StageBreakdown n={w.last} /></Card></Section> : null}
            {w.last.hr5.length ? <Card>
              <Segmented options={[{ key: 'hr', label: 'Heart rate' }, { key: 'hrv', label: 'HRV' }]} value={hrKind} onChange={setHrKind} />
              <NightHrChart n={w.last} kind={hrKind} />
              <T v="small">{hrKind === 'hr'
                ? (w.last.lowestHrPos != null && w.last.lowestHrPos > 0.66 ? 'Your heart rate bottomed out late in the night. Late meals, alcohol, late exercise or a warm room often delay it.' : 'Your heart rate settled early, a sign your body could start recovering soon after you fell asleep.')
                : 'HRV usually rises through the night as recovery takes over.'}</T>
            </Card> : null}
            {w.sleep ? <Section title="Contributors"><ContributorList items={w.sleep.contributors} /></Section> : null}
            <Trends w={w} kind="sleep" />
            {w.last.source === 'patch' ? <Button kind="secondary" title="Open the full session" icon="folder" onPress={() => router.push('/captures')} /> : null}
          </>
        ) : <Empty title="No night yet" body="Wear the patch or ring to bed (Telomy detects sleep on its own), or connect Apple Health to use your Apple Watch's sleep." actions={[{ title: 'Start Overnight sleep', onPress: () => router.push('/capture') }]} />
      ) : null}

      {metric === 'strain' ? (
        <>
          <DetailHero value={w.today.worn >= 10 ? Math.round(w.today.strain * 10) / 10 : null} max={21} unit="OF 21" label="Today’s strain" sub={`${w.today.worn} min worn · ${w.today.activeMin} min active${w.today.source === 'whoop' ? ' · from WHOOP (all-day heart rate)' : ''}`} color={C.strain} />
          {w.today.whoop?.workouts.length ? (
            <Section title="Workouts detected today">
              {w.today.whoop.workouts.map((x) => (
                <Card key={x.start} style={{ gap: 2 }}>
                  <T v="h3">{fmtClock(x.start)} · {x.min} min</T>
                  <T v="small">avg {x.avgHr} bpm · max {x.maxHr}{x.kcal != null ? ` · ${x.kcal} kcal` : ''} · heart rate and wrist motion</T>
                </Card>
              ))}
            </Section>
          ) : null}
          <Button kind="secondary" title="Exercise & training" icon="figure.run" onPress={() => router.push('/training' as any)} />
          <Section title="Your day, hour by hour">
            <Card><StrainColumns mins={w.today.minutes} age={w.age} /><T v="small">Each column is one hour; height is that hour's load, colours are minutes in each heart-rate zone.</T></Card>
          </Section>
          <Section title="Heart-rate zones today">
            <Card><ZoneBar zones={w.today.zones} /><T v="small">Zones are % of your estimated max heart rate ({Math.round(hrMax(w.age))} bpm at age {Math.round(w.age)}).</T></Card>
          </Section>
          {w.yesterdayTrimp != null ? <T v="small">Yesterday’s training load: {w.yesterdayTrimp} TRIMP.</T> : null}
        </>
      ) : null}

      {metric === 'stress' ? (
        <>
          <DetailHero value={w.today.stress.score} unit="STRESS" label={w.today.stress.score == null ? 'Not enough daytime data' : w.today.stress.score >= 50 ? 'High' : w.today.stress.score >= 25 ? 'Moderate' : 'Low'} sub={`${w.today.stress.stressMin} stressed · ${w.today.stress.calmMin} calm minutes`} color={C.stress} />
          <Section title="Stress rhythm today"><Card><StressStrip timeline={w.today.stress.timeline} /></Card></Section>
          <Button kind="secondary" title="Breathe for 2 minutes" icon="wind" onPress={() => router.push('/breathe')} />
        </>
      ) : null}

      <Section title="How it’s calculated">
        <Card style={{ gap: space[2] }}>
          <T v="body">{m.how}</T>
          {m.sources.map((s) => <T key={s} v="small">• {s}</T>)}
          <T v="small" color={p.muted}>Wellness estimates from a single-lead ECG band, not a medical diagnosis.</T>
        </Card>
      </Section>
    </Screen>
  );
}

/** 7 / 30-night trends with the personal normal range shaded (previous ≤ 30 nights, mean ± 1 SD). */
function Trends({ w, kind }: { w: Wellness; kind: 'recovery' | 'sleep' }) {
  const [days, setDays] = React.useState<'7' | '30'>('7');
  if (w.nights.length < 1) return null;
  if (w.nights.length < 2) {
    return (
      <Section title="Trends">
        <Card style={{ gap: space[3] }}>
          <T v="body">Trends start after your second night, and your normal range after four.</T>
          <Row gap={6}>
            {[0, 1, 2, 3].map((i) => <View key={i} style={{ flex: 1, height: 6, borderRadius: 3, backgroundColor: i < w.nights.length ? C.sleep : 'rgba(127,127,127,0.2)' }} />)}
          </Row>
          <T v="small">{w.nights.length} of 4 nights recorded. Wear the band to bed tonight.</T>
        </Card>
      </Section>
    );
  }
  const series = nightSeries(w.nights);
  const win = series.slice(-Number(days));
  const pts = (f: (x: (typeof series)[number]) => number | null | undefined) =>
    win.map((x) => ({ t: x.n.end, v: f(x) })).filter((q): q is { t: number; v: number } => typeof q.v === 'number');
  const band = (f: (x: (typeof series)[number]) => number | null | undefined) =>
    normalBand(series.slice(0, -1).slice(-30).map(f).filter((v): v is number => typeof v === 'number'));
  const charts = kind === 'recovery'
    ? [
        { title: 'Recovery', f: (x: any) => x.recovery, color: C.green, unit: '%', up: true, dec: 0 },
        { title: 'Overnight HRV', f: (x: any) => x.n.sleepRmssd, color: '#5CC9A7', unit: 'ms', up: true, dec: 0 },
        { title: 'Lowest heart rate', f: (x: any) => x.n.lowestHr, color: data.heart, unit: 'bpm', up: false, dec: 0 },
      ]
    : [
        { title: 'Time asleep', f: (x: any) => x.n.tstMin / 60, color: C.sleep, unit: 'h', up: true, dec: 1 },
        { title: 'Sleep score', f: (x: any) => x.sleep, color: C.sleep, unit: '', up: true, dec: 0 },
        { title: 'Breathing rate', f: (x: any) => x.n.respRate, color: data.sleep, unit: '/min', up: false, dec: 1 },
      ];
  return (
    <Section title="Trends">
      <Segmented options={[{ key: '7', label: '7 nights' }, { key: '30', label: '30 nights' }]} value={days} onChange={setDays} />
      {charts.map((c) => <TrendChart key={c.title} title={c.title} points={pts(c.f)} band={band(c.f)} color={c.color} unit={c.unit} decimals={c.dec} higherIsBetter={c.up} />)}
    </Section>
  );
}

/** Tonight's sleep need (baseline + strain + debt repayment), the running debt and a suggested bedtime. */
function SleepNeedCard({ w }: { w: Wellness }) {
  const p = usePalette();
  const n = w.need;
  const parts: [string, number, string][] = [
    ['Baseline', n.baselineMin, n.personal ? 'learnt from your nights' : 'adult typical until 14 nights'],
    ['Today\u2019s strain', n.strainMin, 'harder days need more'],
    ['Paying back debt', n.repayMin, 'carried from short nights'],
  ];
  return (
    <Card style={{ gap: space[2] }}>
      <Row>
        <T v="label" style={{ flex: 1 }}>Tonight you need</T>
        {n.bedtime ? <T v="small">in bed by {fmtClock(n.bedtime)}</T> : null}
      </Row>
      <T v="num" style={{ fontSize: type.h1 }} color={C.sleep}>{fmtDur(n.needMin)}</T>
      {parts.map(([k, v, note]) => (
        <Row key={k}>
          <T v="small" style={{ flex: 1 }}>{k} <T v="small" color={p.faint}>· {note}</T></T>
          <T v="small">{v >= 1 ? (k === 'Baseline' ? fmtDur(v) : `+${Math.round(v)} min`) : '—'}</T>
        </Row>
      ))}
      <Row>
        <T v="small" style={{ flex: 1 }}>Sleep debt (last 14 nights)</T>
        <T v="small" color={n.debtMin > 120 ? p.warn : p.text}>{n.debtMin >= 1 ? fmtDur(n.debtMin) : 'none'}</T>
      </Row>
      {w.sri != null ? (
        <Row>
          <T v="small" style={{ flex: 1 }}>Sleep regularity index</T>
          <T v="small" color={w.sri >= 80 ? p.success : w.sri >= 65 ? p.text : p.warn}>{w.sri}</T>
        </Row>
      ) : null}
      {n.lastNightPct != null ? <T v="small">Last night you got {Math.round(n.lastNightPct * 100)} % of the sleep you needed.</T> : null}
    </Card>
  );
}
