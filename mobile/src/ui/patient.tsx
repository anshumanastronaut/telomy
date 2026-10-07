import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { usePalette } from '@/lib/theme';

import { Card, Chip, Row, T } from './core';

export function PatientRow({ p: x, onPress }: { p: any; onPress?: () => void }) {
  const p = usePalette();
  const pr = x.priority >= 40 ? [p.danger, p.dangerSoft, 'High'] : x.priority >= 20 ? [p.warn, p.warnSoft, 'Medium'] : [p.success, p.successSoft, 'Routine'];
  return (
    <Card onPress={onPress ?? (() => router.push(`/patient/${x.id}`))} testID={`patient-${x.id}`}>
      <Row>
        <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: p.tealSoft, alignItems: 'center', justifyContent: 'center' }}>
          <T v="h3" color={p.teal}>{x.name[0]}</T>
        </View>
        <View style={{ flex: 1 }}>
          <T v="h3">{x.name}</T>
          <T v="small">{x.age} y · {x.sex} · {x.city}{x.plan ? ` · ${x.plan}` : ''}</T>
        </View>
        <Chip label={pr[2] as string} fg={pr[0] as string} bg={pr[1] as string} />
      </Row>
      {x.flags.length ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
          {x.flags.map((f: string) => <Chip key={f} label={f} />)}
        </View>
      ) : <T v="small">No risk flags</T>}
      <T v="small">
        {x.cvd != null ? `10-y CVD ${x.cvd}%` : '10-y CVD —'} · {x.diabetes != null ? `diabetes 5-y ${x.diabetes}%` : 'diabetes —'}
        {x.awaiting_reviews ? ` · ${x.awaiting_reviews} drafts to review` : ''}{x.full_vault ? ' · full Vault' : ''}
      </T>
    </Card>
  );
}
