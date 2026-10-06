import { router, useLocalSearchParams } from 'expo-router';
import React, { useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, TextInput, View } from 'react-native';

import { ago, fmtDate, useApi } from '@/lib/api';
import { radius, space, statusColor, usePalette } from '@/lib/theme';
import { Sparkline, StackBar } from '@/ui/charts';
import { Button, Card, Chip, Divider, Empty, ErrorState, Icon, ListRow, Loading, Row, Screen, Section, Segmented, Spacer, StatusChip, T } from '@/ui/core';
import { InsightCard } from '@/ui/insight';

type Tab = 'markers' | 'insights' | 'signals' | 'timeline' | 'reports';

export default function Vault() {
  const params = useLocalSearchParams<{ tab?: string }>();
  const [tab, setTab] = useState<Tab>((params.tab as Tab) ?? 'markers');
  useEffect(() => {
    if (params.tab) setTab(params.tab as Tab);
  }, [params.tab]);
  return (
    <Screen>
      <Row>
        <T v="h1">Vault</T>
        <Spacer />
        <Button kind="secondary" icon="arrow.up.doc" title="Add report" onPress={() => router.push('/upload')} testID="add-report" />
      </Row>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
        {(
          [
            ['markers', 'Biomarkers'],
            ['insights', 'Insights'],
            ['signals', 'Signals'],
            ['timeline', 'Timeline'],
            ['reports', 'Reports'],
          ] as [Tab, string][]
        ).map(([k, l]) => (
          <Pill key={k} on={tab === k} label={l} onPress={() => setTab(k)} />
        ))}
      </ScrollView>
      {tab === 'markers' && <Markers />}
      {tab === 'insights' && <Insights />}
      {tab === 'signals' && <Signals />}
      {tab === 'timeline' && <Timeline />}
      {tab === 'reports' && <Reports />}
    </Screen>
  );
}

export function Pill({ on, label, onPress }: { on: boolean; label: string; onPress: () => void }) {
  const p = usePalette();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="tab"
      accessibilityState={{ selected: on }}
      style={{ paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.pill, backgroundColor: on ? p.teal : p.surface, borderWidth: 1, borderColor: on ? p.teal : p.border }}>
      <T v="small" color={on ? '#fff' : p.text} style={{ fontWeight: '600' }}>
        {label}
      </T>
    </Pressable>
  );
}

