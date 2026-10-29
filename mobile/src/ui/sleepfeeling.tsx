// "How did you sleep?" — a one-tap subjective morning rating, captured right next to the objective sleep score so
// we learn the person-specific gap between how sleep FELT and what the numbers said (sleep misperception is a real,
// useful signal). Rendered inline under the sleep dial AND as the /sleep-feeling screen from the morning notification.
// Backend: GET/POST /me/sleep-feeling.
import React, { useState } from 'react';
import { Pressable } from 'react-native';
import { api, useApi } from '@/lib/api';
import { space, usePalette } from '@/lib/theme';
import { Card, Row, T } from '@/ui/core';

const OPTIONS = [
  { r: 1, emoji: '😫', label: 'Awful' },
  { r: 2, emoji: '😕', label: 'Poor' },
  { r: 3, emoji: '😐', label: 'As usual' },
  { r: 4, emoji: '🙂', label: 'Good' },
  { r: 5, emoji: '🤩', label: 'Amazing' },
];

export function SleepFeeling({ onDone }: { onDone?: () => void } = {}) {
  const p = usePalette();
  const { data, reload } = useApi<any>('/me/sleep-feeling');
  const [sent, setSent] = useState<number | null>(null);
  const answered: number | null = data?.answered_today ? data?.today?.rating ?? null : sent;

  async function pick(r: number) {
    setSent(r);
    try { await api('/me/sleep-feeling', { body: { rating: r } }); reload(); onDone?.(); } catch {}
  }

  return (
    <Card style={{ gap: space[2] }}>
      <T v="h3">{answered ? 'How you felt this morning' : 'How did you sleep?'}</T>
      {!answered ? <T v="small" color={p.muted}>One tap — we learn what restorative sleep looks like for you, beyond the score.</T> : null}
      <Row style={{ justifyContent: 'space-between' }}>
        {OPTIONS.map((o) => {
          const on = answered === o.r;
          return (
            <Pressable key={o.r} onPress={() => pick(o.r)} style={{ alignItems: 'center', flex: 1, opacity: answered && !on ? 0.3 : 1 }}>
              <T style={{ fontSize: 26 }}>{o.emoji}</T>
              <T v="small" color={on ? p.teal : p.muted} style={{ fontSize: 10, marginTop: 2 }}>{o.label}</T>
            </Pressable>
          );
        })}
      </Row>
      {answered ? <Reconcile today={data?.today} patterns={data?.patterns} count={data?.count ?? 0} /> : null}
    </Card>
  );
}

// The point of the whole feature (per the "numbers aren't verdicts" idea): when how you FELT and the score
// disagree, say so plainly and side with your experience. One night is a data point, not a verdict.
function Reconcile({ today, patterns, count }: { today: any; patterns: any; count: number }) {
  const p = usePalette();
  const rating: number | undefined = today?.rating;
  const score: number | null = today?.objective?.sleep_score ?? null;
  if (rating != null && score != null) {
    if (rating >= 4 && score < 60)
      return <T v="small" color={p.teal}>Your numbers read low, but you said you feel refreshed — trust how you feel. One night is a data point, not a verdict.</T>;
    if (rating <= 2 && score >= 70)
      return <T v="small" color={p.copper}>The score looks good, but you don't feel it — that's real too, and worth noting. We'll watch for what's behind it.</T>;
  }
  return <PatternHint patterns={patterns} count={count} />;
}

function PatternHint({ patterns, count }: { patterns: any; count: number }) {
  const p = usePalette();
  const ss = patterns?.sleep_score;
  if (count >= 4 && ss?.felt_good != null && ss?.felt_poor != null) {
    const diff = ss.felt_good - ss.felt_poor;
    return (
      <T v="small" color={p.muted}>
        On nights you felt good your sleep score averaged {ss.felt_good} vs {ss.felt_poor} on rough nights
        {Math.abs(diff) < 5 ? ' — your feeling often diverges from the number, which is exactly what we learn from.' : '.'}
      </T>
    );
  }
  return <T v="small" color={p.faint}>Keep rating a few mornings — we'll show what good sleep looks like for you.</T>;
}
