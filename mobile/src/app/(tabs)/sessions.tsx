import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, ErrorState, Icon, ListRow, Loading, Row, Screen, Section, Segmented, Spacer, T, useToast } from '@/ui/core';

export default function Sessions() {
  const p = usePalette();
  const today = useApi<any>('/today');
  const prots = useApi<any[]>('/protocols');
  const plan = useApi<any>('/action-plan');
  const studies = useApi<any[]>('/studies');
  const sess = useApi<any>('/sessions/stats');
  const [pillar, setPillar] = useState<'Lifestyle' | 'Diet' | 'Fitness' | 'Supplements'>('Lifestyle');
  const [planTab, setPlanTab] = useState<'food' | 'supplement' | 'lifestyle'>('lifestyle');
  const { toast, show } = useToast();

  async function toggle(id: string, done: boolean) {
    const r = await api('/today', { body: { item_id: id, done } });
    today.setData(r);
    if (done) show('Saved.', 'success');
  }

  if (today.error) return <Screen><ErrorState message={today.error} onRetry={today.reload} /></Screen>;
  const active = prots.data?.find((x) => x.active);
  const items = (today.data?.items ?? []).filter((i: any) => i.pillar === pillar);
  const done = (today.data?.items ?? []).filter((i: any) => i.done).length;

  return (
    <View style={{ flex: 1 }}>
      <Screen onRefresh={() => { today.reload(); prots.reload(); plan.reload(); studies.reload(); }} refreshing={today.loading}>
        <T v="h1">Sessions</T>
        {active ? (
          <Card tone="teal">
            <Row>
              <T v="label">Active protocol · {active.phase}</T>
              <Spacer />
              <Chip label={`Evidence ${active.evidence}`} fg={p.teal} bg={p.surface} />
            </Row>
            <T v="h2">{active.title}</T>
            <T v="small">Authored by {active.author} · reviews {active.review}</T>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {active.targets.map((t: string) => <Chip key={t} label={t} />)}
            </View>
          </Card>
        ) : null}

        <Section title={`Today · ${done}/${today.data?.items?.length ?? 0} done`}>
          <Segmented
            options={(['Lifestyle', 'Diet', 'Fitness', 'Supplements'] as const).map((k) => ({ key: k, label: k }))}
            value={pillar}
            onChange={setPillar}
          />
          {!today.data ? (
            <Loading what="Loading today's plan…" />
          ) : items.length ? (
            <Card style={{ paddingVertical: 4 }}>
              {items.map((it: any, i: number) => (
                <Pressable key={it.id} onPress={() => toggle(it.id, !it.done)} accessibilityRole="checkbox" accessibilityState={{ checked: it.done }} testID={`check-${it.id}`} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderTopColor: p.border, minHeight: 48 }}>
                  <View style={{ width: 24, height: 24, borderRadius: 12, borderWidth: 1.5, borderColor: it.done ? p.teal : p.borderStrong, backgroundColor: it.done ? p.teal : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
                    {it.done ? <Icon name="checkmark" size={12} color="#fff" /> : null}
                  </View>
                  <View style={{ flex: 1 }}>
                    <T v="body" style={{ textDecorationLine: it.done ? 'line-through' : 'none' }}>{it.title}</T>
                    <T v="small">{it.when}</T>
                  </View>
                </Pressable>
              ))}
            </Card>
          ) : (
            <T v="small">Nothing in {pillar.toLowerCase()} for this phase.</T>
          )}
        </Section>

        <Row gap={space[3]}>
          <Tile icon="wind" title="Breathe" sub={sess.data ? `${sess.data.sessions} sessions · ${sess.data.total_minutes} min · ${sess.data.days_in_a_row} d in a row` : '—'} onPress={() => router.push('/breathe')} />
          <Tile icon="fork.knife" title="Weekly menu" sub="Indian meals, swap any" onPress={() => router.push('/menu')} />
        </Row>
        <Row gap={space[3]}>
          <Tile icon="flask" title="N-of-1 studies" sub={studies.data ? `${studies.data.length} studies` : '—'} onPress={() => router.push('/studies')} />
          <Tile icon="square.grid.2x2" title="Marketplace" sub="Clinician-authored" onPress={() => router.push('/marketplace')} />
        </Row>

        {plan.data ? (
          <Section title="Action plan from your results">
            <Segmented
              options={[
                { key: 'lifestyle', label: `Lifestyle · ${plan.data.lifestyle.length}` },
                { key: 'food', label: `Food · ${plan.data.food.length}` },
                { key: 'supplement', label: `Supplements · ${plan.data.supplement.length}` },
              ]}
              value={planTab}
              onChange={setPlanTab}
            />
            <Card style={{ paddingVertical: 4 }}>
              {plan.data[planTab].map((a: any, i: number) => (
                <View key={a.title}>
                  {i ? <Divider /> : null}
                  <View style={{ paddingVertical: 12, gap: 6, opacity: a.avoid ? 0.75 : 1 }}>
                    <Row>
                      <T v="body" style={{ flex: 1, fontWeight: '600' }}>{a.title}</T>
                      {a.avoid ? (
                        <Chip label="Avoid" fg={p.danger} bg={p.dangerSoft} icon="xmark" />
                      ) : (
                        <Chip label={`${a.impact} impact`} fg={a.impact === 'high' ? p.teal : p.muted} bg={a.impact === 'high' ? p.tealSoft : p.surfaceAlt} />
                      )}
                    </Row>
                    {a.dose ? <T v="small">Dose: {a.dose}</T> : null}
                    {a.contains ? <T v="small">Contains: {a.contains}</T> : null}
                    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                      {a.targets.map((t: any) => (
                        <Pressable key={t.id} onPress={() => router.push(`/marker/${t.id}`)}>
                          <Chip label={`Targets ${t.name}`} />
                        </Pressable>
                      ))}
                    </View>
                    {a.avoid ? <T v="small" color={p.danger}>{a.avoid}</T> : null}
                    {a.caution ? <T v="small" color={p.warn}>{a.caution}</T> : null}
                  </View>
                </View>
              ))}
            </Card>
            <T v="small">Supplements are suggestions to discuss with your clinician, not prescriptions.</T>
          </Section>
        ) : null}

        <Section title="Protocols" action="Marketplace" onAction={() => router.push('/marketplace')}>
          {(prots.data ?? []).map((pr) => (
            <Card key={pr.id}>
              <Row>
                <T v="h3" style={{ flex: 1 }}>{pr.title}</T>
                {pr.active ? <Chip label="Active" fg={p.success} bg={p.successSoft} /> : null}
              </Row>
              <T v="small">{pr.author} · {pr.phase} · evidence {pr.evidence}</T>
            </Card>
          ))}
        </Section>
      </Screen>
      {toast}
    </View>
  );
}

function Tile({ icon, title, sub, onPress }: { icon: any; title: string; sub: string; onPress: () => void }) {
  const p = usePalette();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => ({ flex: 1, backgroundColor: p.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: p.border, padding: space[4], gap: 6, opacity: pressed ? 0.8 : 1 })}>
      <Icon name={icon} size={22} color={p.teal} />
      <T v="h3">{title}</T>
      <T v="small">{sub}</T>
    </Pressable>
  );
}
