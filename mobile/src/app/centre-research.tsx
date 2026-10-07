import { Stack } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, Chip, Loading, Row, Screen, Section, T } from '@/ui/core';

export default function CentreResearch() {
  const p = usePalette();
  const out = useApi<any[]>('/centre/therapy-outcomes');
  const ph = useApi<any>('/centre/research/phenotypes');
  const val = useApi<any>('/physio/validation');
  if (!out.data || !ph.data) return <Screen edges={[]}><Loading what="Analysing every session…" /></Screen>;
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Outcomes & research' }} />
      <T v="h1">What your machines do to people</T>
      <Section title="Therapy response phenotypes (cold)">
        <Card tone="teal">
          <T v="body">{ph.data.n} members clustered by their cryo/plunge fingerprint — HRV rebound, rewarming half-time and recovery constant k.</T>
          {ph.data.finding ? (
            <T v="h3">{ph.data.finding.x} vs {ph.data.finding.y}: r = {ph.data.finding.r} ({ph.data.finding.p}, n = {ph.data.finding.n})</T>
          ) : null}
          <T v="small">{ph.data.caveat}</T>
        </Card>
        {ph.data.groups?.map((g: any) => (
          <Card key={g.phenotype}>
            <Row><T v="h3" style={{ flex: 1 }}>{g.phenotype}</T><Chip label={`${g.members} members`} />{g.includes_you ? <Chip label="Aarav here" fg={p.copper} bg={p.copperSoft} /> : null}</Row>
            <T v="small">HRV rebound {g.rebound_pct}% · rewarming half-time {g.rewarm_half_min} min · k {g.k}/min</T>
            <T v="small">Average HbA1c {g.hba1c}% · BMI {g.bmi} · night HRV {g.hrv_night} ms</T>
          </Card>
        ))}
      </Section>
      <Section title="Every therapy, every session">
        {out.data.map((m) => (
          <Card key={m.modality}>
            <Row><T v="h3" style={{ flex: 1 }}>{m.name}</T><Chip label={`Evidence ${m.evidence}`} /></Row>
            <T v="small">{m.sessions} sessions · {m.members} members{m.hr_peak_delta != null ? ` · HR change ${m.hr_peak_delta > 0 ? '+' : ''}${m.hr_peak_delta} bpm` : ''}{m.rebound_pct != null ? ` · HRV after ${m.rebound_pct > 0 ? '+' : ''}${m.rebound_pct}%` : ''}</T>
            <T v="small">Pain {m.pain_change ?? '—'} · calm {m.calm_change != null ? (m.calm_change > 0 ? '+' : '') + m.calm_change : '—'} (0–10){m.pain_responders_pct != null ? ` · ${m.pain_responders_pct}% had ≥2-point pain relief` : ''}</T>
            <T v="small" color={m.adverse || m.safety_flags ? p.warn : p.muted}>Adverse events {m.adverse} · safety flags {m.safety_flags}</T>
          </Card>
        ))}
      </Section>
      {val.data ? (
        <Section title="Model check against the literature">
          <Card>
            <T v="body">{val.data.all_pass ? 'All physiology targets reproduced' : 'Some targets out of range'} — the ODE prior is checked against published ranges before its traces are used.</T>
            {['cryo', 'cold', 'hbot', 'sauna', 'sauna_ir'].map((k) => (val.data[k] ?? []).map((c: any) => (
              <T key={k + c.metric} v="small" color={c.pass ? p.success : p.danger}>{c.pass ? '✓' : '✗'} {k} · {c.metric.replace(/_/g, ' ')} {c.mean} (target {c.range[0]}–{c.range[1]}, {c.source})</T>
            )))}
          </Card>
        </Section>
      ) : null}
      <View style={{ height: space[2] }} />
    </Screen>
  );
}
