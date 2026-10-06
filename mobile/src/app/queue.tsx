import React from 'react';

import { useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Empty, Loading, Screen, T } from '@/ui/core';
import { InsightCard } from '@/ui/insight';

export default function Queue() {
  const p = usePalette();
  const { data } = useApi<any[]>('/care/queue');
  return (
    <Screen edges={[]}>
      <T v="body" color={p.muted}>Sinc drafts that touch medical decisions wait here for a clinician. In Telomy Care, Dr. Meera Rao signs off, modifies or rejects each one with a note.</T>
      {!data ? <Loading what="Loading queue…" /> : data.length ? data.map((i) => <InsightCard key={i.id} i={i} />) : <Empty title="Nothing awaiting review" body="Every medical-adjacent draft has been reviewed." />}
    </Screen>
  );
}
