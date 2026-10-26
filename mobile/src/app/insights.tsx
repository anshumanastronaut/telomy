// "What affects you" — the discovery feed. Surfaces Telomy's own correlation engine (/insights): behavioural
// event-effects (alcohol → HRV), signal correlations (Pearson + lag + Fisher-z, with r/p/n receipts), cross-panel
// lab patterns and trends — as plain-language cards you can tap open to see the data and the method behind each one.
// Inspired by the discovery feeds people love, but grounded in our own statistics (effect size, 95% CI, p, n).
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, Chip, ErrorState, Loading, Row, Screen, Section, T } from '@/ui/core';

type Insight = {
  id: string; kind: string; title: string; body: string; confidence: number;
  receipts?: { method?: string; n?: number; r?: number; p?: number; direction?: string };
  evidence?: any[]; dismissed?: number; created_at: string;
};

const GROUPS = [
  { key: 'affects', kinds: ['event_effect'], title: 'What affects you', sub: 'Things you log, and what they do to your body — usually the next day' },
  { key: 'signals', kinds: ['signal_correlation'], title: 'How your signals move together', sub: 'Patterns across your wearable metrics over months' },
  { key: 'patterns', kinds: ['cross_panel'], title: 'Patterns across your health', sub: 'What your labs, genetics and vitals reveal together' },
  { key: 'trends', kinds: ['lab_trend'], title: 'Trends over time', sub: 'Where your numbers are heading' },
];

const HARM = /alcohol|late meal|caffeine|stress|smoking|poor|travel/i;
const HELP = /sauna|magnesium|exercise|workout|steps|sleep|cold|cryo|walk|protein|fibre|fiber|meditat|breath/i;

export default function Insights() {
  const p = usePalette();
  const { data, loading, error, reload } = useApi<Insight[]>('/insights');
  const [open, setOpen] = React.useState<Record<string, boolean>>({});
  if (error) return <Screen><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen><Loading what="Analysing your data…" /></Screen>;

  const accent = (ins: Insight) => {
    const subj = ins.title.split('→')[0] || ins.title;
    if (ins.kind === 'event_effect') {
      if (HARM.test(subj)) return { fg: p.copper, bg: p.copperSoft };
      if (HELP.test(subj)) return { fg: p.teal, bg: p.tealSoft };
    }
    return { fg: p.muted, bg: p.surfaceAlt };
  };
  const stat = (ins: Insight) => {
    const r = ins.receipts || {};
    const bits: string[] = [];
    if (r.n != null) bits.push(`${r.n} days`);
    if (r.r != null) bits.push(`r = ${r.r}`);
    if (r.p != null) bits.push(r.p < 0.001 ? 'p < 0.001' : `p = ${r.p}`);
    return bits.join('   ·   ');
  };

  const total = data.filter((i) => !i.dismissed).length;

  return (
    <Screen onRefresh={reload} refreshing={loading}>
      <View style={{ marginBottom: space[2] }}>
        <T v="h1">What affects you</T>
        <T v="small" color={p.muted}>
          {total} patterns found in your own data. These are correlations in your life — not proof of cause. Tap any card to see the data and the method behind it.
        </T>
      </View>

      {GROUPS.map((g) => {
        const items = data.filter((i) => g.kinds.includes(i.kind) && !i.dismissed)
          .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0));
        if (!items.length) return null;
        return (
          <Section key={g.key} title={g.title}>
            <T v="small" color={p.faint} style={{ marginTop: -2, marginBottom: space[1] }}>{g.sub}</T>
            {items.map((ins) => {
              const a = accent(ins);
              const isOpen = !!open[ins.id];
              const s = stat(ins);
              return (
                <Card key={ins.id} onPress={() => setOpen((st) => ({ ...st, [ins.id]: !st[ins.id] }))} style={{ marginBottom: space[2] }}>
                  <Row gap={space[2]} style={{ alignItems: 'flex-start' }}>
                    <View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: a.fg, marginTop: 6 }} />
                    <View style={{ flex: 1 }}>
                      <T v="h3">{ins.title}</T>
                      {isOpen ? (
                        <>
                          <T v="body" style={{ marginTop: space[1] }}>{ins.body}</T>
                          {s ? (
                            <View style={{ marginTop: space[2] }}>
                              <Chip label={s} fg={a.fg} bg={a.bg} />
                              {ins.receipts?.method ? <T v="small" color={p.faint} style={{ marginTop: space[1] }}>{ins.receipts.method}</T> : null}
                            </View>
                          ) : null}
                        </>
                      ) : (
                        <T v="small" color={p.faint} style={{ marginTop: 2 }}>Tap to see the data →</T>
                      )}
                    </View>
                    <Chip label={`${Math.round((ins.confidence ?? 0) * 100)}%`} fg={a.fg} bg={a.bg} />
                  </Row>
                </Card>
              );
            })}
          </Section>
        );
      })}
    </Screen>
  );
}
