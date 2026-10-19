import { router } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Keyboard, KeyboardAvoidingView, Platform, Pressable, ScrollView, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, useApi } from '@/lib/api';
import { askOnDevice, SLM_INFO, useSlm } from '@/lib/slm';
import { radius, space, type, usePalette } from '@/lib/theme';
import { Button, Chip, ConfBar, Icon, Row, Spacer, StatusChip, T } from '@/ui/core';
import { Logo } from '@/ui/logo';
import { ThinkingOrb, type OrbState } from '@/sinc/ThinkingOrb';

type Msg = { role: 'user' | 'assistant'; content: string; meta?: any; id?: number; pending?: boolean };

const STARTERS = [
  'What correlations do you see across all my reports?',
  'Why is my HRV lower this month?',
  'What does my CT calcium score mean with my ApoB?',
  'What should I retest, and when?',
  'Should I take a statin for my ApoB?',
];

export default function Sinc() {
  const p = usePalette();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [chatId, setChatId] = useState<number | null>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [mode, setMode] = useState<'normal' | 'deep'>('normal');
  const scroll = useRef<ScrollView>(null);
  const chats = useApi<any[]>(history ? '/sinc/chats' : null, [history]);
  const health = useApi<any>('/health');
  const slm = useSlm();
  const [slmCard, setSlmCard] = useState(false);

  async function send(q: string) {
    if (!q.trim() || busy) return;
    setText('');
    setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', pending: true }]);
    setBusy(true);
    try {
      // On this iPhone first when chosen (quick answers only — deep research needs the citation library on the server).
      if (slm.on && mode === 'normal') {
        let streamed = '';
        const d = await askOnDevice(q, (t) => {
          streamed += t;
          const shown = streamed.replace(/<think>[\s\S]*?(<\/think>|$)/g, '');
          setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: shown, pending: !shown.trim() }]);
        });
        if ('answer' in d) {
          const r = await api('/sinc/log', { body: { question: q, answer: d.answer, chat_id: chatId, model: d.model } });
          setChatId(r.chat_id);
          setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: d.answer, id: r.message_id,
            meta: { ...r, notice: `${d.model}${d.tps ? ` · ${Math.round(d.tps)} tokens/s` : ''} · every number checked against your data` } }]);
          return;
        }
        setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: '', pending: true }]);
        const r = await api('/sinc/ask', { body: { question: q, chat_id: chatId, mode } });
        setChatId(r.chat_id);
        setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: r.answer, id: r.message_id,
          meta: { ...r, notice: `Answered from your Vault on your server — ${d.fallback}.` } }]);
        return;
      }
      const r = await api('/sinc/ask', { body: { question: q, chat_id: chatId, mode } });
      setChatId(r.chat_id);
      setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: r.answer, meta: r, id: r.message_id }]);
    } catch (e: any) {
      setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: `I couldn't answer just now. ${e.message}`, meta: { error: true } }]);
    } finally {
      setBusy(false);
      setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 100);
    }
  }

  async function openChat(id: number) {
    const ms = await api<any[]>(`/sinc/chats/${id}`);
    setChatId(id);
    setMsgs(ms.map((m) => ({ role: m.role, content: m.content, meta: m.meta, id: m.id })));
    setHistory(false);
  }

  async function draft(id: number) {
    const r = await api('/sinc/draft-for-clinician', { body: { message_id: id } });
    setNotice(r.message);
    setTimeout(() => setNotice(null), 4000);
  }

  const [kbd, setKbd] = useState(false);
  useEffect(() => {
    const a = Keyboard.addListener('keyboardWillShow', () => setKbd(true));
    const b = Keyboard.addListener('keyboardWillHide', () => setKbd(false));
    return () => { a.remove(); b.remove(); };
  }, []);

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: p.bg }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }} keyboardVerticalOffset={60}>
        <Row style={{ paddingHorizontal: space[4], paddingVertical: space[2] }}>
          {/* Sinc's face: the orb is always alive here — calm "shaping" at rest, "solving" while it works */}
          <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: p.surface, alignItems: 'center', justifyContent: 'center' }}>
            <ThinkingOrb state={busy ? 'solving' : 'shaping'} size={20} />
          </View>
          <View style={{ flex: 1 }}>
            <T v="h3">Sinc</T>
            <T v="small" numberOfLines={1}>{health.data?.sinc ? `Reads your Vault · ${health.data.sinc}` : 'Reads your Vault'}</T>
          </View>
          <Pressable onPress={() => setHistory(!history)} hitSlop={10} accessibilityLabel="Chat history">
            <Icon name="clock.arrow.circlepath" color={p.teal} />
          </Pressable>
          <Pressable
            onPress={() => {
              setMsgs([]);
              setChatId(null);
            }}
            hitSlop={10}
            accessibilityLabel="New chat">
            <Icon name="square.and.pencil" color={p.teal} />
          </Pressable>
        </Row>
        <ScrollView ref={scroll} contentContainerStyle={{ padding: space[4], gap: space[3], paddingBottom: 30 }} keyboardShouldPersistTaps="handled">
          {history ? (
            <View style={{ gap: 8 }}>
              <T v="label">History</T>
              {(chats.data ?? []).map((c) => (
                <Pressable key={c.id} onPress={() => openChat(c.id)} style={{ backgroundColor: p.surface, borderRadius: radius.lg, padding: space[3] }}>
                  <T v="body" style={{ fontWeight: '600' }}>{c.title}</T>
                  <T v="small" numberOfLines={2}>{c.preview}</T>
                </Pressable>
              ))}
              {chats.data && !chats.data.length ? <T v="small">No conversations yet.</T> : null}
            </View>
          ) : msgs.length === 0 ? (
            // First impression: Sinc's presence, two words, nothing else competing. Everything Sinc can do stays one
            // tap away — the starters become quiet chips, the "how it works" line sits small under the orb.
            <View style={{ alignItems: 'center', gap: space[5], paddingTop: space[8] }}>
              <ThinkingOrb state="listening" size={64} scale={2.6} />
              <View style={{ alignItems: 'center', gap: space[2] }}>
                <T v="display" style={{ textAlign: 'center' }}>Always watching.</T>
                <T v="small" color={p.muted} style={{ textAlign: 'center' }}>Sinc knows your whole Vault — and shows its evidence.</T>
              </View>
              {/* all starters kept, as one quiet scrollable row of small pills */}
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space[2], paddingHorizontal: space[1] }}>
                {STARTERS.map((s) => (
                  <Pressable key={s} onPress={() => send(s)} accessibilityRole="button"
                    style={({ pressed }) => ({ backgroundColor: p.surface, borderRadius: radius.pill, paddingHorizontal: space[3], paddingVertical: 6, opacity: pressed ? 0.7 : 1 })}>
                    <T v="small" color={p.muted} style={{ fontSize: type.caption - 1 }} numberOfLines={1}>{s}</T>
                  </Pressable>
                ))}
              </ScrollView>
            </View>
          ) : (
            msgs.map((m, i) => <Bubble key={i} m={m} onDraft={draft} />)
          )}
        </ScrollView>
        <Row style={{ paddingHorizontal: space[4], paddingBottom: 6 }}>
          {(['normal', 'deep'] as const).map((m) => (
            <Pressable key={m} onPress={() => setMode(m)} accessibilityRole="tab" accessibilityState={{ selected: mode === m }} testID={`mode-${m}`}>
              <Chip label={m === 'normal' ? 'Quick answer' : 'Deep research · with citations'} fg={mode === m ? (p.isDark ? p.bg : p.onAccent) : p.text} bg={mode === m ? p.teal : p.surfaceAlt} icon={m === 'deep' ? 'books.vertical' : 'bolt'} />
            </Pressable>
          ))}
          {slm.available ? (
            <Pressable onPress={() => (slm.ready ? slm.setOn(!slm.on) : setSlmCard(!slmCard))} accessibilityRole="switch"
              accessibilityState={{ checked: slm.on }} testID="mode-device">
              <Chip label={slm.on ? 'On this iPhone' : 'On-device'} fg={slm.on ? (p.isDark ? p.bg : p.onAccent) : p.text} bg={slm.on ? p.copper : p.surfaceAlt} icon="iphone" />
            </Pressable>
          ) : null}
        </Row>
        {slmCard && !slm.ready ? (
          <View style={{ marginHorizontal: space[4], marginBottom: 6, padding: 12, gap: 8, borderRadius: radius.md, backgroundColor: p.surface }}>
            <T v="body" style={{ fontWeight: '600' }}>Sinc on this iPhone</T>
            <T v="small">{SLM_INFO.label} ({SLM_INFO.note}) answers quick questions without your question leaving the phone. Every number it writes is checked against your data; if one doesn't match, your server answers instead. One-time download about {(SLM_INFO.mb / 1000).toFixed(1)} GB — use Wi-Fi.</T>
            {slm.error ? <T v="small" color={p.warn}>{slm.error}</T> : null}
            <Button kind="secondary" icon="arrow.down.circle" disabled={slm.progress != null}
              title={slm.progress != null ? `Downloading… ${Math.round(slm.progress * 100)}%` : 'Download the model'}
              onPress={async () => { await slm.download(); slm.setOn(true); }} />
          </View>
        ) : null}
        {notice ? (
          <View style={{ marginHorizontal: space[4], marginBottom: 6, padding: 12, borderRadius: radius.md, backgroundColor: p.successSoft }}>
            <T v="small" color={p.success}>{notice}</T>
          </View>
        ) : null}
        {/* composer floats above the glass tab bar; drops to the keyboard when typing */}
        <Row style={{ marginHorizontal: space[3], marginBottom: kbd ? 8 : 98, padding: 6, paddingLeft: 4, borderRadius: 28, backgroundColor: p.surface }}>
          <TextInput
            value={text}
            onChangeText={setText}
            placeholder="Ask about your data"
            placeholderTextColor={p.faint}
            multiline
            style={{ flex: 1, minHeight: 40, maxHeight: 120, color: p.text, fontSize: 15, paddingHorizontal: 12, paddingVertical: 10 }}
            accessibilityLabel="Message Sinc"
            testID="sinc-input"
          />
          <Pressable onPress={() => router.push('/voice')} accessibilityLabel="Talk to Sinc" testID="sinc-mic" style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: p.copper, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="mic.fill" size={18} color={p.onAccent} />
          </Pressable>
          <Pressable onPress={() => send(text)} disabled={busy || !text.trim()} accessibilityLabel="Send" testID="sinc-send" style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: text.trim() ? p.teal : p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
            {busy ? <ActivityIndicator color={p.onAccent} /> : <Icon name="arrow.up" size={18} color={text.trim() ? p.onAccent : p.faint} />}
          </Pressable>
        </Row>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Bubble({ m, onDraft }: { m: Msg; onDraft: (id: number) => void }) {
  const p = usePalette();
  if (m.role === 'user')
    return (
      <View style={{ alignSelf: 'flex-end', maxWidth: '85%', backgroundColor: p.copper, borderRadius: radius.lg, padding: space[3] }}>
        <T v="body" color={p.onAccent}>{m.content}</T>
      </View>
    );
  if (m.pending) return <SincThinking />;
  const meta = m.meta ?? {};
  return (
    <View style={{ gap: 8, maxWidth: '96%' }}>
      <Md text={m.content} />
      {meta.notice ? <T v="small" color={p.warn}>{meta.notice}</T> : null}
      {meta.chips?.length ? (
        <View style={{ gap: 6 }}>
          <T v="label">See evidence</T>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
            {meta.chips.map((c: any) => (
              <Pressable
                key={c.id}
                onPress={() => router.push(c.type === 'insight' ? `/insight/${c.id}` : c.type === 'marker' ? `/marker/${c.id}` : `/signal/${c.id}`)}
                accessibilityRole="link">
                <Chip label={c.label.length > 44 ? c.label.slice(0, 42) + '…' : c.label} fg={p.teal} bg={p.tealSoft} icon={c.type === 'insight' ? 'sparkle' : c.type === 'marker' ? 'testtube.2' : 'waveform'} />
              </Pressable>
            ))}
          </View>
        </View>
      ) : null}
      {meta.confidence != null && !meta.error ? (
        <Row>
          <ConfBar value={meta.confidence} />
          <T v="small">{Math.round(meta.confidence * 100)}% confidence</T>
          {meta.medical ? <StatusChip status="awaiting" /> : null}
        </Row>
      ) : null}
      {meta.medical && m.id ? <Button kind="secondary" icon="stethoscope" title="Draft this for my clinician" onPress={() => onDraft(m.id!)} /> : null}
    </View>
  );
}

