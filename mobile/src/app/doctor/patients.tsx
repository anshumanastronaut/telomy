import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Card, ErrorState, Icon, Loading, Row, Screen, T } from '@/ui/core';

export default function Patients() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<any[]>('/mgmt/doctor/patients');
  const [q, setQ] = useState('');
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  const list = (data ?? []).filter((x) => !q || (x.name || '').toLowerCase().includes(q.toLowerCase()));
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Patients</T>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: p.surface, borderRadius: radius.md, paddingHorizontal: 12 }}>
        <Icon name="magnifyingglass" size={14} color={p.muted} />
        <TextInput value={q} onChangeText={setQ} placeholder="Search patients" placeholderTextColor={p.faint} style={{ flex: 1, paddingVertical: 10, color: p.text, fontFamily: 'Inter_400Regular' }} />
      </View>
      <T v="small">Your panel. {list.length} patient{list.length === 1 ? '' : 's'}.</T>
      {!data ? <Loading what="Loading panel…" /> : null}
      <View style={{ gap: space[3] }}>
        {list.map((x) => (
          <Pressable key={x.id} onPress={() => router.push(`/patient/${x.id}` as any)} accessibilityRole="button">
            <Card>
              <Row>
                <View style={{ flex: 1 }}>
                  <T v="h3">{x.name || `#${x.id}`}</T>
                  <T v="small">{[x.age ? `${Math.round(x.age)}y` : null, x.sex, x.city].filter(Boolean).join(' · ') || '—'}</T>
                </View>
                <Icon name="chevron.right" size={16} color={p.faint} />
              </Row>
            </Card>
          </Pressable>
        ))}
        {data && !list.length ? <Card><T v="small">No patients on your panel yet.</T></Card> : null}
      </View>
    </Screen>
  );
}