function Markers() {
  const p = usePalette();
  const panels = useApi<any[]>('/vault/panels');
  const concerns = useApi<any[]>('/vault/concerns');
  const risks = useApi<any[]>('/risks');
  const nudges = useApi<any[]>('/nudges');
  const derived = useApi<any[]>('/vault/derived');
  const [mode, setMode] = useState<'panel' | 'concern'>('panel');
  const [panel, setPanel] = useState('blood');
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState<'all' | 'flag'>('all');
  const detail = useApi<any>(mode === 'panel' ? `/vault/panel/${panel}` : null, [panel, mode]);

  if (panels.error) return <ErrorState message={panels.error} onRetry={panels.reload} />;
  if (!panels.data) return <Loading what="Opening your biomarkers…" />;
  const counts = panels.data.reduce(
    (a, x) => ({ o: a.o + x.counts.optimal, r: a.r + x.counts.in_range, x: a.x + x.counts.out_of_range, n: a.n + x.markers }),
    { o: 0, r: 0, x: 0, n: 0 },
  );
  const filt = (m: any) =>
    (!q || m.name.toLowerCase().includes(q.toLowerCase())) && (filter === 'all' || ['out_of_range', 'variant', 'detected'].includes(m.status));

  return (
    <>
      <Card>
        <T v="label">Across {panels.data.filter((x) => x.markers).length} panels</T>
        <Row gap={space[4]}>
          <Count n={counts.n} label="Markers" />
          <Count n={counts.o} label="Optimal" color={p.success} />
          <Count n={counts.r} label="In range" color={p.warn} />
          <Count n={counts.x} label="Out of range" color={p.danger} />
        </Row>
        <StackBar parts={[{ value: counts.o, color: p.success }, { value: counts.r, color: p.warn }, { value: counts.x, color: p.danger }]} />
      </Card>

      <Row gap={space[2]}>
        <Card style={{ flex: 1 }} onPress={() => router.push('/notes')} testID="notes-link">
          <T v="label">Clinician notes</T>
          <T v="small">Top 3 priorities + TL;DR</T>
        </Card>
        <Card style={{ flex: 1 }} onPress={() => router.push('/browse')} testID="browse-link">
          <T v="label">Browse</T>
          <T v="small">By health category</T>
        </Card>
      </Row>

      {nudges.data?.length ? (
        <Card tone="copper">
          <T v="label">Retest due</T>
          {nudges.data.slice(0, 2).map((n: any) => (
            <View key={n.panel} style={{ gap: 4 }}>
              <T v="body">{n.text}</T>
              <Row style={{ flexWrap: 'wrap' }}>
                {n.markers.slice(0, 5).map((m: any) => (
                  <Chip key={m.id} label={m.name} fg={p.danger} bg={p.dangerSoft} />
                ))}
              </Row>
              {n.prep?.map((t: string) => (
                <T key={t} v="small">
                  · {t}
                </T>
              ))}
            </View>
          ))}
        </Card>
      ) : null}

      {risks.data ? (
        <Section title="Risk map" action="Details" onAction={() => router.push('/risks' as any)}>
          <Card>
            {risks.data.slice(0, 6).map((r: any, i: number) => (
              <View key={r.condition}>
                {i ? <Divider /> : null}
                <Row style={{ paddingVertical: 8 }}>
                  <T v="body" style={{ flex: 1 }}>
                    {r.condition}
                  </T>
                  <Chip
                    label={r.level === 'unknown' ? 'Not enough data' : r.level[0].toUpperCase() + r.level.slice(1)}
                    fg={r.level === 'high' ? p.danger : r.level === 'moderate' ? p.warn : r.level === 'low' ? p.success : p.muted}
                    bg={r.level === 'high' ? p.dangerSoft : r.level === 'moderate' ? p.warnSoft : r.level === 'low' ? p.successSoft : p.surfaceAlt}
                  />
                </Row>
              </View>
            ))}
            <T v="small">Levels come from which of your markers are outside range, weighted by how strongly each predicts the condition. Not a diagnosis.</T>
          </Card>
        </Section>
      ) : null}

      <Segmented
        options={[
          { key: 'panel', label: 'By panel' },
          { key: 'concern', label: 'By health concern' },
        ]}
        value={mode}
        onChange={setMode}
      />
      <Row>
        <View style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: p.surface, borderRadius: radius.md, borderWidth: 1, borderColor: p.border, paddingHorizontal: 12 }}>
          <Icon name="magnifyingglass" size={14} color={p.muted} />
          <TextInput value={q} onChangeText={setQ} placeholder="Search biomarkers" placeholderTextColor={p.faint} style={{ flex: 1, paddingVertical: 10, color: p.text, fontSize: 15 }} accessibilityLabel="Search biomarkers" />
        </View>
        <Pill on={filter === 'flag'} label="Flagged" onPress={() => setFilter(filter === 'flag' ? 'all' : 'flag')} />
      </Row>

      {mode === 'panel' ? (
        <>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {panels.data.map((x: any) => (
              <Pill key={x.panel} on={panel === x.panel} label={`${shortPanel(x.title)}${x.markers ? ` · ${x.markers}` : ''}`} onPress={() => setPanel(x.panel)} />
            ))}
          </ScrollView>
          {detail.error ? <ErrorState message={detail.error} onRetry={detail.reload} /> : null}
          {detail.data ? (
            detail.data.items.length ? (
              <Card style={{ paddingVertical: 4 }}>
                <T v="small">
                  {detail.data.title} · latest {fmtDate(detail.data.latest_day, true)} · {detail.data.reports.length} report{detail.data.reports.length === 1 ? '' : 's'}
                </T>
                {detail.data.items.filter(filt).map((m: any, i: number) => (
                  <MarkerRow key={m.id} m={m} first={i === 0} />
                ))}
              </Card>
            ) : (
              <Empty
                title={`No ${detail.data.title.toLowerCase()} yet`}
                body="Upload the PDF your lab or imaging centre sent you. Telomy reads it, you check the values, and it lands here with its date."
                actions={[{ title: 'Upload a report', onPress: () => router.push('/upload') }]}
              />
            )
          ) : (
            <Loading what="Loading panel…" />
          )}
        </>
      ) : concerns.data ? (
        concerns.data.map((c: any) => {
          const items = c.markers.filter(filt);
          if (!items.length) return null;
          return (
            <Card key={c.concern} style={{ paddingVertical: 6 }}>
              <Row style={{ paddingTop: 6 }}>
                <T v="h3" style={{ flex: 1 }}>
                  {c.concern}
                </T>
                {c.flagged ? <Chip label={`${c.flagged} flagged`} fg={p.danger} bg={p.dangerSoft} /> : <Chip label="All clear" fg={p.success} bg={p.successSoft} />}
              </Row>
              {items.map((m: any, i: number) => (
                <MarkerRow key={m.id} m={m} first={i === 0} />
              ))}
            </Card>
          );
        })
      ) : (
        <Loading what="Grouping by concern…" />
      )}

      {derived.data?.length ? (
        <Section title="Calculated from your results">
          <Card style={{ paddingVertical: 4 }}>
            {derived.data.map((d: any, i: number) => (
              <View key={d.id}>
                {i ? <Divider /> : null}
                <View style={{ paddingVertical: 10, gap: 2 }}>
                  <Row>
                    <T v="body" style={{ flex: 1, fontWeight: '500' }}>
                      {d.name}
                    </T>
                    <T v="num" style={{ fontSize: 17 }}>
                      {d.value}
                      <T v="small"> {d.unit}</T>
                    </T>
                  </Row>
                  <T v="small">{d.formula} · inputs from {fmtDate(d.as_of, true)}</T>
                  {d.interpretation ? <T v="small">{d.interpretation}</T> : null}
                </View>
              </View>
            ))}
          </Card>
        </Section>
      ) : null}
    </>
  );
}

