import { router } from 'expo-router';
import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ErrorState, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function Work() {
  const p = usePalette();
  const org = staffOrg();
  const inbox = useApi<any>(`/mgmt/clinic/inbox?org=${encodeURIComponent(org)}`);
  const tasks = useApi<any[]>(`/mgmt/clinic/tasks?org=${encodeURIComponent(org)}`);
  const { toast, show } = useToast();
  const [newTask, setNewTask] = useState('');
  if (inbox.error) return <Screen><ErrorState message={inbox.error} onRetry={() => { inbox.reload(); tasks.reload(); }} /></Screen>;
  const care = inbox.data?.care_queue ?? [];
  const reload = () => { inbox.reload(); tasks.reload(); };

  async function done(id: number) {
    try { await api(`/mgmt/clinic/tasks/${id}/complete`, { method: 'POST' }); show('Done.', 'success'); tasks.reload(); }
    catch (e: any) { show(e.message, 'alert'); }
  }
  async function add() {
    if (!newTask.trim()) return;
    try { await api('/mgmt/clinic/tasks', { body: { org, text: newTask.trim(), priority: 2 } }); setNewTask(''); show('Task added.', 'success'); tasks.reload(); }
    catch (e: any) { show(e.message, 'alert'); }
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen onRefresh={reload} refreshing={inbox.loading}>
        <T v="h1">Work queue</T>
        {!inbox.data ? <Loading what="Loading…" /> : null}

        <Section title={`Care review · ${care.length}`}>
          <T v="small" color={p.faint} style={{ marginTop: -2, marginBottom: space[1] }}>Findings from your patients' own data, awaiting your sign-off. Tap to open the chart and act.</T>
          {care.length ? care.map((c: any) => (
            <Card key={`${c.patient_id}-${c.id}`} onPress={() => router.push(`/doctor/patient/${c.patient_id}` as any)} style={{ marginBottom: space[2] }}>
              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <T v="label" color={p.teal}>{c.patient}</T>
                <Chip label={`${Math.round((c.confidence ?? 0) * 100)}%`} fg={p.muted} bg={p.surfaceAlt} />
              </Row>
              <T v="body" style={{ marginTop: 4 }} numberOfLines={2}>{c.title}</T>
            </Card>
          )) : <Card><T v="small">Nothing awaiting review.</T></Card>}
        </Section>

        <Section title={`Open tasks · ${tasks.data?.length ?? 0}`}>
          <Card style={{ gap: space[2] }}>
            {(tasks.data ?? []).map((t: any) => (
              <Row key={t.id} style={{ alignItems: 'center' }}>
                <View style={{ flex: 1 }}><T v="body">{t.text}</T><T v="small">{['', 'Low', 'Normal', 'High'][t.priority] ?? ''}{t.due ? ` · due ${t.due}` : ''}</T></View>
                <Button kind="ghost" title="Done" onPress={() => done(t.id)} />
              </Row>
            ))}
            {tasks.data && !tasks.data.length ? <T v="small">Inbox zero.</T> : null}
            <Row style={{ alignItems: 'center', gap: 8 }}>
              <TextInput value={newTask} onChangeText={setNewTask} placeholder="New task" placeholderTextColor={p.faint}
                style={{ flex: 1, borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10, color: p.text, fontFamily: 'HankenGrotesk_400Regular' }} onSubmitEditing={add} />
              <Button kind="secondary" title="Add" disabled={!newTask.trim()} onPress={add} />
            </Row>
          </Card>
        </Section>
      </Screen>
      {toast}
    </View>
  );
}
