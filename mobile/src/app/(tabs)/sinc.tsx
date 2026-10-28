import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system/legacy';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { ActionSheetIOS, ActivityIndicator, Alert, Keyboard, KeyboardAvoidingView, Platform, Pressable, ScrollView, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, useApi } from '@/lib/api';
import { askOnDevice, SLM_INFO, useSlm } from '@/lib/slm';
import { radius, space, type, usePalette } from '@/lib/theme';
import { Button, Chip, ConfBar, Icon, Row, Spacer, StatusChip, T } from '@/ui/core';
import { Logo } from '@/ui/logo';
import { TelomyLoader } from '@/ui/loader';

/** A file staged in the composer (image, pdf or document) before it's sent to Sinc. `data` is base64. */
type Att = { kind: 'image' | 'pdf' | 'file'; name: string; media_type?: string; data: string };
type Msg = { role: 'user' | 'assistant'; content: string; meta?: any; id?: number; pending?: boolean; attachments?: { name: string; kind: string }[] };

const STARTERS = [
  'My lower back hurts, about 5/10',
  'I started magnesium 200 mg before bed',
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
  const [atts, setAtts] = useState<Att[]>([]);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [mode, setMode] = useState<'normal' | 'deep'>('normal');
  const scroll = useRef<ScrollView>(null);
  const chats = useApi<any[]>(history ? '/sinc/chats' : null, [history]);
  const health = useApi<any>('/health');
  const insights = useApi<any>('/sinc/insights');
  const slm = useSlm();
  const [slmCard, setSlmCard] = useState(false);

  async function addImage(fromCamera: boolean) {
    try {
      const perm = fromCamera ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) { setNotice(`Allow ${fromCamera ? 'camera' : 'photo'} access in Settings to attach images.`); return; }
      const res = fromCamera
        ? await ImagePicker.launchCameraAsync({ base64: true, quality: 0.6 })
        : await ImagePicker.launchImageLibraryAsync({ base64: true, quality: 0.6, mediaTypes: ['images'] });
      if (res.canceled || !res.assets?.[0]?.base64) return;
      const a = res.assets[0];
      setAtts((xs) => [...xs, { kind: 'image' as const, name: a.fileName ?? 'photo.jpg', media_type: a.mimeType ?? 'image/jpeg', data: a.base64! }].slice(-6));
    } catch (e: any) { setNotice(`Couldn't add the image. ${e.message ?? ''}`); }
  }

  async function addDocument() {
    try {
      const res = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'text/markdown', 'text/csv'],
        copyToCacheDirectory: true,
      });
      if (res.canceled || !res.assets?.[0]) return;
      const f = res.assets[0];
      const data = await FileSystem.readAsStringAsync(f.uri, { encoding: FileSystem.EncodingType.Base64 });
      const kind: Att['kind'] = (f.mimeType === 'application/pdf' || f.name?.toLowerCase().endsWith('.pdf')) ? 'pdf' : 'file';
      setAtts((xs) => [...xs, { kind, name: f.name ?? 'document', media_type: f.mimeType, data }].slice(-6));
    } catch (e: any) { setNotice(`Couldn't add the document. ${e.message ?? ''}`); }
  }

  function pickAttachment() {
    Keyboard.dismiss();
    const opts = ['Photo Library', 'Take Photo', 'PDF or Document', 'Cancel'];
    const run = (i: number) => { if (i === 0) addImage(false); else if (i === 1) addImage(true); else if (i === 2) addDocument(); };
    if (Platform.OS === 'ios') {
      ActionSheetIOS.showActionSheetWithOptions({ options: opts, cancelButtonIndex: 3, title: 'Attach to Sinc' }, run);
    } else {
      Alert.alert('Attach to Sinc', undefined, [
        { text: opts[0], onPress: () => run(0) }, { text: opts[1], onPress: () => run(1) },
        { text: opts[2], onPress: () => run(2) }, { text: 'Cancel', style: 'cancel' },
      ]);
    }
  }

  async function send(q: string) {
    const outgoing = atts;
    if ((!q.trim() && outgoing.length === 0) || busy) return;
    setText('');
    setAtts([]);
    const chips = outgoing.map((a) => ({ name: a.name, kind: a.kind === 'image' ? 'image' : 'doc' }));
    setMsgs((m) => [...m, { role: 'user', content: q, attachments: chips.length ? chips : undefined }, { role: 'assistant', content: '', pending: true }]);
    setBusy(true);
    // files need the cloud Sinc (document parsing + vision), so bypass the on-device model when anything is attached
    if (outgoing.length) {
      try {
        const body = { question: q, chat_id: chatId, mode, attachments: outgoing };
        const r = await api('/sinc/ask', { body, timeoutMs: 180000 });
        setChatId(r.chat_id);
        setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: r.answer, meta: r, id: r.message_id }]);
      } catch (e: any) {
        setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: `I couldn't read that just now. ${e.message}`, meta: { error: true } }]);
      } finally {
        setBusy(false);
        setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 100);
      }
      return;
    }
    try {
      // On this iPhone first when chosen (quick answers only — deep research needs the citation library on the server).
      if (slm.on && mode === 'normal') {
        // statements ("my knee hurts, 5", "started magnesium") set up trackers on the server first
        const cap = await api('/sinc/capture', { body: { text: q } });
        if (cap.captured) {
          const r = await api('/sinc/log', { body: { question: q, answer: cap.answer, chat_id: chatId, model: 'telomy-trackers' } });
          setChatId(r.chat_id);
          setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: cap.answer, id: r.message_id, meta: { ...r, trackers: cap.trackers } }]);
          return;
        }
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
    setMsgs(ms.map((m) => ({ role: m.role, content: m.content, meta: m.meta, id: m.id, attachments: m.meta?.attachments })));
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
          {/* Sinc's face: the Telomy motion mark is always alive here — the brand's signature loader */}
          <View style={{ width: 44, height: 36, alignItems: 'center', justifyContent: 'center' }}>
            <TelomyLoader size="mark" />
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
        <ScrollView ref={scroll} style={{ flex: 1 }} contentContainerStyle={{ padding: space[4], gap: space[3], paddingBottom: 30 }} keyboardShouldPersistTaps="handled">
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
              <TelomyLoader size="hero" />
              <View style={{ alignItems: 'center', gap: space[2] }}>
                <T v="h1" style={{ textAlign: 'center' }}>Always watching.</T>
                <T v="small" color={p.muted} style={{ textAlign: 'center' }}>Sinc knows your whole Vault — and shows its evidence.</T>
              </View>
              {insights.data?.threads?.length ? (
                <View style={{ width: '100%', gap: space[2] }}>
                  <T v="label">What Sinc connects across your data</T>
                  {insights.data.threads.map((t: any) => (
                    <Pressable key={t.insight_id} onPress={() => send(`Tell me more about: ${t.headline}`)}
                      style={{ backgroundColor: p.surface, borderRadius: radius.lg, padding: space[3], gap: 4 }}>
                      <Row>
                        <Chip label={t.theme} fg={p.teal} bg={p.tealSoft} />
                        <View style={{ flex: 1 }} />
                        <T v="small" color={p.muted}>{Math.round((t.confidence ?? 0) * 100)}%</T>
                      </Row>
                      <T v="body" style={{ fontWeight: '600' }}>{t.headline}</T>
                      <T v="small" color={p.muted} numberOfLines={3}>{t.story}</T>
                    </Pressable>
                  ))}
                </View>
              ) : null}
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
        {/* mode row: a quiet wrapping row (never a horizontal scroll), with vertical room so chips aren't clipped */}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: space[2], paddingHorizontal: space[4], paddingBottom: 6 }}>
          {(['normal', 'deep'] as const).map((m) => (
            <Pressable key={m} onPress={() => setMode(m)} accessibilityRole="tab" accessibilityState={{ selected: mode === m }} testID={`mode-${m}`}>
              <Chip label={m === 'normal' ? 'Quick answer' : 'Deep research'} fg={mode === m ? (p.isDark ? p.bg : p.onAccent) : p.text} bg={mode === m ? p.teal : p.surfaceAlt} icon={m === 'deep' ? 'books.vertical' : 'bolt'} />
            </Pressable>
          ))}
          {slm.available ? (
            <Pressable onPress={() => (slm.ready ? slm.setOn(!slm.on) : setSlmCard(!slmCard))} accessibilityRole="switch"
              accessibilityState={{ checked: slm.on }} testID="mode-device">
              <Chip label={slm.on ? 'On this iPhone' : 'On-device'} fg={slm.on ? (p.isDark ? p.bg : p.onAccent) : p.text} bg={slm.on ? p.copper : p.surfaceAlt} icon="iphone" />
            </Pressable>
          ) : null}
        </View>
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
        {/* staged attachments, above the input */}
        {atts.length ? (
          <Row style={{ marginHorizontal: space[4], marginBottom: 6, flexWrap: 'wrap' }} gap={6}>
            {atts.map((a, i) => (
              <Pressable key={i} onPress={() => setAtts((xs) => xs.filter((_, j) => j !== i))} accessibilityLabel={`Remove ${a.name}`}
                style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 6, paddingHorizontal: 10, borderRadius: radius.md, backgroundColor: p.surfaceAlt }}>
                <Icon name={a.kind === 'image' ? 'photo' : 'doc.text'} size={14} color={p.teal} />
                <T v="small" color={p.text} numberOfLines={1} style={{ maxWidth: 160 }}>{a.name}</T>
                <Icon name="xmark.circle.fill" size={14} color={p.faint} />
              </Pressable>
            ))}
          </Row>
        ) : null}
        {/* composer floats above the glass tab bar; drops to the keyboard when typing */}
        <Row style={{ marginHorizontal: space[3], marginBottom: kbd ? 8 : 98, padding: 6, paddingLeft: 4, borderRadius: 28, backgroundColor: p.surface }}>
          <Pressable onPress={pickAttachment} disabled={busy} accessibilityLabel="Attach a file" testID="sinc-attach"
            style={{ width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="paperclip" size={20} color={p.muted} />
          </Pressable>
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
          <Pressable onPress={() => send(text)} disabled={busy || (!text.trim() && atts.length === 0)} accessibilityLabel="Send" testID="sinc-send" style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: (text.trim() || atts.length) ? p.teal : p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
            {busy ? <ActivityIndicator color={p.onAccent} /> : <Icon name="arrow.up" size={18} color={(text.trim() || atts.length) ? p.onAccent : p.faint} />}
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
      <View style={{ alignSelf: 'flex-end', maxWidth: '85%', backgroundColor: p.copper, borderRadius: radius.lg, padding: space[3], gap: 6 }}>
        {m.attachments?.length ? (
          <Row style={{ flexWrap: 'wrap' }} gap={6}>
            {m.attachments.map((a, i) => (
              <Row key={i} gap={5} style={{ alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: radius.sm, paddingVertical: 4, paddingHorizontal: 8 }}>
                <Icon name={a.kind === 'image' ? 'photo' : 'doc.text'} size={13} color={p.onAccent} />
                <T v="small" color={p.onAccent} numberOfLines={1} style={{ maxWidth: 170 }}>{a.name}</T>
              </Row>
            ))}
          </Row>
        ) : null}
        {m.content ? <T v="body" color={p.onAccent}>{m.content}</T> : null}
      </View>
    );
  if (m.pending) return <SincThinking />;
  const meta = m.meta ?? {};
  return (
    <View style={{ gap: 8, maxWidth: '96%' }}>
      <Md text={m.content} />
      {meta.notice ? <T v="small" color={p.warn}>{meta.notice}</T> : null}
      {meta.trackers?.length ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
          {meta.trackers.map((t: any) => (
            <Pressable key={t.id} onPress={() => router.push(`/tracker/${t.id}` as any)} accessibilityRole="link">
              <Chip label={`${t.new ? 'New tracker' : 'Tracker'} · ${t.name}`} fg={p.teal} bg={p.tealSoft} icon="list.bullet.clipboard" />
            </Pressable>
          ))}
        </View>
      ) : null}
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
  const stages = ['Reading your Vault…', 'Checking the evidence…', 'Writing your answer…'];
  return (
    <Row gap={space[3]} style={{ alignItems: 'center' }}>
      <TelomyLoader size="inline" />
      <T v="small">{stages[phase]}</T>
    </Row>
  );
}
