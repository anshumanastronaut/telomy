// "Make yourself fully insured" — explains which kinds of cover matter for *this* person, from what their Vault shows,
// and what full cover means in India. Telomy is not an insurer or broker: advice on specific policies comes from an
// IRDAI-licensed partner advisor, so this screen educates and connects — it never sells or picks a product.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { View } from 'react-native';
import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Icon, Row, Screen, Section, T } from '@/ui/core';

const COVER = [
  { icon: 'cross.case', name: 'Base health cover', why: 'Hospital bills. In a metro, ₹10–25 lakh for the family is a common floor today — treatment costs rise every year.' },
  { icon: 'arrow.up.circle', name: 'Super top-up', why: 'The cheapest way to reach a high sum insured: pays once a large bill crosses your base cover.' },
  { icon: 'heart.text.square', name: 'Critical illness', why: 'A lump sum on diagnosis of heart attack, stroke, cancer and more — for costs and income loss a hospital policy never pays.' },
  { icon: 'figure.fall', name: 'Personal accident', why: 'Pays for death or disability from an accident. Inexpensive and often missed.' },
  { icon: 'person.2.circle', name: 'Term life', why: 'Protects the people who depend on your income. Pure cover, no investment mixed in.' },
  { icon: 'stethoscope', name: 'OPD & consultations', why: 'Doctor visits, tests and medicines outside hospital — useful if you monitor a condition regularly.' },
];

/** What a flagged organ system means for cover — the same organ map the Twin shows. */
const FOR_SYSTEM: Record<string, string> = {
  'Heart & vessels': 'Your heart & vessel markers are flagged — critical-illness cover (heart attack, stroke) matters most for you. Check cardiac waiting periods before you buy.',
  'Blood sugar & metabolism': 'Your blood-sugar markers are flagged — look at how each policy treats diabetes and pre-diabetes, and the waiting period for pre-existing conditions.',
  Liver: 'Your liver markers are flagged — fatty-liver findings are usually insurable; disclose them so a future claim is never refused.',
  'Lungs & cardio fitness': 'Low cardio fitness is worth improving before a medical underwriting check, which can lower your premium.',
};

export default function Insurance() {
  const p = usePalette();
  const twin = useApi<any>('/twin');
  const [asked, setAsked] = useState(false);
  useEffect(() => { AsyncStorage.getItem('telomy.insuranceInterest').then((v) => setAsked(!!v)).catch(() => {}); }, []);
  const flagged = (twin.data?.systems ?? []).filter((s: any) => s.status !== 'ok' && FOR_SYSTEM[s.name]);

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Insurance' }} />
      <View style={{ alignItems: 'center', gap: space[2], paddingVertical: space[4] }}>
        <Icon name="shield.checkered" size={40} color={p.teal} />
        <T v="h1" style={{ textAlign: 'center' }}>Make yourself fully insured.</T>
        <T v="small" style={{ textAlign: 'center' }}>Telomy knows your health. Let it make sure you're covered for it.</T>
      </View>

      {flagged.length ? (
        <Section title="Based on your Vault">
          {flagged.map((s: any) => (
            <Card key={s.name}>
              <Row><Chip label={s.name} fg={s.status === 'high' ? p.danger : p.warn} bg={s.status === 'high' ? p.dangerSoft : p.warnSoft} /></Row>
              <T v="body">{FOR_SYSTEM[s.name]}</T>
            </Card>
          ))}
        </Section>
      ) : null}

      <Section title="What full cover means">
        <Card style={{ gap: space[4] }}>
          {COVER.map((c) => (
            <Row key={c.name} style={{ alignItems: 'flex-start' }} gap={space[3]}>
              <Icon name={c.icon as any} size={18} color={p.teal} />
              <View style={{ flex: 1, gap: 2 }}><T v="h3">{c.name}</T><T v="small">{c.why}</T></View>
            </Row>
          ))}
        </Card>
      </Section>

      <Card tone="copper">
        <T v="h3">Always disclose your conditions</T>
        <T v="small">Non-disclosure is the most common reason a claim is rejected. Your Vault already holds the records an insurer will ask for — share them with consent from the Consent centre.</T>
      </Card>

      <Card style={{ gap: space[3] }}>
        <T v="h3">Get matched with an advisor</T>
        <T v="small">Telomy isn't an insurer or broker. We'll connect you to an IRDAI-licensed advisor who compares policies for your needs — your Vault stays private unless you choose to share it.</T>
        {asked
          ? <Row gap={8}><Icon name="checkmark.circle.fill" size={16} color={p.success} /><T v="small" color={p.success}>You're on the list — we'll reach out when advisor matching opens.</T></Row>
          : <Button title="I'm interested" icon="hand.raised" onPress={() => { AsyncStorage.setItem('telomy.insuranceInterest', String(Date.now())).catch(() => {}); setAsked(true); }} />}
      </Card>
      <T v="small" color={p.faint}>General information, not insurance advice. Policy terms, waiting periods and exclusions vary by insurer.</T>
    </Screen>
  );
}
