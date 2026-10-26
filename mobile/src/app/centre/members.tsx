// Centre members — the roster. Searchable, tappable to a member's record (contact, plan, membership, bookings,
// assigned doctor). Uses /mgmt/centre/members so each row's id opens its detail.
import { router } from 'expo-router';
import React from 'react';
import { TextInput, View } from 'react-native';

import { useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { radius, space, usePalette } from '@/lib/theme';
import { Card, Chip, ErrorState, Loading, Row, Screen, T } from '@/ui/core';

type Member = { id: number; name: string; status: string; joined_on?: string; fields?: { plan?: string } };

export default function Members() {
  const p = usePalette();
  const { data, error, reload, loading } = useApi<Member[]>(`/mgmt/centre/members?org=${encodeURIComponent(staffOrg())}`);
  const [q, setQ] = React.useState('');
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen><Loading what="Loading members…" /></Screen>;

  const rows = data.filter((m) => !q || m.name.toLowerCase().includes(q.toLowerCase()));
  const active = data.filter((m) => m.status === 'active').length;

  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <T v="h1">Members</T>
      <T v="small" color={p.muted}>{data.length} members · {active} active</T>
      <TextInput value={q} onChangeText={setQ} placeholder="Search members" placeholderTextColor={p.faint}
        style={{ marginTop: space[2], borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, fontFamily: 'HankenGrotesk_400Regular' }} />
      <View style={{ gap: space[2], marginTop: space[2] }}>
        {rows.map((m) => (
          <Card key={m.id} onPress={() => router.push(`/centre/member/${m.id}` as any)}>
            <Row>
              <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: p.tealSoft, alignItems: 'center', justifyContent: 'center' }}>
                <T v="h3" color={p.teal}>{m.name?.[0] ?? '·'}</T>
              </View>
              <View style={{ flex: 1 }}>
                <T v="h3" numberOfLines={1}>{m.name}</T>
                <T v="small" color={p.faint}>{m.joined_on ? `Joined ${m.joined_on}` : ''}</T>
              </View>
              {m.fields?.plan ? <Chip label={m.fields.plan} fg={p.teal} bg={p.tealSoft} /> : null}
              <Chip label={m.status} fg={m.status === 'active' ? p.teal : p.muted} bg={m.status === 'active' ? p.tealSoft : p.surfaceAlt} />
            </Row>
          </Card>
        ))}
        {!rows.length ? <T v="small" color={p.muted}>No members match "{q}".</T> : null}
      </View>
      <View style={{ height: space[6] }} />
    </Screen>
  );
}
