import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function Meds() {
  const p = usePalette();
  const { data, reload } = useApi<any>('/meds');
  const [name, setName] = useState('');
  const [dose, setDose] = useState('');
  const [freq, setFreq] = useState('once daily');
  const { toast, show } = useToast();
  const times: Record<string, string[]> = { 'once daily': ['08:00'], 'twice daily': ['08:00', '20:00'], 'at night': ['22:00'] };
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        {data?.interactions?.length ? (
          <Card tone="copper">
            <T v="label">Check with your clinician</T>
            {data.interactions.map((i: any) => <T key={i.message} v="body">{i.between.join(' + ')}: {i.message}</T>)}
          </Card>
        ) : null}
        {!data ? <Loading what="Loading medications…" /> : null}
        {data?.items.map((m: any) => (
          <Card key={m.id} style={{ opacity: m.active ? 1 : 0.5 }}>
            <Row>
              <T v="h3" style={{ flex: 1 }}>{m.name} {m.dose}</T>
              <Chip label={`${m.adherence_30d}% taken · 30 d`} fg={m.adherence_30d >= 80 ? p.success : p.warn} bg={m.adherence_30d >= 80 ? p.successSoft : p.warnSoft} />
            </Row>
            <T v="small">{m.frequency} · {m.times.join(', ')} · {m.reason}{m.prescriber ? ` · ${m.prescriber}` : ''} · since {fmtDate(m.start_day, true)}</T>
            {m.active ? (
              <Row>
                <Button style={{ flex: 1 }} title={m.taken_today >= m.times.length ? 'Taken today' : `Mark taken (${m.taken_today}/${m.times.length})`} disabled={m.taken_today >= m.times.length} onPress={async () => { await api(`/meds/${m.id}/taken`, { method: 'POST' }); show('Logged.', 'success'); reload(); }} />
                <Button kind="secondary" title="Stop" onPress={async () => { await api(`/meds/${m.id}/stop`, { method: 'POST' }); reload(); }} />
              </Row>
            ) : <T v="small">Stopped</T>}
          </Card>
        ))}
        <Section title="Add a medication or supplement">
          <Card>
            <TextInput value={name} onChangeText={setName} placeholder="Name, e.g. Atorvastatin" placeholderTextColor={p.faint} style={inp(p)} />
            <TextInput value={dose} onChangeText={setDose} placeholder="Dose, e.g. 10 mg" placeholderTextColor={p.faint} style={inp(p)} />
            <Row>{Object.keys(times).map((f) => <Pressable key={f} onPress={() => setFreq(f)} accessibilityRole="radio" accessibilityState={{ selected: freq === f }}><Chip label={f} fg={freq === f ? '#fff' : p.text} bg={freq === f ? p.teal : p.surfaceAlt} /></Pressable>)}</Row>
            <Button title="Add" disabled={!name.trim()} onPress={async () => {
              const r = await api('/meds', { body: { name, dose, frequency: freq, times: times[freq] } });
              setName(''); setDose(''); reload();
              show(r.interactions?.length ? `Added. ${r.interactions.length} interaction(s) to review.` : 'Added.', r.interactions?.length ? 'alert' : 'success');
            }} />
          </Card>
        </Section>
      </Screen>
      {toast}
    </View>
  );
}

function inp(p: any) {
  return { borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, fontFamily: 'Inter_400Regular', backgroundColor: p.surface };
}
