import { router, Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { statusColor, usePalette } from '@/lib/theme';
import { Sparkline } from '@/ui/charts';
import { Card, Chip, Divider, ListRow, Loading, Row, Screen, Section, StatusChip, T } from '@/ui/core';

export default function Browse() {
  const p = usePalette();
  const { name } = useLocalSearchParams<{ name?: string }>();
  const list = useApi<any[]>(name ? null : '/categories');
  const one = useApi<any>(name ? `/categories/${encodeURIComponent(name)}` : null, [name]);
  if (!name) {
    return (
      <Screen edges={[]}>
        {!list.data ? <Loading what="Loading categories…" /> : null}
        <Card style={{ paddingVertical: 2 }}>
          {list.data?.map((c, i) => (
            <View key={c.name}>
              {i ? <Divider /> : null}
              <ListRow
                title={c.name}
                subtitle={c.empty ? 'No data yet' : `${c.signals} signals · ${c.markers} markers`}
                right={c.flagged ? <Chip label={`${c.flagged} flagged`} fg={p.danger} bg={p.dangerSoft} /> : undefined}
                onPress={() => router.push(`/browse?name=${encodeURIComponent(c.name)}`)}
              />
            </View>
          ))}
        </Card>
      </Screen>
    );
  }
  const d = one.data;
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: name }} />
      {!d ? <Loading what="Loading…" /> : null}
      {d?.signals.length ? (
        <Section title="From your devices">
          <Card style={{ paddingVertical: 4 }}>
            {d.signals.map((s: any, i: number) => (
              <Pressable key={s.id} onPress={() => router.push(`/signal/${s.id}`)} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                <T v="body" style={{ flex: 1 }}>{s.label}</T>
                <Sparkline data={s.spark} width={60} height={20} />
                <T v="num" style={{ fontSize: 16 }}>{s.value} <T v="small">{s.unit}</T></T>
              </Pressable>
            ))}
          </Card>
        </Section>
      ) : null}
      {d?.markers.length ? (
        <Section title="From your reports">
          <Card style={{ paddingVertical: 4 }}>
            {d.markers.map((m: any, i: number) => (
              <Pressable key={m.id} onPress={() => router.push(`/marker/${m.id}`)} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border, gap: 4 }}>
                <Row><T v="body" style={{ flex: 1 }}>{m.name}</T><T v="num" style={{ fontSize: 16 }} color={statusColor(p, m.status).fg}>{String(m.value)} <T v="small">{m.unit}</T></T></Row>
                <StatusChip status={m.status} />
              </Pressable>
            ))}
          </Card>
        </Section>
      ) : null}
      {d?.no_data.length ? (
        <Section title="No data yet">
          <Card><T v="small">{d.no_data.join(' · ')}</T></Card>
        </Section>
      ) : null}
    </Screen>
  );
}
