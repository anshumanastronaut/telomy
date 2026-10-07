import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { ErrorState, Icon, Loading, Screen, Segmented, T } from '@/ui/core';
import { PatientRow } from '@/ui/patient';

export default function Patients() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<any[]>('/doctor/patients');
  const [q, setQ] = useState('');
  const [f, setF] = useState<'all' | 'high' | 'cvd' | 'dm'>('all');
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  const list = (data ?? []).filter((x) => (!q || x.name.toLowerCase().includes(q.toLowerCase()))
    && (f === 'all' || (f === 'high' && x.priority >= 40) || (f === 'cvd' && (x.cvd ?? 0) >= 7.5) || (f === 'dm' && (x.diabetes ?? 0) >= 25)));
  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Patients</T>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: p.surface, borderRadius: radius.md, borderWidth: 1, borderColor: p.border, paddingHorizontal: 12 }}>
        <Icon name="magnifyingglass" size={14} color={p.muted} />
        <TextInput value={q} onChangeText={setQ} placeholder="Search patients" placeholderTextColor={p.faint} style={{ flex: 1, paddingVertical: 10, color: p.text, fontFamily: 'Inter_400Regular' }} />
      </View>
      <Segmented options={[{ key: 'all', label: 'All' }, { key: 'high', label: 'High' }, { key: 'cvd', label: 'CVD ≥ 7.5%' }, { key: 'dm', label: 'Diabetes' }]} value={f} onChange={setF} />
      <T v="small">Ranked by predicted risk and open flags. {list.length} shown.</T>
      {!data ? <Loading what="Loading panel…" /> : null}
      <View style={{ gap: space[3] }}>{list.map((x) => <PatientRow key={x.id} p={x} />)}</View>
    </Screen>
  );
}
