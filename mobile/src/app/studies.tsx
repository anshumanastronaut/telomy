import { useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, Section, Stat, T } from '@/ui/core';

const OUTCOMES = [['deep_sleep', 'Deep sleep'], ['hrv', 'HRV'], ['sleep_score', 'Sleep score'], ['rhr', 'Resting HR']];

export default function Studies() {
  const p = usePalette();
  const params = useLocalSearchParams<{ intervention?: string }>();
  const { data, reload } = useApi<any[]>('/studies');
  const [iv, setIv] = useState(params.intervention ?? '');
  const [out, setOut] = useState('deep_sleep');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  async function create() {
    setErr(null);
    try {
      const r = await api('/studies', { body: { title: `Does ${iv} change my ${OUTCOMES.find((o) => o[0] === out)![1].toLowerCase()}?`, intervention: iv, outcome: out } });
      setMsg(r.message);
      setIv('');
      reload();
    } catch (e: any) {
      setErr(e.message);
    }
  }
  return (
    <Screen edges={[]}>
      <T v="body" color={p.muted}>An N-of-1 study alternates weeks on and off an intervention, then compares your own data. You get one of three verdicts: Helped, No reliable signal, or Possible negative.</T>
      <Section title="Start a study">
        <Card>
          <TextInput value={iv} onChangeText={setIv} placeholder="Intervention, e.g. Magnesium 300 mg at night" placeholderTextColor={p.faint} style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, fontFamily: 'Inter_400Regular' }} />
          <T v="label">Outcome</T>
          <Row style={{ flexWrap: 'wrap' }}>
            {OUTCOMES.map(([k, l]) => (
              <Pressable key={k} onPress={() => setOut(k)}>
                <Chip label={l} fg={out === k ? '#fff' : p.text} bg={out === k ? p.teal : p.surfaceAlt} />
              </Pressable>
            ))}
          </Row>
          {err ? <T v="small" color={p.danger}>{err}</T> : null}
          {msg ? <T v="body" color={p.success}>{msg}</T> : null}
          <Button title="Schedule ABAB study (4 weeks)" disabled={!iv.trim()} onPress={create} />
        </Card>
      </Section>
      <Section title="Your studies">
        {!data ? <Loading what="Loading…" /> : null}
        {data?.map((s) => {
          const r = s.result;
          const verdictCol = r.verdict === 'Helped' ? [p.success, p.successSoft] : r.verdict === 'Possible negative' ? [p.danger, p.dangerSoft] : [p.warn, p.warnSoft];
          return (
            <Card key={s.id}>
              <Row>
                <T v="h3" style={{ flex: 1 }}>{s.title}</T>
                <Chip label={r.verdict} fg={verdictCol[0]} bg={verdictCol[1]} />
              </Row>
              <T v="small">{s.intervention} · {s.design} · {s.period_days}-day periods from {fmtDate(s.start_day, true)} · outcome {s.outcome_label}</T>
              {r.mean_on != null ? (
                <>
                  <Row>
                    <Stat label="On" value={r.mean_on} unit={r.unit} />
                    <Stat label="Off" value={r.mean_off} unit={r.unit} />
                    <Stat label="Difference" value={(r.diff > 0 ? '+' : '') + r.diff} unit={r.unit} />
                  </Row>
                  <T v="small">n = {r.n_on} on / {r.n_off} off · d = {r.d} · p ≈ {r.p} · {r.method}</T>
                  {r.verdict === 'No reliable signal' ? <T v="small">The difference is smaller than your normal night-to-night variation. A longer study would tell you more.</T> : null}
                </>
              ) : (
                <T v="small">{r.days_logged ?? 0} of {r.days_total ?? 28} days logged so far.</T>
              )}
            </Card>
          );
        })}
      </Section>
    </Screen>
  );
}
