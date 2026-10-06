import { router, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { Alert, Pressable } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { statusColor, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ErrorState, Loading, Row, Screen, StatusChip, T } from '@/ui/core';

export default function Report() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { data: r, error, reload } = useApi<any>(`/reports/${id}`, [id]);
  if (error) return <Screen edges={[]}><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!r) return <Screen edges={[]}><Loading what="Opening report…" /></Screen>;
  return (
    <Screen edges={[]}>
      <T v="h1">{r.title}</T>
      <Row style={{ flexWrap: 'wrap' }}>
        <Chip label={fmtDate(r.collected_on, true)} />
        <Chip label={`${r.results.length} markers`} />
        {r.is_test_data ? <Chip label="Test data" fg={p.copper} bg={p.copperSoft} /> : null}
      </Row>
      <T v="small">{r.source} · {r.filename}</T>
      <Card style={{ paddingVertical: 4 }}>
        {r.results.map((x: any, i: number) => (
          <Pressable key={x.id} onPress={() => router.push(`/marker/${x.marker_id}`)} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border, gap: 4 }}>
            <Row>
              <T v="body" style={{ flex: 1 }}>{x.name}</T>
              <T v="num" style={{ fontSize: 16 }} color={statusColor(p, x.status).fg}>
                {x.value_num ?? x.value_text} <T v="small">{x.unit}</T>
              </T>
            </Row>
            <Row>
              <StatusChip status={x.status} />
              <T v="small">Lab range {x.ref_text || '—'}</T>
            </Row>
          </Pressable>
        ))}
      </Card>
      <Button
        kind="danger"
        title="Delete this report"
        onPress={() =>
          Alert.alert('Delete this report?', 'This is permanent. Undo will not bring it back.', [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Delete', style: 'destructive', onPress: async () => { await api(`/reports/${id}`, { method: 'DELETE' }); router.back(); } },
          ])
        }
      />
    </Screen>
  );
}
