import React, { useState } from 'react';
import { View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Button, Card, Chip, Icon, Loading, Row, Screen, Section, Segmented, T, useToast } from '@/ui/core';

export default function Plans() {
  const p = usePalette();
  const { data, reload } = useApi<any>('/plans');
  const [billing, setBilling] = useState<'month' | 'year'>('year');
  const { toast, show } = useToast();
  if (!data) return <Screen edges={[]}><Loading what="Loading plans…" /></Screen>;
  const cur = data.subscription.plan;
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Segmented options={[{ key: 'month', label: 'Monthly' }, { key: 'year', label: 'Yearly · save ~17%' }]} value={billing} onChange={setBilling} />
        {data.plans.map((pl: any) => {
          const price = billing === 'year' ? pl.price_year : pl.price_month;
          const on = pl.id === cur;
          return (
            <Card key={pl.id} tone={pl.popular ? 'teal' : undefined} style={on ? { borderColor: p.teal, borderWidth: 2 } : undefined}>
              <Row>
                <T v="h2" style={{ flex: 1 }}>{pl.name}</T>
                {pl.popular ? <Chip label="Most popular" fg="#fff" bg={p.teal} /> : null}
                {on ? <Chip label="Your plan" fg={p.success} bg={p.successSoft} /> : null}
              </Row>
              <T v="num">{price ? `₹${price.toLocaleString('en-IN')}` : '₹0'}<T v="small">{price ? (billing === 'year' ? ' / year' : ' / month') : ''}</T></T>
              {pl.features.map((f: string) => <Row key={f} style={{ alignItems: 'flex-start' }}><Icon name="checkmark" size={13} color={p.teal} /><T v="body" style={{ flex: 1 }}>{f}</T></Row>)}
              {!on ? <Button kind={pl.popular ? 'primary' : 'secondary'} title={pl.price_month ? `Choose ${pl.name}` : 'Switch to Free'} onPress={async () => { const r = await api('/subscription', { body: { plan: pl.id, billing } }); show(r.message, 'success'); reload(); }} /> : null}
            </Card>
          );
        })}
        <Section title="Consult on demand (any plan)">
          <Card>
            {Object.entries(data.on_demand).map(([k, v]: any) => <Row key={k}><T v="body" style={{ flex: 1 }}>{v.name} · {v.minutes} min</T><T v="body" style={{ fontWeight: '600' }}>₹{v.price}</T></Row>)}
            <T v="small">Includes an automatic pre-clinic brief so the doctor sees your data before the call.</T>
          </Card>
        </Section>
        <T v="small">Test mode: no payment is taken. Prices benchmarked against Practo (₹799 GP consult, Plus ₹1,199/month) and clinician-reviewed services such as Function Health ($365/yr).</T>
      </Screen>
      {toast}
    </View>
  );
}
