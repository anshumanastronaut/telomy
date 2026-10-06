import { router } from 'expo-router';
import React, { useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Chip, ConfBar, Icon, Row, Spacer, StatusChip, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

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

  async function send(q: string) {
    if (!q.trim() || busy) return;
    setText('');
    setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', pending: true }]);
    setBusy(true);
    try {
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

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: p.bg }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }} keyboardVerticalOffset={60}>
        <Row style={{ paddingHorizontal: space[4], paddingVertical: space[2] }}>
          <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center' }}>
            <Logo kind="mark" width={28} tone="dark" />
          </View>
          <View>
            <T v="h3">Sinc</T>
            <T v="small">{health.data?.sinc ? `Reads your Vault · ${health.data.sinc}` : 'Reads your Vault'}</T>
          </View>
          <Spacer />
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
                <Pressable key={c.id} onPress={() => openChat(c.id)} style={{ backgroundColor: p.surface, borderRadius: radius.lg, padding: space[3], borderWidth: 1, borderColor: p.border }}>
                  <T v="body" style={{ fontWeight: '600' }}>{c.title}</T>
                  <T v="small" numberOfLines={2}>{c.preview}</T>
                </Pressable>
              ))}
              {chats.data && !chats.data.length ? <T v="small">No conversations yet.</T> : null}
            </View>
          ) : msgs.length === 0 ? (
            <View style={{ gap: space[3] }}>
              <T v="h1">I read your whole Vault before I answer.</T>
              <T v="body" color={p.muted}>
                Labs, imaging, wearables and what you log. I'll show you the evidence behind every answer, and tell you when I don't have enough to say.
              </T>
              {STARTERS.map((s) => (
                <Pressable key={s} onPress={() => send(s)} style={{ backgroundColor: p.surface, borderRadius: radius.lg, padding: space[3], borderWidth: 1, borderColor: p.border }} accessibilityRole="button">
                  <T v="body">{s}</T>
                </Pressable>
              ))}
            </View>
          ) : (
            msgs.map((m, i) => <Bubble key={i} m={m} onDraft={draft} />)
          )}
        </ScrollView>
        <Row style={{ paddingHorizontal: space[4], paddingBottom: 6 }}>
          {(['normal', 'deep'] as const).map((m) => (
            <Pressable key={m} onPress={() => setMode(m)} accessibilityRole="tab" accessibilityState={{ selected: mode === m }} testID={`mode-${m}`}>
              <Chip label={m === 'normal' ? 'Quick answer' : 'Deep research · with citations'} fg={mode === m ? '#fff' : p.text} bg={mode === m ? p.teal : p.surfaceAlt} icon={m === 'deep' ? 'books.vertical' : 'bolt'} />
            </Pressable>
          ))}
        </Row>
        {notice ? (
          <View style={{ marginHorizontal: space[4], marginBottom: 6, padding: 12, borderRadius: radius.md, backgroundColor: p.successSoft }}>
            <T v="small" color={p.success}>{notice}</T>
          </View>
        ) : null}
        <Row style={{ padding: space[3], borderTopWidth: 1, borderTopColor: p.border, backgroundColor: p.surface }}>
          <TextInput
            value={text}
            onChangeText={setText}
            placeholder="Ask about your data"
            placeholderTextColor={p.faint}
            multiline
            style={{ flex: 1, minHeight: 40, maxHeight: 120, color: p.text, fontSize: 15, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: p.bg, borderRadius: radius.md }}
            accessibilityLabel="Message Sinc"
            testID="sinc-input"
          />
          <Pressable onPress={() => send(text)} disabled={busy || !text.trim()} accessibilityLabel="Send" testID="sinc-send" style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: text.trim() ? p.teal : p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
            {busy ? <ActivityIndicator color="#fff" /> : <Icon name="arrow.up" size={18} color={text.trim() ? '#fff' : p.faint} />}
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
        <T v="body" color="#fff">{m.content}</T>
      </View>
    );
  if (m.pending)
    return (
      <Row>
        <ActivityIndicator color={p.teal} />
        <T v="small">Reading your Vault and checking the evidence…</T>
      </Row>
    );
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
