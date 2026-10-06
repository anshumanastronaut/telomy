import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Card, Divider, Empty, Icon, Loading, Row, Screen, T } from '@/ui/core';

const ICON: Record<string, any> = { retest: 'testtube.2', review: 'stethoscope', insight: 'sparkle', appointment: 'calendar', medication: 'pills' };

export default function Notifications() {
  const p = usePalette();
  const { data, reload } = useApi<any[]>('/notifications');
  if (!data) return <Screen edges={[]}><Loading what="Loading…" /></Screen>;
  if (!data.length) return <Screen edges={[]}><Empty title="You're up to date" body="Retest reminders, clinician sign-offs and new patterns will show here." /></Screen>;
  return (
    <Screen edges={[]} onRefresh={reload}>
      <Card style={{ paddingVertical: 2 }}>
        {data.map((n, i) => (
          <View key={n.key + i}>
            {i ? <Divider /> : null}
            <Pressable onPress={async () => { await api('/notifications/read', { body: [n.key] }); router.push(n.route); }} style={{ flexDirection: 'row', gap: 12, paddingVertical: 12, alignItems: 'flex-start' }}>
              <Icon name={ICON[n.kind] ?? 'bell'} color={n.read ? p.faint : p.teal} />
              <View style={{ flex: 1, gap: 2 }}>
                <T v="body" style={{ fontWeight: n.read ? '400' : '600' }}>{n.title}</T>
                <T v="small" numberOfLines={2}>{n.body}</T>
              </View>
              <T v="small">{n.ts ? fmtDate(n.ts) : ''}</T>
            </Pressable>
          </View>
        ))}
      </Card>
    </Screen>
  );
}
