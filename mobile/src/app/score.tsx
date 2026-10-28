// Telomy Score — the headline longevity number + domain sub-scores + biological age, from the member's labs.
// Wellness information, not a diagnosis. Backend: /score (app/score.py).
import { router, Stack } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Card, Empty, Icon, Loading, Row, Screen, T } from '@/ui/core';
import { Ring } from '@/ui/charts';

type Marker = { id: string; name: string; value: number; unit: string; score: number; status: string };
type Domain = { key: string; name: string; score: number; status: string; band: string; n: number; markers: Marker[] };
type Score = { score: number | null; band: string | null; bio_age: number | null; chrono_age: number | null;
  age_delta: number | null; clock: string | null; domains: Domain[]; coverage: number; note: string };

function scoreColor(s: number, p: any) {
  return s >= 70 ? '#2F8F6B' : s >= 55 ? '#C98A1B' : '#D3523F';
}

export default function TelomyScore() {
  const p = usePalette();
  const r = useApi<Score>('/score');
  const [open, setOpen] = useState<Record<string, boolean>>({});

  if (!r.data) return <Screen><Stack.Screen options={{ title: 'Telomy Score' }} /><Loading what="Working out your score…" /></Screen>;
  const d = r.data;

  if (d.score == null) {
    return (
      <Screen edges={['top']}>
        <Stack.Screen options={{ title: 'Telomy Score' }} />
        <Empty title="Add labs to see your score" body="Upload a blood report and your Telomy Score, domain sub-scores and biological age will appear here."
          actions={[{ title: 'Add a report', onPress: () => router.push('/upload') }]} />
      </Screen>
    );
  }

  const younger = d.age_delta != null && d.age_delta < 0;
  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Telomy Score' }} />

      {/* headline */}
      <Card style={{ alignItems: 'center', gap: space[2], paddingVertical: space[5] }}>
        <Ring value={d.score} size={160} stroke={14} color={scoreColor(d.score, p)} label={`${d.score}`} />
        <T v="h2" style={{ color: scoreColor(d.score, p), textTransform: 'capitalize' }}>{d.band}</T>
        <T v="small" color={p.muted} style={{ textAlign: 'center' }}>Composite of {d.coverage} health domains vs optimal ranges</T>
      </Card>

      {/* biological age */}
      {d.bio_age != null ? (
        <Card>
          <Row style={{ alignItems: 'center' }}>
            <View style={{ flex: 1 }}>
              <T v="label">BIOLOGICAL AGE</T>
              <Row gap={8} style={{ alignItems: 'baseline', marginTop: 2 }}>
                <T v="display" style={{ fontSize: 40 }}>{d.bio_age}</T>
                {d.chrono_age != null ? <T v="small" color={p.muted}>vs {d.chrono_age} actual</T> : null}
              </Row>
              {d.clock ? <T v="small" color={p.faint}>from {d.clock}</T> : null}
            </View>
            {d.age_delta != null ? (
              <View style={{ alignItems: 'center', backgroundColor: (younger ? '#2F8F6B' : '#D3523F') + '22', borderRadius: radius.md, paddingVertical: space[2], paddingHorizontal: space[3] }}>
                <T v="h3" style={{ color: younger ? '#2F8F6B' : '#D3523F' }}>{younger ? '' : '+'}{d.age_delta}</T>
                <T v="small" color={p.muted}>{younger ? 'years younger' : 'years older'}</T>
              </View>
            ) : null}
          </Row>
        </Card>
      ) : null}

      {/* domain sub-scores, weakest first */}
      <T v="label" style={{ marginTop: space[2] }}>DOMAIN SCORES</T>
      {d.domains.map((dom) => {
        const isOpen = open[dom.key];
        const c = scoreColor(dom.score, p);
        return (
          <Pressable key={dom.key} onPress={() => setOpen((o) => ({ ...o, [dom.key]: !o[dom.key] }))}>
            <Card style={{ gap: space[2] }}>
              <Row style={{ alignItems: 'center' }}>
                <T v="num" style={{ fontSize: 22, color: c, width: 44 }}>{dom.score}</T>
                <View style={{ flex: 1 }}>
                  <T v="h3">{dom.name}</T>
                  <View style={{ height: 6, borderRadius: 3, backgroundColor: p.surfaceAlt, marginTop: 4, overflow: 'hidden' }}>
                    <View style={{ width: `${dom.score}%`, height: 6, backgroundColor: c }} />
                  </View>
                </View>
                <Icon name={isOpen ? 'chevron.up' : 'chevron.down'} size={13} color={p.faint} />
              </Row>
              {isOpen ? (
                <View style={{ gap: 6, marginTop: 4 }}>
                  {dom.markers.map((m) => (
                    <Row key={m.id} style={{ alignItems: 'center' }}>
                      <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: scoreColor(m.score, p) }} />
                      <T v="small" style={{ flex: 1, marginLeft: 8 }}>{m.name}</T>
                      <T v="small" color={p.muted}>{m.value} {m.unit}</T>
                    </Row>
                  ))}
                </View>
              ) : null}
            </Card>
          </Pressable>
        );
      })}

      <Card onPress={() => router.push('/retest' as any)} accessibilityLabel="Retest plan">
        <Row style={{ alignItems: 'center' }} gap={space[3]}>
          <Icon name="arrow.triangle.2.circlepath" size={20} color={p.teal} />
          <View style={{ flex: 1 }}>
            <T v="h3">Retest plan</T>
            <T v="small">What to re-measure, what's improved since last time, and when each marker is next due.</T>
          </View>
          <Icon name="chevron.right" size={13} color={p.faint} />
        </Row>
      </Card>

      <Row style={{ alignItems: 'flex-start', paddingHorizontal: space[1], marginTop: space[1] }}>
        <Icon name="info.circle" size={14} color={p.faint} />
        <T v="small" color={p.faint} style={{ flex: 1, marginLeft: space[2] }}>{d.note}</T>
      </Row>
    </Screen>
  );
}
