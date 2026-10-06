import React, { useEffect, useState } from 'react';
import { TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { Button, Card, Row, Screen, T, useToast } from '@/ui/core';

const F = [['steps', 'Daily steps', 10000], ['exercise_min', 'Exercise minutes', 30], ['kcal', 'Energy (kcal)', 2000], ['protein', 'Protein (g)', 120], ['carbs', 'Carbs (g)', 220], ['fat', 'Fat (g)', 70]] as const;

export default function Goals() {
  const p = usePalette();
  const { data } = useApi<any>('/profile');
  const calc = useApi<any>('/calculators');
  const [g, setG] = useState<any>({});
  const { toast, show } = useToast();
  useEffect(() => { if (data) setG({ ...Object.fromEntries(F.map(([k, , d]) => [k, d])), ...(data.goals ?? {}), ...(data.nutrition_goals ?? {}) }); }, [data]);
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Card>
          {F.map(([k, l]) => (
            <Row key={k}>
              <T v="body" style={{ flex: 1 }}>{l}</T>
              <TextInput keyboardType="number-pad" value={String(g[k] ?? '')} onChangeText={(v) => setG({ ...g, [k]: Number(v) || 0 })} style={{ width: 100, textAlign: 'right', borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 8, color: p.text, fontFamily: 'Inter_400Regular' }} />
            </Row>
          ))}
        </Card>
        {calc.data?.macros ? (
          <Card tone="teal">
            <T v="label">Suggested from your data</T>
            <T v="body">BMR {calc.data.bmr.value} kcal ({calc.data.bmr.method}) · TDEE {calc.data.tdee.value} kcal</T>
            <T v="body">Lean mass {calc.data.lean_mass.value} kg ({calc.data.lean_mass.source}) → protein {calc.data.protein_target.range[0]}–{calc.data.protein_target.range[1]} g</T>
            <T v="body">Plan: {calc.data.macros.kcal} kcal · P {calc.data.macros.protein} g · C {calc.data.macros.carbs} g · F {calc.data.macros.fat} g</T>
            <T v="small">{calc.data.macros.note}</T>
            <Button kind="secondary" title="Use these targets" onPress={() => setG({ ...g, kcal: calc.data.macros.kcal, protein: calc.data.macros.protein, carbs: calc.data.macros.carbs, fat: calc.data.macros.fat })} />
          </Card>
        ) : null}
        <Button title="Save goals" onPress={async () => {
          await api('/profile', { method: 'PUT', body: { goals: { steps: g.steps, exercise_min: g.exercise_min }, nutrition_goals: { kcal: g.kcal, protein: g.protein, carbs: g.carbs, fat: g.fat } } });
          show('Saved.', 'success');
        }} />
      </Screen>
      {toast}
    </View>
  );
}