/** Minimal markdown: **bold**, _italic_, "- " bullets, blank-line paragraphs. */
function Md({ text }: { text: string }) {
  return (
    <View style={{ gap: 6 }}>
      {text.split('\n').filter((l) => l.trim()).map((line, i) => {
        const bullet = line.trim().startsWith('- ');
        const body = bullet ? line.trim().slice(2) : line;
        const parts = body.split(/(\*\*[^*]+\*\*|_[^_]+_)/g);
        return (
          <Row key={i} style={{ alignItems: 'flex-start' }} gap={6}>
            {bullet ? <T v="body">•</T> : null}
            <T v="body" style={{ flex: 1 }}>
              {parts.map((pt, k) =>
                pt.startsWith('**') ? (
                  <T key={k} v="body" style={{ fontWeight: '700' }}>{pt.slice(2, -2)}</T>
                ) : pt.startsWith('_') && pt.endsWith('_') ? (
                  <T key={k} v="small">{pt.slice(1, -1)}</T>
                ) : (
                  pt
                ),
              )}
            </T>
          </Row>
        );
      })}
    </View>
  );
}

/** While Sinc works: the thinking orb morphs through timed stages (the answer arrives in one response, so these are
 *  paced stages of a typical answer, not live progress). */
function SincThinking() {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const a = setTimeout(() => setPhase(1), 2200), b = setTimeout(() => setPhase(2), 5500);
    return () => { clearTimeout(a); clearTimeout(b); };
  }, []);
  const stages: { state: OrbState; text: string }[] = [
    { state: 'searching', text: 'Reading your Vault…' },
    { state: 'solving', text: 'Checking the evidence…' },
    { state: 'composing', text: 'Writing your answer…' },
  ];
  const s = stages[phase];
  return (
    <Row gap={space[3]}>
      <ThinkingOrb state={s.state} size={64} />
      <T v="small">{s.text}</T>
    </Row>
  );
}
