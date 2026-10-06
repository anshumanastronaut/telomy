import * as DocumentPicker from 'expo-document-picker';
import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { api } from '@/lib/api';
import { radius, space, statusColor, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Divider, Icon, Row, Screen, Spacer, StatusChip, T } from '@/ui/core';

const STEPS = ['Reading the PDF text', 'Finding biomarkers', 'Matching reference ranges', 'Routing to the right panel'];

export default function Upload() {
  const p = usePalette();
  const [stage, setStage] = useState<'pick' | 'reading' | 'verify' | 'saving' | 'done'>('pick');
  const [step, setStep] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [parsed, setParsed] = useState<any>(null);
  const [verified, setVerified] = useState(false);
  const [replace, setReplace] = useState(true);
  const [saved, setSaved] = useState<any>(null);

  async function pick() {
    setErr(null);
    const res = await DocumentPicker.getDocumentAsync({ type: 'application/pdf', copyToCacheDirectory: true });
    if (res.canceled) return;
    const f = res.assets[0];
    setStage('reading');
    setStep(0);
    const tick = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 450);
    try {
      const form = new FormData();
      form.append('file', { uri: f.uri, name: f.name, type: 'application/pdf' } as any);
      const r = await api('/labs/parse', { form });
      setParsed(r);
      setStage('verify');
    } catch (e: any) {
      setErr(e.message);
      setStage('pick');
    } finally {
      clearInterval(tick);
    }
  }

  async function save() {
    setStage('saving');
    try {
      const r = await api('/labs/save', {
        body: {
          title: parsed.title, panel: parsed.panel, collected_on: parsed.collected_on, filename: parsed.filename,
          is_test_data: parsed.is_test_data, markers: parsed.markers, replace_id: parsed.duplicate_of && replace ? parsed.duplicate_of : null,
        },
      });
      setSaved(r);
      setStage('done');
    } catch (e: any) {
      setErr(e.message);
      setStage('verify');
    }
  }

  function edit(i: number, v: string) {
    const m = [...parsed.markers];
    const n = Number(v);
    m[i] = { ...m[i], value: v === '' || isNaN(n) ? v : n, edited: true };
    setParsed({ ...parsed, markers: m });
  }

  return (
    <Screen edges={['top']}>
      <Row>
        <T v="h1">Add a report</T>
        <Spacer />
        <Pressable onPress={() => router.back()} hitSlop={10} accessibilityLabel="Close">
          <Icon name="xmark" color={p.muted} />
        </Pressable>
      </Row>

      {stage === 'pick' && (
        <>
          <T v="body" color={p.muted}>
            Lab panels, VO2 max / CPET, DEXA, body-composition (BCA), cardiac CT, MRI, sleep studies, genetics, gut, toxins and proteomic reports. Telomy reads the PDF, you check every value, then it's saved as its own dated record.
          </T>
          <Pressable onPress={pick} testID="pick-pdf" accessibilityRole="button" style={{ alignItems: 'center', gap: 10, padding: space[8], borderRadius: radius.xl, borderWidth: 1.5, borderStyle: 'dashed', borderColor: p.teal, backgroundColor: p.tealSoft }}>
            <Icon name="doc.badge.plus" size={36} color={p.teal} />
            <T v="h3" color={p.teal}>Choose a PDF</T>
            <T v="small">From Files, iCloud Drive or Downloads</T>
          </Pressable>
          {err ? (
            <Card tone="copper">
              <T v="body">{err}</T>
            </Card>
          ) : null}
          <T v="small">Your PDF is processed on Telomy's server for extraction only and isn't shared with anyone.</T>
        </>
      )}

      {stage === 'reading' && (
        <Card>
          {STEPS.map((s, i) => (
            <Row key={s}>
              <Icon name={i < step ? 'checkmark.circle.fill' : i === step ? 'circle.dotted' : 'circle'} color={i <= step ? p.teal : p.faint} size={18} />
              <T v="body" color={i <= step ? p.text : p.faint}>{s}{i === step ? '…' : ''}</T>
            </Row>
          ))}
        </Card>
      )}

      {(stage === 'verify' || stage === 'saving') && parsed && (
        <>
          <Card>
            <T v="label">Check what I found</T>
            <T v="h3">{parsed.title}</T>
            <Row style={{ flexWrap: 'wrap' }}>
              <Chip label={parsed.panel_title} fg={p.teal} bg={p.tealSoft} />
              <Chip label={parsed.collected_on ?? 'Date not found'} />
              <Chip label={`${parsed.markers.length} markers`} />
              {parsed.is_test_data ? <Chip label="Marked as test data" fg={p.copper} bg={p.copperSoft} /> : null}
            </Row>
            {parsed.duplicate_of ? (
              <Pressable onPress={() => setReplace(!replace)} style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }} accessibilityRole="checkbox" accessibilityState={{ checked: replace }}>
                <Icon name={replace ? 'checkmark.square.fill' : 'square'} color={p.teal} />
                <T v="small" style={{ flex: 1 }}>You already have a {parsed.panel_title.toLowerCase()} from this date. Replace it instead of adding a second copy.</T>
              </Pressable>
            ) : null}
          </Card>
          <Card style={{ paddingVertical: 4 }}>
            {parsed.markers.map((m: any, i: number) => (
              <View key={m.marker_id}>
                {i ? <Divider /> : null}
                <Row style={{ paddingVertical: 8 }}>
                  <View style={{ flex: 1, gap: 3 }}>
                    <T v="body" style={{ fontWeight: '500' }}>{m.name}</T>
                    <Row>
                      <StatusChip status={m.status} />
                      <T v="small">{m.ref_text || '—'}</T>
                    </Row>
                  </View>
                  <TextInput
                    value={String(m.value)}
                    onChangeText={(v) => edit(i, v)}
                    style={{ width: 92, textAlign: 'right', borderWidth: 1, borderColor: m.edited ? p.copper : p.border, borderRadius: radius.sm, padding: 8, color: statusColor(p, m.status).fg, fontVariant: ['tabular-nums'] }}
                    accessibilityLabel={`${m.name} value`}
                  />
                  <T v="small" style={{ width: 54 }}>{m.unit}</T>
                </Row>
              </View>
            ))}
          </Card>
          {parsed.unmatched?.length ? <T v="small">Not recognised (not saved): {parsed.unmatched.join('; ')}</T> : null}
          <Pressable onPress={() => setVerified(!verified)} testID="verify-check" accessibilityRole="checkbox" accessibilityState={{ checked: verified }} style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}>
            <Icon name={verified ? 'checkmark.square.fill' : 'square'} color={p.teal} size={22} />
            <T v="body" style={{ flex: 1 }}>I've checked these values against my report.</T>
          </Pressable>
          {err ? <T v="small" color={p.danger}>{err}</T> : null}
          <Button title="Save to my Vault" disabled={!verified} loading={stage === 'saving'} onPress={save} testID="save-report" />
        </>
      )}

      {stage === 'done' && saved && (
        <Card tone="teal">
          <T v="h2">Saved.</T>
          <T v="body">{saved.markers} markers added to your {parsed.panel_title.toLowerCase()}. Sinc has re-read your Vault with them.</T>
          <Button title="See the panel" onPress={() => router.replace('/(tabs)/vault')} />
          <Button kind="secondary" title="Add another" onPress={() => { setStage('pick'); setParsed(null); setVerified(false); }} />
        </Card>
      )}
    </Screen>
  );
}
