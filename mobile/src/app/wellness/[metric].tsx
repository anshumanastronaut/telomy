// Detail for Recovery · Sleep · Strain · Stress: score, contributors, charts, method and sources.
import { router, Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { fmtClock, fmtDur, hrMax, useWellness } from '@/lib/wellness';
import { Button, Card, Empty, Loading, Row, Screen, Section, Segmented, T } from '@/ui/core';
import { ContributorList, Hypnogram, LastNightCard, MiniMetric, NightHrChart, NightTrend, recoveryColor, StressStrip, ZoneBar } from '@/ui/wellness';

const METHODS: Record<string, { title: string; how: string; sources: string[] }> = {
  recovery: {
    title: 'Recovery',
    how: 'Your overnight HRV (ln RMSSD) and lowest heart rate are compared with your own last 30 nights, together with breathing rate, sleep and yesterday’s strain. A normal day for you scores about 60; green is 67+, amber 34–66, red 33 or less. Until 3 nights are recorded it compares you with typical adults.',
    sources: ['Plews DJ et al. 2013, Sports Med: daily ln RMSSD vs rolling baseline', 'Buchheit M 2014, Front Physiol: monitoring with HR and HRV', 'Nunan D et al. 2010, PACE: normal short-term HRV values'],
  },
  sleep: {
    title: 'Sleep',
    how: 'Sleep and wake are estimated every 30 s from your heart rhythm (a model trained on PhysioNet sleep-lab nights). The score combines duration, efficiency, time to fall asleep, time awake, wake-ups, overnight HRV vs your normal, the heart-rate drop in sleep and timing regularity. Breathing rate comes from the breathing rhythm in your ECG.',
    sources: ['Hirshkowitz M et al. 2015, Sleep Health: NSF sleep duration', 'Ohayon M et al. 2017, Sleep Health: NSF sleep-quality indicators', 'Phillips AJK et al. 2017, Sci Rep: sleep regularity', 'Charlton PH et al. 2016, Physiol Meas: respiratory rate from the ECG', 'Karlen W et al. 2013, IEEE TBME: smart fusion'],
  },
  strain: {
    title: 'Strain',
    how: 'Every minute you wear the band, your heart rate is placed in one of five zones of your maximum (208 − 0.7 × age). Minutes are weighted 1–5 by zone (Edwards TRIMP) and mapped to a 0–21 scale: about 3 for a short walk, 13 for a 45-minute moderate run, 17+ for a hard long session.',
    sources: ['Edwards S 1993, The Heart Rate Monitor Book: zone TRIMP', 'Tanaka H et al. 2001, JACC: age-predicted maximal HR', 'Banister EW 1991: training impulse'],
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

  const header = (score: number | null, unit: string, label: string, color: string) => (
    <Card>
      <Row style={{ alignItems: 'baseline' }}>
        <T v="numLg" color={color}>{score == null ? '—' : score}</T>
        <T v="body" color={p.muted}>{unit}</T>
      </Row>
      <T v="h3">{label}</T>
    </Card>
  );

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: m.title }} />
      {metric === 'recovery' ? (
        <>
          {header(w.recovery.score, '%', w.recovery.calibrating ? `${w.recovery.label} · ${w.recovery.calibrating}` : w.recovery.label, recoveryColor(p, w.recovery.score))}
          {w.recovery.contributors.length ? <Section title="What moved it"><ContributorList items={w.recovery.contributors} /></Section>
            : <Empty title="No night yet" body="Wear the band to bed and start Overnight sleep. Recovery appears the next morning." actions={[{ title: 'Start Overnight sleep', onPress: () => router.push('/capture') }]} />}
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
            {header(w.sleep?.score ?? null, '/100', `${w.sleep?.label ?? ''} · ${fmtDur(w.last.tstMin)} asleep`, p.teal)}
            <LastNightCard n={w.last} sleep={w.sleep} />
            <Card>
              <Segmented options={[{ key: 'hr', label: 'Heart rate' }, { key: 'hrv', label: 'HRV' }]} value={hrKind} onChange={setHrKind} />
              <NightHrChart n={w.last} kind={hrKind} />
              <T v="small">{hrKind === 'hr'
                ? (w.last.lowestHrPos != null && w.last.lowestHrPos > 0.66 ? 'Your heart rate bottomed out late in the night. Late meals, alcohol, late exercise or a warm room often delay it.' : 'Your heart rate settled early, a sign your body could start recovering soon after you fell asleep.')
                : 'HRV usually rises through the night as recovery takes over.'}</T>
            </Card>
            {w.sleep ? <Section title="Contributors"><ContributorList items={w.sleep.contributors} /></Section> : null}
            {w.nights.length >= 2 ? <Section title="Last nights"><Card><NightTrend nights={w.nights} /><T v="small">Bars: hours asleep (blue = 7 h or more). Numbers: overnight HRV (ms).</T></Card></Section> : null}
            <Button kind="secondary" title="Open the full session" icon="folder" onPress={() => router.push('/captures')} />
          </>
        ) : <Empty title="No night yet" body="Wear the band to bed and start Overnight sleep from Therapy → Record therapy." actions={[{ title: 'Start Overnight sleep', onPress: () => router.push('/capture') }]} />
      ) : null}

      {metric === 'strain' ? (
        <>
          {header(w.today.worn >= 10 ? Math.round(w.today.strain * 10) / 10 : null, 'of 21', `${w.today.worn} min worn today · ${w.today.activeMin} min active`, p.copper)}
          <Section title="Heart-rate zones today">
            <Card><ZoneBar zones={w.today.zones} /><T v="small">Zones are % of your estimated max heart rate ({Math.round(hrMax(w.age))} bpm at age {Math.round(w.age)}).</T></Card>
          </Section>
          {w.yesterdayTrimp != null ? <T v="small">Yesterday’s training load: {w.yesterdayTrimp} TRIMP.</T> : null}
        </>
      ) : null}

      {metric === 'stress' ? (
        <>
          {header(w.today.stress.score, '/100', `${w.today.stress.stressMin} stress · ${w.today.stress.calmMin} calm minutes`, p.warn)}
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