function shortPanel(t: string) {
  const x = t.split(' (')[0].replace('Standard ', '').replace('Advanced blood', 'Advanced');
  return x[0].toUpperCase() + x.slice(1);
}

function Count({ n, label, color }: { n: number; label: string; color?: string }) {
  return (
    <View style={{ flex: 1 }}>
      <T v="num" color={color}>
        {n}
      </T>
      <T v="small">{label}</T>
    </View>
  );
}

function MarkerRow({ m, first }: { m: any; first?: boolean }) {
  const p = usePalette();
  const c = statusColor(p, m.status);
  return (
    <Pressable
      onPress={() => router.push(`/marker/${m.id}`)}
      testID={`marker-${m.id}`}
      accessibilityRole="button"
      accessibilityLabel={`${m.name} ${m.value} ${m.unit ?? ''}`}
      style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: space[3], paddingVertical: 12, borderTopWidth: first ? 0 : 1, borderTopColor: p.border, opacity: pressed ? 0.7 : 1 })}>
      <View style={{ flex: 1, gap: 4 }}>
        <T v="body" style={{ fontWeight: '500' }}>
          {m.name}
        </T>
        <Row>
          <StatusChip status={m.status} />
          {m.n > 1 ? <T v="small">{m.n} results</T> : null}
          {m.variant_note ? <T v="small" numberOfLines={1}>{m.variant_note}</T> : null}
        </Row>
      </View>
      {m.spark?.length > 1 ? <Sparkline data={m.spark} width={56} height={22} /> : null}
      <T v="num" style={{ fontSize: 17, textAlign: 'right', minWidth: 70 }} color={c.fg}>
        {typeof m.value === 'number' ? m.value : String(m.value)}
        <T v="small"> {m.unit}</T>
      </T>
    </Pressable>
  );
}

function Insights() {
  const { data, error, reload } = useApi<any[]>('/insights');
  const [kind, setKind] = useState('all');
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading what="Reading insights…" />;
  const kinds = ['all', 'cross_panel', 'event_effect', 'lab_trend', 'signal_correlation', 'lab_wearable'];
  const label: Record<string, string> = { all: 'All', cross_panel: 'Across reports', event_effect: 'From your log', lab_trend: 'Lab trends', signal_correlation: 'Wearable', lab_wearable: 'Lab × wearable' };
  const shown = data.filter((i) => kind === 'all' || i.kind === kind);
  return (
    <>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
        {kinds.map((k) => (
          <Pill key={k} on={kind === k} label={`${label[k]} · ${k === 'all' ? data.length : data.filter((i) => i.kind === k).length}`} onPress={() => setKind(k)} />
        ))}
      </ScrollView>
      {shown.map((i) => (
        <InsightCard key={i.id} i={i} />
      ))}
    </>
  );
}

