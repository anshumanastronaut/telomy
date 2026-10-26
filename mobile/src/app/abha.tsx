// ABHA — India's health ID (ABDM). The member can register their ABHA address with Telomy; pulling their national
// health records (from hospitals/labs across India, over ABDM's consented FHIR exchange) turns on once the clinic
// connects ABDM. Honest about the sandbox state — nothing is faked as "connected" until it really is.
import { Stack } from 'expo-router';
import React from 'react';
import { Linking, TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, ErrorState, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function Abha() {
  const p = usePalette();
  const st = useApi<any>('/abha/status');
  const rec = useApi<any>('/abha/records');
  const [abha, setAbha] = React.useState('');
  const { toast, show } = useToast();
  if (st.error) return <Screen edges={['top']}><ErrorState message={st.error} onRetry={st.reload} /></Screen>;
  if (!st.data) return <Screen edges={['top']}><Loading what="Checking ABHA…" /></Screen>;
  const s = st.data;

  async function link() {
    try { await api('/abha/link', { body: { abha: abha.trim() } }); show('ABHA registered.', 'success'); setAbha(''); st.reload(); rec.reload(); }
    catch (e: any) { show(e.message, 'alert'); }
  }
  async function unlink() {
    try { await api('/abha/link', { method: 'DELETE' }); show('Unlinked.', 'success'); st.reload(); }
    catch (e: any) { show(e.message, 'alert'); }
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={['top']} onRefresh={() => { st.reload(); rec.reload(); }} refreshing={st.loading}>
        <Stack.Screen options={{ title: '' }} />
        <T v="h1">ABHA</T>
        <T v="small" color={p.muted}>Your Ayushman Bharat Health Account — India's national health ID. Link it to bring your records from any hospital or lab into your Telomy Vault, with your consent.</T>

        <Row style={{ marginTop: 8 }}>
          {s.linked ? <Chip label="ABHA ID linked" fg={p.teal} bg={p.tealSoft} /> : null}
          <Chip label={s.configured ? 'Records: connected' : 'Records: pending clinic setup'} fg={s.configured ? p.teal : p.warn} bg={s.configured ? p.tealSoft : p.warnSoft} />
        </Row>

        {s.linked ? (
          <Section title="Your ABHA">
            <Card>
              <Row style={{ justifyContent: 'space-between' }}><T v="h3">{s.abha}</T><Chip label={s.configured ? 'verified' : 'registered'} fg={p.teal} bg={p.tealSoft} /></Row>
              {s.linked_at ? <T v="small" color={p.faint}>Linked {s.linked_at.slice(0, 10)}</T> : null}
              <Button kind="ghost" title="Unlink ABHA" onPress={unlink} />
            </Card>
          </Section>
        ) : (
          <Section title="Link your ABHA">
            <Card style={{ gap: space[1] }}>
              <T v="label" color={p.muted}>ABHA number or address</T>
              <TextInput value={abha} onChangeText={setAbha} placeholder="e.g. 12-3456-7890-1234 or you@abdm" placeholderTextColor={p.faint} autoCapitalize="none"
                style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, fontFamily: 'HankenGrotesk_400Regular' }} />
              <Button kind="primary" title="Link ABHA" disabled={!abha.trim()} onPress={link} />
              <T v="small" color={p.teal} onPress={() => Linking.openURL('https://abha.abdm.gov.in/')}>Don't have one? Create an ABHA →</T>
            </Card>
          </Section>
        )}

        <Section title="Health records">
          <Card>
            {(rec.data?.records ?? []).length ? rec.data.records.map((r: any, i: number) => (
              <Row key={i} style={{ justifyContent: 'space-between' }}><T v="body">{r.title ?? r.type}</T><T v="small" color={p.faint}>{r.date}</T></Row>
            )) : <T v="small" color={p.muted}>{rec.data?.note ?? 'No records yet.'}</T>}
          </Card>
          <T v="small" color={p.faint} style={{ marginTop: 6 }}>Records are fetched only with your explicit, per-request consent (ABDM) and land in your Vault. You can revoke access any time in the Consent Centre.</T>
        </Section>
      </Screen>
      {toast}
    </View>
  );
}
