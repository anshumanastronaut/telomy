import { router, Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { ago, fmtDate, useApi } from '@/lib/api';
import { radius, statusColor, usePalette } from '@/lib/theme';
import { LineChart } from '@/ui/charts';
import { Card, Chip, Divider, ErrorState, Icon, Loading, Prov, Row, Screen, Section, StatusChip, T } from '@/ui/core';
import { InsightCard } from '@/ui/insight';

export default function Marker() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: m, error, reload } = useApi<any>(`/vault/marker/${id}`, [id]);
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!m) return <Screen edges={[]}><Loading what="Loading biomarker…" /></Screen>;
  const last = m.history[m.history.length - 1];
  const numeric = m.history.filter((h: any) => typeof h.value === 'number');
  const c = statusColor(p, last?.status);
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: m.name }} />
      <View style={{ gap: 4 }}>
        <Row style={{ flexWrap: 'wrap' }}>
          <Chip label={m.panel_title} />
          {m.evidence_grade ? <Chip label={`Evidence ${m.evidence_grade}`} fg={p.teal} bg={p.tealSoft} /> : null}
          {m.concerns.map((x: string) => <Chip key={x} label={x} />)}
        </Row>
        <T v="h1">{m.name}</T>
      </View>
      {last ? (
        <Card>
          <Row style={{ alignItems: 'baseline' }}>
            <T v="numLg" color={c.fg}>{typeof last.value === 'number' ? last.value : String(last.value)}</T>
            <T v="body" color={p.muted}> {m.unit}</T>
          </Row>
          <Row style={{ flexWrap: 'wrap' }}>
            <StatusChip status={last.status} />
            {m.zone ? <Chip label={m.zone.label} fg={statusColor(p, m.zone.status).fg} bg={statusColor(p, m.zone.status).bg} /> : null}
            {last.flag ? <Chip label={`Lab flag ${last.flag}`} /> : null}
          </Row>
          {m.variant_note ? <T v="small">{m.variant_note}</T> : null}
          <Prov source={`${last.source}${last.test_data && !/test/i.test(last.source ?? '') ? ' (test data)' : ''}`} when={`${fmtDate(last.day, true)} · ${ago(last.day)}`} confidence={m.confidence} />
        </Card>
      ) : null}

      {m.zone ? (
        <Section title="Where you sit">
          <Card style={{ gap: 0, paddingVertical: 6 }}>
            {m.zone.bands.map((b: any, i: number) => {
              const prev = i ? m.zone.bands[i - 1].upper : null;
              const range = prev == null ? `< ${b.upper}` : b.upper == null ? `≥ ${prev}` : `${prev} – ${b.upper}`;
              const on = b.label === m.zone.label;
              const bc = statusColor(p, b.status);
              return (
                <Row key={i} style={{ paddingVertical: 8, paddingHorizontal: 8, borderRadius: radius.sm, backgroundColor: on ? bc.bg : 'transparent' }}>
                  <T v="body" style={{ width: 96, fontVariant: ['tabular-nums'] }}>{range}</T>
                  <T v="body" style={{ flex: 1, fontWeight: on ? '700' : '400' }} color={on ? bc.fg : p.text}>{b.label}</T>
                  {on ? <Icon name="arrowtriangle.left.fill" size={10} color={bc.fg} /> : null}
                </Row>
              );
            })}
            <T v="small" style={{ paddingHorizontal: 8, paddingTop: 6 }}>Bands from clinical guidelines, personalised to your sex where they differ.</T>
          </Card>
        </Section>
      ) : null}

      {numeric.length ? (
        <Section title={`History · ${m.history.length} result${m.history.length === 1 ? '' : 's'}`}>
          <Card>
            <LineChart
              points={numeric.map((h: any) => ({ x: h.day, y: h.value }))}
              band={m.optimal?.[0] != null && m.optimal?.[1] != null ? m.optimal : null}
              refBand={last && (last.ref_low != null || last.ref_high != null) ? [last.ref_low, last.ref_high] : null}
              unit={m.unit}
              dots
              caption={`n = ${numeric.length} · teal band = optimal ${m.optimal?.[0] ?? ''}–${m.optimal?.[1] ?? ''}, grey = lab range`}
            />
          </Card>
        </Section>
      ) : null}

      {m.sinc_read ? (
        <Section title="Sinc's read">
          <Card tone="teal">
            <T v="body">{m.sinc_read}</T>
          </Card>
        </Section>
      ) : null}

      <Section title="Every result">
        <Card style={{ paddingVertical: 4 }}>
          {m.history
            .slice()
            .reverse()
            .map((h: any, i: number) => (
              <Pressable key={i} onPress={() => router.push(`/report/${h.report_id}`)} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border, gap: 2 }}>
                <Row>
                  <T v="body" style={{ flex: 1 }}>{fmtDate(h.day, true)}</T>
                  <T v="num" style={{ fontSize: 16 }} color={statusColor(p, h.status).fg}>{String(h.value)} <T v="small">{m.unit}</T></T>
                </Row>
                <T v="small">Lab range {h.ref_text || '—'} · {h.report_title}</T>
              </Pressable>
            ))}
        </Card>
      </Section>

      {m.what_changes?.length ? (
        <Section title="What could change this">
          <Card>
            {m.what_changes.map((w: string) => (
              <Row key={w} style={{ alignItems: 'flex-start' }}>
                <Icon name="arrow.right" size={12} color={p.teal} />
                <T v="body" style={{ flex: 1 }}>{w}</T>
              </Row>
            ))}
          </Card>
        </Section>
      ) : null}

      {m.retest_prep ? (
        <Card tone="copper">
          <T v="label">Before your next test</T>
          <T v="body">{m.retest_prep}</T>
        </Card>
      ) : null}

      {m.related?.length ? (
        <Section title="Connected patterns">
          {m.related.map((i: any) => <InsightCard key={i.id} i={i} compact />)}
        </Section>
      ) : null}
      <Divider />
      <T v="small">Optimal range: {m.optimal?.[0] ?? '—'} – {m.optimal?.[1] ?? '—'} {m.unit}{m.loinc ? ` · LOINC ${m.loinc}` : ''}</T>
    </Screen>
  );
}
