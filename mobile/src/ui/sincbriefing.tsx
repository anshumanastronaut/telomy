// Proactive Sinc — the briefing. Instead of waiting to be asked, Sinc surfaces the few things that matter right
// now (doctor targets you haven't hit, findings awaiting review, what your own data showed), each with one next
// step. Tap an item to go straight to it. Grounded in the same engines; nothing invented.
import { router } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, Icon, Row, T } from './core';
import { TelomyLoader } from './loader';

type Item = { kind: string; severity: 'high' | 'watch'; icon?: any; title: string; detail?: string; action?: string; route?: string };

export function SincBriefing() {
  const p = usePalette();
  const { data, loading } = useApi<any>('/sinc/briefing');
  if (!data) {
    if (!loading) return null;
    return (
      <Card style={{ gap: space[1] }}>
        <Row gap={8} style={{ alignItems: 'center' }}>
          <View style={{ width: 26, height: 26, borderRadius: 13, backgroundColor: p.tealSoft, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="sparkles" size={14} color={p.teal} />
          </View>
          <T v="label" style={{ flex: 1 }}>Sinc</T>
        </Row>
        <TelomyLoader message="Reading your signals…" />
      </Card>
    );
  }
  const items: Item[] = data.items ?? [];

  return (
    <Card style={{ gap: space[1] }}>
      <Row gap={8} style={{ alignItems: 'center' }}>
        <View style={{ width: 26, height: 26, borderRadius: 13, backgroundColor: p.tealSoft, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="sparkles" size={14} color={p.teal} />
        </View>
        <T v="label" style={{ flex: 1 }}>Sinc · {data.greeting ?? 'Here’s what I noticed'}</T>
        {items.length ? <T v="small" color={p.muted}>{items.length}</T> : null}
      </Row>

      {items.length ? items.map((it, i) => {
        const col = it.severity === 'high' ? p.copper : p.teal;
        return (
          <Pressable key={i} onPress={() => it.route && router.push(it.route as any)}>
            <Row gap={10} style={{ alignItems: 'flex-start', paddingVertical: 6, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
              <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: col, marginTop: 7 }} />
              <View style={{ flex: 1 }}>
                <T v="body">{it.title}</T>
                {it.detail ? <T v="small" color={p.muted} numberOfLines={2} style={{ marginTop: 2 }}>{it.detail}</T> : null}
                {it.action ? <T v="small" color={p.teal} style={{ marginTop: 3 }}>{it.action} →</T> : null}
              </View>
            </Row>
          </Pressable>
        );
      }) : <T v="body" color={p.muted}>{data.headline}</T>}
    </Card>
  );
}
