// Log any event (meal, supplement, caffeine, alcohol, smoking, custom…) with its own time. During a recording it goes
// into the session file; it always goes into the on-phone event log shown on Today's timeline.
import * as Haptics from 'expo-haptics';
import { router, Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api } from '@/lib/api';
import { Band } from '@/lib/band';
import { EVENT_KINDS, kindOf, localIso } from '@/lib/events';
import { radius, space, usePalette } from '@/lib/theme';
import { fmtClock } from '@/lib/wellness';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

const AGO = [{ m: 0, l: 'Now' }, { m: 15, l: '15 min' }, { m: 30, l: '30 min' }, { m: 60, l: '1 h' }, { m: 120, l: '2 h' },
  { m: 180, l: '3 h' }, { m: 360, l: '6 h' }, { m: 720, l: '12 h' }, { m: 1440, l: '24 h' }];

export default function LogEvent() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [kind, setKind] = useState('meal');
  const [label, setLabel] = useState('');
  const [note, setNote] = useState('');
  const [ago, setAgo] = useState(0);
  const [today, setToday] = useState<any[]>([]);
  const k = kindOf(kind);
  const capturing = Band.captureId();
  const load = () => Band.wellnessRead('events', 1).then(setToday).catch(() => {});
  useEffect(() => { load(); }, []);

  function save() {
    const t = Date.now() / 1000 - ago * 60;
    const text = (kind === 'custom' ? label.trim() : label.trim() || k.label) || 'Event';
    const r = Band.addUserEvent({ kind, label: text, note: note.trim() || undefined, t });
    // Also sync to the backend Vault so it shows on the longitudinal timeline (not only the on-phone log). The ts
    // is the device-LOCAL wall-clock, so it lands at the time the user picked regardless of the server's timezone.
    api('/events', { body: { kind, label: text, ts: localIso(t), data: note.trim() ? { note: note.trim() } : undefined }, queue: true }).catch(() => {});
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    show(r.captureId ? `Added to your recording at ${fmtClock(t)}` : `Logged at ${fmtClock(t)}`, 'success');
    setLabel(''); setNote(''); setAgo(0); load();
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Log an event' }} />
        {capturing ? (
          <Card tone="teal"><Row><Icon name="record.circle" color={p.danger} size={16} /><T v="small" style={{ flex: 1 }}>Recording in progress: this event will be added to the session timeline.</T></Row></Card>
        ) : null}
        <Section title="What happened">
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space[2] }}>
            {EVENT_KINDS.map((x) => {
              const on = x.k === kind;
              return (
                <Pressable key={x.k} onPress={() => { Haptics.selectionAsync(); setKind(x.k); }} accessibilityRole="radio" accessibilityState={{ selected: on }}
                  style={({ pressed }) => ({ width: '31%', height: 84, alignItems: 'center', justifyContent: 'center', gap: 6, paddingHorizontal: 4, borderRadius: radius.lg,
                    backgroundColor: on ? x.color + '26' : p.surface, borderWidth: 1.5, borderColor: on ? x.color : p.border, transform: [{ scale: pressed ? 0.96 : 1 }] })}>
                  <Icon name={x.icon} size={20} color={x.color} />
                  <T v="small" numberOfLines={2} color={on ? p.text : p.muted} style={{ fontWeight: '600', textAlign: 'center', lineHeight: 14 }}>{x.label}</T>
                </Pressable>
              );
            })}
          </View>
        </Section>
        <Section title="Details">
          <Card style={{ gap: space[3] }}>
            <TextInput value={label} onChangeText={setLabel} placeholder={kind === 'custom' ? 'Name it (e.g. cold shower, argument, travel)' : k.hint}
              placeholderTextColor={p.faint} style={{ color: p.text, fontSize: 17, paddingVertical: 6 }} accessibilityLabel="Event name or amount" />
            <View style={{ height: 1, backgroundColor: p.border }} />
            <TextInput value={note} onChangeText={setNote} placeholder="Notes (optional): how you feel, brand, place…" placeholderTextColor={p.faint} multiline
              style={{ color: p.text, fontSize: 15, minHeight: 44 }} accessibilityLabel="Notes" />
          </Card>
        </Section>
        <Section title="When">
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space[2] }}>
            {AGO.map((a) => (
              <Pressable key={a.m} onPress={() => setAgo(a.m)} accessibilityRole="radio" accessibilityState={{ selected: ago === a.m }}
                style={{ paddingHorizontal: 14, paddingVertical: 9, borderRadius: radius.pill, backgroundColor: ago === a.m ? p.teal : p.surfaceAlt }}>
                <T v="small" color={ago === a.m ? p.onAccent : p.text} style={{ fontWeight: '600' }}>{a.l}</T>
              </Pressable>
            ))}
          </View>
          <T v="small">{fmtClock(Date.now() / 1000 - ago * 60)}</T>
        </Section>
        <Button title={`Log ${kind === 'custom' ? 'event' : k.label.toLowerCase()}`} icon="plus" onPress={save} disabled={kind === 'custom' && !label.trim()} />
        {today.length ? (
          <Section title="Today">
            <Card style={{ paddingVertical: 4 }}>
              {[...today].reverse().slice(0, 12).map((e, i) => {
                const x = kindOf(e.kind);
                return (
                  <Row key={i} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                    <View style={{ width: 30, height: 30, borderRadius: 15, alignItems: 'center', justifyContent: 'center', backgroundColor: x.color + '26' }}><Icon name={x.icon} size={14} color={x.color} /></View>
                    <View style={{ flex: 1 }}>
                      <T v="body">{e.label}</T>
                      {e.note ? <T v="small" numberOfLines={1}>{e.note}</T> : null}
                    </View>
                    <T v="small">{fmtClock(e.t)}{e.captureId ? ' · in recording' : ''}</T>
                  </Row>
                );
              })}
            </Card>
          </Section>
        ) : null}
        <Button kind="ghost" title="Done" onPress={() => router.back()} />
      </Screen>
      {toast}
    </View>
  );
}
