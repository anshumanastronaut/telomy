// Context tags: one tap to note what was going on around a reading (caffeine, stress, standing, late meal, a warm
// room…), so an unusual number is explained rather than alarming — the "signal, not verdict" idea. Over time these
// also explain outliers in the trends. Backend: GET/POST /me/context-tags.
import React, { useState } from 'react';
import { Pressable, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, T } from '@/ui/core';

const TAGS = ['Caffeine', 'Alcohol', 'Late meal', 'Stress', 'Travel', 'Illness', 'Hard workout', 'Warm/noisy room', 'Late screen', 'Poor night'];

export function ContextTags() {
  const p = usePalette();
  const { data, reload } = useApi<any>('/me/context-tags');
  const [sel, setSel] = useState<string[] | null>(null);
  const current: string[] = sel ?? data?.today?.tags ?? [];

  async function toggle(tag: string) {
    const next = current.includes(tag) ? current.filter((t) => t !== tag) : [...current, tag];
    setSel(next);
    try { await api('/me/context-tags', { body: { tags: next } }); reload(); } catch {}
  }

  return (
    <Card style={{ gap: space[2] }}>
      <T v="h3">What was going on?</T>
      <T v="small" color={p.muted}>Tag anything that could explain today's numbers — so a reading is context, not a verdict.</T>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        {TAGS.map((tag) => {
          const on = current.includes(tag);
          return (
            <Pressable key={tag} onPress={() => toggle(tag)}
              style={{ paddingHorizontal: 12, paddingVertical: 7, borderRadius: 16, borderWidth: 1, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.teal + '22' : 'transparent' }}>
              <T v="small" color={on ? p.teal : p.muted}>{tag}</T>
            </Pressable>
          );
        })}
      </View>
    </Card>
  );
}
