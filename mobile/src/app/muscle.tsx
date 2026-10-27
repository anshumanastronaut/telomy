// Muscle age test — the flow the Telomy EMG patch will run. Modelled on predict.fit's system-age pattern: a short,
// guided test → one age for the system → the drivers behind it → the levers that move it.
// The patch is in development, so this screen shows the real protocol and an EXAMPLE result, clearly labelled.
// No simulated value is ever stored in the Vault or fed to the clocks.
import { Stack } from 'expo-router';
import React, { useState } from 'react';
import { View } from 'react-native';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Icon, Row, Screen, Section, T } from '@/ui/core';

const STEPS = [
  { icon: 'bandage', title: 'Place the patch', body: 'On the outer thigh (vastus lateralis), a hand-width above the knee, along the muscle. A second patch on the other leg measures symmetry.' },
  { icon: 'figure.stand', title: 'Rest baseline · 10 s', body: 'Stand still. Telomy records resting muscle tone and electrode quality before the test.' },
  { icon: 'figure.strengthtraining.functional', title: 'Max effort · 3 × 3 s', body: 'Push your heel into the floor as hard as you can (MVC). This sets your 100 % reference.' },
  { icon: 'timer', title: 'Wall-sit at 60 % · 45 s', body: 'Hold a wall-sit. As muscle fatigues, the EMG frequency content drops — how fast it drops is the core signal.' },
  { icon: 'figure.run', title: 'Sit-to-stand · 30 s', body: 'As many full stands as you can. Adds power, recruitment speed and a functional score (CDC STEADI norms).' },
];

const METRICS = [
  { k: 'Fatigue resistance', d: 'Median-frequency (MDF) slope during the wall-sit. Older and deconditioned muscle shows a steeper decline as fast-twitch fibres are lost (Merletti; De Luca).' },
  { k: 'Activation', d: 'RMS amplitude at max effort, normalised. Lower drive per unit effort tracks with sarcopenia and neuromuscular ageing.' },
  { k: 'Recruitment speed', d: 'EMG onset to force — slows with age and predicts fall risk.' },
  { k: 'Symmetry', d: 'Left vs right activation. > 15 % imbalance flags injury risk or compensation.' },
  { k: 'Muscle mass', d: 'ALMI from your DEXA in the Vault, combined with EMG quality into one Muscle age.' },
];

export default function MuscleTest() {
  const p = usePalette();
  const [example, setExample] = useState(false);

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Muscle age test' }} />
      <Card tone="copper">
        <Row><Icon name="waveform.path" color={p.copper} /><T v="h3" style={{ flex: 1 }}>EMG patch — coming soon</T><Chip label="Preview" /></Row>
        <T v="small">This is the test the Telomy EMG patch will run (about 2 minutes). Until it ships, your Muscle age uses muscle mass from your DEXA scan.</T>
      </Card>

      <Section title="How the test works">
        {STEPS.map((s, i) => (
          <Card key={s.title}>
            <Row style={{ alignItems: 'flex-start' }}>
              <View style={{ width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: p.tealSoft }}>
                <T v="small" color={p.teal} style={{ fontWeight: '700' }}>{i + 1}</T>
              </View>
              <View style={{ flex: 1, gap: 2 }}>
                <Row gap={6}><Icon name={s.icon as any} size={14} color={p.teal} /><T v="h3">{s.title}</T></Row>
                <T v="small">{s.body}</T>
              </View>
            </Row>
          </Card>
        ))}
      </Section>

      <Section title="What it measures">
        <Card style={{ gap: space[3] }}>
          {METRICS.map((m) => (
            <View key={m.k} style={{ gap: 2 }}>
              <T v="body" style={{ fontWeight: '600' }}>{m.k}</T>
              <T v="small" color={p.muted}>{m.d}</T>
            </View>
          ))}
        </Card>
      </Section>

      <Button kind="secondary" title={example ? 'Hide example result' : 'See an example result'} icon="doc.text.magnifyingglass" onPress={() => setExample((x) => !x)} />
      {example ? (
        <Card style={{ gap: space[2] }}>
          <Row><T v="label" style={{ flex: 1 }}>Example result — not your data</T><Chip label="Example" fg={p.warn} bg={p.warnSoft} /></Row>
          <Row style={{ alignItems: 'baseline' }} gap={6}><T v="num" style={{ fontSize: 40 }}>41</T><T v="small">Muscle age · person aged 36</T></Row>
          <T v="small">Drivers: fatigue resistance below norm (MDF −0.42 %/s vs −0.30), activation normal, 11 % left–right imbalance, ALMI 8.1 kg/m².</T>
          <T v="small" color={p.muted}>Levers: 2–3 strength sessions/week with progressive overload; protein 1.6 g/kg/day; single-leg work for the weaker side. Retest in 8 weeks.</T>
        </Card>
      ) : null}
    </Screen>
  );
}