function Signals() {
  const p = usePalette();
  const { data, error, reload } = useApi<any[]>('/signals');
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading what="Loading signals…" />;
  return (
    <Card style={{ paddingVertical: 4 }}>
      {data.map((s, i) => (
        <Pressable key={s.id} onPress={() => router.push(`/signal/${s.id}`)} testID={`signal-${s.id}`} style={{ flexDirection: 'row', alignItems: 'center', gap: space[3], paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
          <View style={{ flex: 1 }}>
            <T v="body" style={{ fontWeight: '500' }}>
              {s.label}
            </T>
            <T v="small">{s.value == null ? 'No data yet' : `${s.source} · ${ago(s.day)} · n = ${s.n}`}</T>
          </View>
          <Sparkline data={s.spark ?? []} width={64} height={22} />
          <T v="num" style={{ fontSize: 17, minWidth: 72, textAlign: 'right' }}>
            {s.value ?? '—'}
            <T v="small"> {s.unit}</T>
          </T>
        </Pressable>
      ))}
    </Card>
  );
}

const TL_ICON: Record<string, any> = {
  alcohol: 'wineglass', late_meal: 'moon', sauna: 'flame', workout_hard: 'figure.run', caffeine_late: 'cup.and.saucer', travel: 'airplane',
  supplement: 'pills', medication: 'pills', mood: 'face.smiling', symptom: 'bandage', stress: 'bolt', lab: 'testtube.2', meal: 'fork.knife',
  imaging: 'waveform.path.ecg', hbot: 'circle.hexagongrid', life: 'house', note: 'note.text',
};

function Timeline() {
  const p = usePalette();
  const [days, setDays] = useState(14);
  const { data, error, reload } = useApi<any[]>(`/vault/timeline?start=${shiftDays(-days)}`, [days]);
  const grouped = useMemo(() => {
    const g: Record<string, any[]> = {};
    (data ?? []).forEach((x) => {
      (g[x.ts.slice(0, 10)] ??= []).push(x);
    });
    return Object.entries(g);
  }, [data]);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <Segmented
        options={[
          { key: '7', label: '7 d' },
          { key: '14', label: '14 d' },
          { key: '30', label: '30 d' },
          { key: '120', label: '120 d' },
        ]}
        value={String(days) as any}
        onChange={(k) => setDays(Number(k))}
      />
      {!data ? <Loading what="Building your timeline…" /> : null}
      {grouped.map(([day, items]) => (
        <View key={day} style={{ gap: 6 }}>
          <T v="label">{new Date(day + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })}</T>
          <Card style={{ paddingVertical: 4 }}>
            {items.map((x, i) => (
              <Pressable
                key={x.type + x.id}
                onPress={() => (x.type === 'report' ? router.push(`/report/${x.id}`) : x.type === 'imaging' ? router.push('/imaging') : undefined)}
                style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <Icon name={TL_ICON[x.kind] ?? 'circle'} size={16} color={x.type === 'report' || x.type === 'imaging' ? p.teal : p.copper} />
                <View style={{ flex: 1 }}>
                  <T v="body">{x.label}</T>
                  <T v="small">
                    {x.kind_label ?? (x.type === 'report' ? 'Lab report' : x.type === 'meal' ? `Meal · score ${x.score ?? '—'}` : x.type)}
                    {x.type === 'event' || x.type === 'meal' ? ` · ${x.ts.slice(11, 16)}` : ''}
                  </T>
                </View>
              </Pressable>
            ))}
          </Card>
        </View>
      ))}
    </>
  );
}

function shiftDays(n: number) {
  const d = new Date('2026-10-06T12:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function Reports() {
  const p = usePalette();
  const { data, error, reload } = useApi<any[]>('/reports');
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading what="Loading reports…" />;
  return (
    <>
      <Card style={{ paddingVertical: 4 }}>
        {data.map((r, i) => (
          <View key={r.id}>
            {i ? <Divider /> : null}
            <ListRow
              icon={['ct', 'mri'].includes(r.panel) ? 'waveform.path.ecg' : r.panel === 'bodycomp' ? 'figure.stand' : r.panel === 'fitness' ? 'figure.run' : 'testtube.2'}
              title={r.title}
              subtitle={`${r.panel_title} · ${fmtDate(r.collected_on, true)} · ${r.markers} markers${r.is_test_data ? ' · test data' : ''}`}
              onPress={() => router.push(`/report/${r.id}`)}
            />
          </View>
        ))}
      </Card>
      <ListRow icon="waveform.path.ecg" title="Imaging viewer" subtitle="Carotid ultrasound, DEXA scans" onPress={() => router.push('/imaging')} />
      <T v="small" color={p.muted}>
        Every report stays as its own dated record. Uploading a new one never overwrites an earlier one.
      </T>
    </>
  );
}
