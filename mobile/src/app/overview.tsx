// Your health summary — the member-facing 360, served by /me/overview: the same combined picture the clinic
// sees (labs, vitals, recovery/sleep, habits, reports) with a grounded AI summary. Every number traces to a
// value in your own Vault; nothing is invented, and missing domains show "—" rather than a guess.
import { router, Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Card, Chip, Divider, ErrorState, ListRow, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';

const n = (x: any, u = '') => (x == null ? '—' : `${x}${u}`);

const ENV_LABEL: Record<string, string> = { air_quality: 'Air quality', social_connection: 'Social connection', noise: 'Noise', uv: 'UV', water: 'Water', food_quality: 'Food quality' };
function envLine(f: any): string {
  if (f.factor === 'air_quality') return `PM2.5 ${f.pm25} µg/m³ · ≈${f.life_years_lost ?? '—'} yr lost (AQLI)`;
  if (f.factor === 'social_connection') return `${f.lonely_pct}% loneliness context · isolation ≈ +26% mortality`;
  if (f.factor === 'noise') return `~${f.lden_db_estimated} dB · +${f.coronary_disease_risk_increase_pct}% coronary risk`;
  if (f.factor === 'uv') return `UV max ~${f.uv_mean_max ?? '—'}`;
  if (f.factor === 'food_quality') return 'From your diet log (NOVA), not your postcode';
  return f.note ?? '';
}

export default function OverviewScreen() {
  const p = usePalette();
  const { data, error, reload } = useApi<any>('/me/overview');
  const organs = useApi<any>('/me/organs');
  const env = useApi<any>('/me/environment');

  if (error) return <Screen edges={[]}><Stack.Screen options={{ title: 'Health summary' }} /><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={[]}><Stack.Screen options={{ title: 'Health summary' }} /><Loading what="Pulling your record together…" /></Screen>;

  const ai = data.ai_summary ?? {};
  const rc = data.recovery_sleep ?? {};
  const vt = data.vitals ?? {};
  const hb = data.habits ?? {};
  const rm = data.risk_models ?? {};
  const bm = data.biomarkers ?? {};
  const raw: any[] = bm.raw ?? [];
  const reports: any[] = data.reports ?? [];
  const cvd = rm.cvd?.risk;
  const dm = rm.diabetes ?? {};
  const liver = rm.liver?.score;

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Health summary' }} />
      <T v="h1">Your health, in one view</T>

      {/* grounded AI summary */}
      <Card tone="teal">
        <Row style={{ justifyContent: 'space-between' }}>
          <T v="label">AI summary</T>
          <Chip label="draft · grounded" />
        </Row>
        <T v="body">{ai.text}</T>
        <T v="small" color={p.muted}>{ai.disclaimer}</T>
      </Card>

      <Card onPress={() => router.push('/plan')} accessibilityLabel="Your longevity plan">
        <Row>
          <View style={{ flex: 1 }}>
            <T v="h3">Your longevity plan</T>
            <T v="small">Evidence-graded interventions and your protein · fibre · fat fix, from these numbers.</T>
          </View>
          <T v="small" color={p.teal} style={{ fontWeight: '600' }}>View →</T>
        </Row>
      </Card>

      {/* recovery + vitals */}
      <Section title="Recovery & vitals">
        <Row>
          <Stat label="Recovery" value={rc.recovery_pct != null ? rc.recovery_pct : '—'} unit={rc.recovery_pct != null ? '%' : ''} sub={rc.interpretation || 'HRV vs your baseline'} />
          <Stat label="Resting HR" value={n(vt.resting_hr)} unit={vt.resting_hr != null ? ' bpm' : ''} sub="7-day" />
        </Row>
        <Row>
          <Stat label="Sleep SpO₂ low" value={n(vt.nocturnal_spo2_min)} unit={vt.nocturnal_spo2_min != null ? '%' : ''} sub="nocturnal dip" />
          <Stat label="Steps" value={hb.steps_per_day_7d != null ? Math.round(hb.steps_per_day_7d) : '—'} sub="per day · 7-day" />
        </Row>
        {!vt.available ? <T v="small" color={p.muted}>Connect a wearable to fill recovery, resting HR and sleep oxygen.</T> : null}
      </Section>

      {/* risk models */}
      <Section title="Risk (model estimates — discuss with your clinician)">
        <Row>
          <Stat label="10-yr CVD" value={n(cvd)} unit={cvd != null ? '%' : ''} sub="PCE" color={cvd != null && cvd >= 7.5 ? p.copper : undefined} />
          <Stat label="5-yr diabetes" value={dm.already ? 'in range' : n(dm.risk)} unit={!dm.already && dm.risk != null ? '%' : ''} />
          <Stat label="FIB-4 liver" value={n(liver)} color={liver != null && liver >= 1.3 ? p.copper : undefined} />
        </Row>
      </Section>

      {/* habits */}
      {hb.available ? (
        <Section title="Habits">
          <Card>
            {hb.exercise_min_per_day != null ? <ListRow title="Activity" right={<T v="body">{`${hb.exercise_min_per_day} min/day`}</T>} /> : null}
            {hb.smoker != null ? <ListRow title="Smoking" right={<T v="body">{hb.smoker ? 'yes' : 'no'}</T>} /> : null}
            {hb.alcohol != null ? <ListRow title="Alcohol" right={<T v="body">{String(hb.alcohol)}</T>} /> : null}
            {hb.bp_treated != null ? <ListRow title="BP treated" right={<T v="body">{hb.bp_treated ? 'yes' : 'no'}</T>} /> : null}
          </Card>
        </Section>
      ) : null}

      {/* latest labs */}
      {raw.length ? (
        <Section title={`Latest labs${data.as_of ? ` · as of ${data.as_of}` : ''}`}>
          <Card style={{ gap: 0 }}>
            {raw.slice(0, 20).map((r, i) => (
              <View key={r.id || r.marker || i}>
                {i ? <Divider /> : null}
                <Row style={{ justifyContent: 'space-between', paddingVertical: 8 }}>
                  <T v="body" style={{ flex: 1 }}>{r.marker}</T>
                  <T v="num" style={{ fontSize: 18 }}>{r.value}</T>
                </Row>
              </View>
            ))}
          </Card>
          <T v="small" color={p.muted}>Latest value per marker, pulled from your Vault ({bm.source}).</T>
        </Section>
      ) : null}

      {/* reports */}
      {reports.length ? (
        <Section title="Reports" action="Open Vault" onAction={() => router.push('/vault')}>
          {reports.slice(0, 6).map((r) => (
            <ListRow key={r.id} title={r.title || r.panel_title || 'Report'} subtitle={`${r.panel_title || ''}${r.collected_on ? ' · ' + r.collected_on : ''}`}
              right={<T v="small" color={r.flagged ? p.copper : p.muted}>{r.flagged ? `${r.flagged} flagged` : 'clear'}</T>}
              onPress={() => router.push(`/report/${r.id}`)} />
          ))}
        </Section>
      ) : null}

      {/* organ clocks */}
      {organs.data?.organs?.length ? (
        <Section title="How each system is aging" action="Open twin" onAction={() => router.push('/body')}>
          <Card style={{ gap: 0 }}>
            {organs.data.organs.map((o: any, i: number) => {
              const acc = o.age_acceleration_years;
              const col = acc == null ? p.text : acc >= 2 ? p.copper : acc <= -1 ? p.teal : p.text;
              return (
                <View key={o.organ}>
                  {i ? <Divider /> : null}
                  <Row style={{ justifyContent: 'space-between', paddingVertical: 8 }}>
                    <T v="body" style={{ flex: 1 }}>{o.label}</T>
                    <T v="num" style={{ fontSize: 18, marginRight: 8 }} color={col}>{o.organ_age != null ? Math.round(o.organ_age) : '—'}</T>
                    {acc != null ? <T v="small" color={col}>{acc > 0 ? '+' : ''}{acc}y</T> : null}
                  </Row>
                </View>
              );
            })}
          </Card>
          <T v="small" color={p.muted}>{organs.data.note}</T>
        </Section>
      ) : null}

      {/* environment / exposome */}
      {env.data?.factors?.length ? (
        <Section title="What your city does to you" action="Details" onAction={() => router.push('/environment')}>
          <Card style={{ gap: 0 }}>
            {env.data.factors.map((f: any, i: number) => (
              <View key={f.factor}>
                {i ? <Divider /> : null}
                <Row style={{ justifyContent: 'space-between', alignItems: 'flex-start', paddingVertical: 8 }}>
                  <View style={{ flex: 1 }}>
                    <T v="body" style={{ fontWeight: '600' }}>{ENV_LABEL[f.factor] ?? f.factor}</T>
                    <T v="small" color={p.muted}>{envLine(f)}</T>
                  </View>
                  {f.confidence ? <Chip label={f.confidence} /> : null}
                </Row>
              </View>
            ))}
          </Card>
        </Section>
      ) : null}

      <T v="small" color={p.muted} style={{ textAlign: 'center', marginTop: 8 }}>
        {ai.drafted_by}
      </T>
      <View style={{ height: 16 }} />
    </Screen>
  );
}
