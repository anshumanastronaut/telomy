import React from 'react';
import { View } from 'react-native';

import { usePalette } from '@/lib/theme';

import { Card, Chip, Divider, Row, Section, T } from './core';

const LBL: Record<string, string> = { total_cvd: 'Any cardiovascular disease', ascvd: 'Heart attack or stroke', heart_failure: 'Heart failure', chd: 'Coronary heart disease', stroke: 'Stroke' };

function bar(p: any, v: number | null, max = 50) {
  const col = v == null ? p.faint : v >= 20 ? p.danger : v >= 7.5 ? p.warn : p.success;
  return <View style={{ height: 6, borderRadius: 3, backgroundColor: p.surfaceAlt, overflow: 'hidden', flex: 1 }}><View style={{ width: `${Math.min(100, ((v ?? 0) / max) * 100)}%`, height: 6, backgroundColor: col }} /></View>;
}

export function PredictionCards({ models }: { models: any }) {
  const p = usePalette();
  const pv = models.prevent;
  return (
    <>
      <Section title="Cardiovascular · AHA PREVENT (2024)">
        <Card>
          {pv.ten_year ? (
            <>
              <Row><T v="small" style={{ flex: 1 }}>Outcome</T><T v="small" style={{ width: 64, textAlign: 'right' }}>10 years</T><T v="small" style={{ width: 64, textAlign: 'right' }}>30 years</T></Row>
              {Object.keys(pv.ten_year).map((k) => (
                <View key={k} style={{ gap: 4, paddingVertical: 4 }}>
                  <Row>
                    <T v="body" style={{ flex: 1 }}>{LBL[k]}</T>
                    <T v="num" style={{ fontSize: 16, width: 64, textAlign: 'right' }}>{pv.ten_year[k]}%</T>
                    <T v="num" style={{ fontSize: 16, width: 64, textAlign: 'right' }}>{pv.thirty_year?.[k]}%</T>
                  </Row>
                  {bar(p, pv.thirty_year?.[k])}
                </View>
              ))}
            </>
          ) : <T v="small">Needs: {pv.missing.join(', ')}</T>}
          <T v="small">{pv.citation}</T>
        </Card>
      </Section>
      <Section title="Heart attack or stroke · Pooled Cohort Equations">
        <Card>
          <Row><T v="num" style={{ flex: 1 }}>{models.cvd.risk ?? '—'}%</T><Chip label={models.cvd.band ?? 'not computed'} /></Row>
          {models.cvd.enhancers?.length ? (
            <>
              <T v="label">Risk enhancers (raise risk beyond the equation)</T>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>{models.cvd.enhancers.map((e: string) => <Chip key={e} label={e} fg={p.danger} bg={p.dangerSoft} />)}</View>
            </>
          ) : null}
          <T v="small">{models.cvd.caveat}</T>
        </Card>
      </Section>
      <Section title="Other conditions">
        <Card style={{ paddingVertical: 4 }}>
          {[
            ['Type 2 diabetes · 5 years', models.diabetes.already ? 'In diabetes range' : models.diabetes.risk != null ? `${models.diabetes.risk}%` : '—', models.diabetes.band, models.diabetes.model],
            ['Advanced liver fibrosis · FIB-4', models.liver.score ?? '—', models.liver.band, models.liver.model],
            ['Kidney failure · 5 years', models.kidney.risk != null ? `${models.kidney.risk}%` : '—', models.kidney.band, models.kidney.model],
          ].map(([t, v, b, m], i) => (
            <View key={t as string}>
              {i ? <Divider /> : null}
              <View style={{ paddingVertical: 10, gap: 2 }}>
                <Row><T v="body" style={{ flex: 1, fontWeight: '500' }}>{t}</T><T v="num" style={{ fontSize: 17 }}>{v}</T></Row>
                {b ? <T v="small">{b}</T> : null}
                <T v="small" color={p.faint}>{m}</T>
              </View>
            </View>
          ))}
        </Card>
      </Section>
    </>
  );
}
