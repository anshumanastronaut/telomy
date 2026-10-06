import React from 'react';
import { Pressable, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Card, Divider, Icon, Loading, Row, Screen, T } from '@/ui/core';

export default function Memory() {
  const p = usePalette();
  const { data, reload } = useApi<any[]>('/memories');
  return (
    <Screen edges={[]}>
      <T v="body" color={p.muted}>Facts Sinc has picked up from your conversations. Delete any you don't want it to use.</T>
      {!data ? <Loading what="Loading…" /> : null}
      <Card style={{ paddingVertical: 4 }}>
        {data?.map((m, i) => (
          <View key={m.id}>
            {i ? <Divider /> : null}
            <Row style={{ paddingVertical: 10 }}>
              <View style={{ flex: 1 }}><T v="body">{m.fact}</T><T v="small">{m.source} · {fmtDate(m.ts)}</T></View>
              <Pressable onPress={async () => { await api(`/memories/${m.id}`, { method: 'DELETE' }); reload(); }} hitSlop={10} accessibilityLabel={`Forget ${m.fact}`}>
                <Icon name="trash" color={p.danger} size={16} />
              </Pressable>
            </Row>
          </View>
        ))}
        {data && !data.length ? <T v="small">Nothing yet.</T> : null}
      </Card>
    </Screen>
  );
}
