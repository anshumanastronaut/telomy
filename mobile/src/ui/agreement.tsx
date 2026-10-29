// "Signal, not verdict" — when two devices both recorded last night, show whether they agree on the score
// instead of presenting one number as the truth. Quiet when only one device saw the night. See lib/agreement.ts.
import React from 'react';
import { View } from 'react-native';

import { nightAgreement } from '@/lib/agreement';
import { space, usePalette } from '@/lib/theme';
import type { Night } from '@/lib/wellness';
import { Card, Row, T } from '@/ui/core';

export function DeviceAgreement({ night, history, metric = 'recovery' }: {
  night: Night | undefined; history: Night[]; metric?: 'recovery' | 'sleep';
}) {
  const p = usePalette();
  const a = nightAgreement(night, history, metric);
  if (!a) return null;
  const chips = [{ label: a.shown.label, score: a.shown.score, shown: true }, ...a.others.map((o) => ({ label: o.label, score: o.score, shown: false }))];
  return (
    <Card tone={a.agree ? undefined : 'copper'} style={{ gap: space[2] }}>
      <Row gap={6}>
        <T v="label" style={{ flex: 1 }}>{a.agree ? 'Your devices agree' : 'Your devices disagree'}</T>
        <T v="small" color={p.muted}>±{a.spread}</T>
      </Row>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        {chips.map((c) => (
          <View key={c.label} style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 16, borderWidth: 1, borderColor: c.shown ? p.teal : p.border, backgroundColor: c.shown ? p.teal + '22' : 'transparent' }}>
            <T v="small" color={c.shown ? p.teal : p.muted}>{c.label}</T>
            <T v="num" style={{ fontSize: 15 }} color={c.shown ? p.teal : p.text}>{c.score}</T>
          </View>
        ))}
      </View>
      <T v="small" color={p.muted}>{a.note}</T>
    </Card>
  );
}
