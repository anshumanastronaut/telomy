import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, Loading, Row, Screen, Section, T } from '@/ui/core';

const SCOPES = ['sleep', 'activity', 'labs', 'insights', 'emergency'];

export default function Family() {
  const p = usePalette();
  const { data, reload } = useApi<any>('/shares');
  const [name, setName] = useState('');
  const [rel, setRel] = useState('Parent');
  const [scopes, setScopes] = useState<string[]>(['sleep']);
  const [days, setDays] = useState(30);
  return (
    <Screen edges={[]}>
      <T v="body" color={p.muted}>Share a summary, not your whole Vault. Every share has a scope and an expiry, and you can see each time someone looks.</T>
      <Section title="Invite someone">
        <Card>
          <TextInput value={name} onChangeText={setName} placeholder="Name" placeholderTextColor={p.faint} style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, fontFamily: 'Inter_400Regular' }} />
          <Row style={{ flexWrap: 'wrap' }}>
            {['Parent', 'Spouse', 'Sibling', 'Child', 'Coach'].map((r) => (
              <Pressable key={r} onPress={() => setRel(r)}><Chip label={r} fg={rel === r ? '#fff' : p.text} bg={rel === r ? p.teal : p.surfaceAlt} /></Pressable>
            ))}
          </Row>
          <T v="label">What they can see</T>
          <Row style={{ flexWrap: 'wrap' }}>
            {SCOPES.map((s) => (
              <Pressable key={s} onPress={() => setScopes(scopes.includes(s) ? scopes.filter((x) => x !== s) : [...scopes, s])}>
                <Chip label={s} fg={scopes.includes(s) ? '#fff' : p.text} bg={scopes.includes(s) ? p.teal : p.surfaceAlt} />
              </Pressable>
            ))}
          </Row>
          <T v="label">For</T>
          <Row>
            {[7, 30, 90].map((d) => (
              <Pressable key={d} onPress={() => setDays(d)}><Chip label={`${d} days`} fg={days === d ? '#fff' : p.text} bg={days === d ? p.teal : p.surfaceAlt} /></Pressable>
            ))}
          </Row>
          <Button title="Share" disabled={!name.trim() || !scopes.length} onPress={async () => { await api('/shares', { body: { name, relation: rel, scopes, days } }); setName(''); reload(); }} />
        </Card>
      </Section>
      {!data ? <Loading what="Loading…" /> : null}
      <Section title="Active shares">
        {data?.shares.map((s: any) => (
          <Card key={s.id}>
            <Row>
              <T v="h3" style={{ flex: 1 }}>{s.name} · {s.relation}</T>
              <Chip label={s.status} fg={s.status === 'active' ? p.success : p.muted} bg={s.status === 'active' ? p.successSoft : p.surfaceAlt} />
            </Row>
            <T v="small">Sees {s.scopes.join(', ')} · until {fmtDate(s.expires_on, true)}</T>
            {s.status === 'active' ? <Button kind="danger" title="Revoke now" onPress={async () => { await api(`/shares/${s.id}/revoke`, { method: 'POST' }); reload(); }} /> : null}
          </Card>
        ))}
      </Section>
      <Section title="Access log">
        <Card style={{ paddingVertical: 4 }}>
          {data?.log.map((l: any, i: number) => (
            <View key={l.id}>{i ? <Divider /> : null}<Row style={{ paddingVertical: 8 }}><T v="body" style={{ flex: 1 }}>{l.who} · {l.what}</T><T v="small">{fmtDate(l.ts)}</T></Row></View>
          ))}
        </Card>
      </Section>
    </Screen>
  );
}
