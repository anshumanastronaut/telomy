// Disease-prediction cards — each validated risk model with its number, a plain-language interpretation, and the
// rationale: exactly which of your values drove it (flagged against reference ranges), the risk enhancers and
// caveats the equation can't see, and the citation. Tap a card to open the full "why this number".
import React from 'react';
import { View } from 'react-native';

import { usePalette } from '@/lib/theme';
import { Card, Chip, Divider, Row, Section, T } from './core';

const LBL: Record<string, string> = { total_cvd: 'Any cardiovascular disease', ascvd: 'Heart attack or stroke', heart_failure: 'Heart failure', chd: 'Coronary heart disease', stroke: 'Stroke' };

// Reference flags for the drivers we surface. level: ok | watch | high.
function flag(key: string, v: any): { level: 'ok' | 'watch' | 'high'; note: string } | null {
  if (v == null || v === '') return null;
  const n = typeof v === 'number' ? v : Number(v);
  const F = (level: any, note: string) => ({ level, note });
  switch (key) {
    case 'ldl': return n >= 160 ? F('high', 'high') : n >= 100 ? F('watch', 'above optimal') : F('ok', 'optimal');
    case 'apob': return n >= 100 ? F('high', 'high') : n >= 90 ? F('watch', 'borderline') : F('ok', 'optimal');
    case 'tc': return n >= 240 ? F('high', 'high') : n >= 200 ? F('watch', 'borderline') : F('ok', 'desirable');
    case 'hdl': return n < 40 ? F('watch', 'low') : F('ok', 'protective');
    case 'sbp': return n >= 140 ? F('high', 'stage 2') : n >= 130 ? F('watch', 'stage 1') : n >= 120 ? F('watch', 'elevated') : F('ok', 'normal');
    case 'hba1c': return n >= 6.5 ? F('high', 'diabetes range') : n >= 5.7 ? F('watch', 'prediabetes') : F('ok', 'normal');
    case 'glucose': return n >= 126 ? F('high', 'diabetes range') : n >= 100 ? F('watch', 'impaired fasting') : F('ok', 'normal');
    case 'hscrp': return n > 3 ? F('high', 'high inflammation') : n >= 1 ? F('watch', 'moderate') : F('ok', 'low');
    case 'cac': return n >= 400 ? F('high', 'extensive plaque') : n >= 100 ? F('watch', 'moderate plaque') : n > 0 ? F('watch', 'plaque present') : F('ok', 'no plaque');
    case 'lpa': return n >= 50 ? F('high', 'high (genetic)') : n >= 30 ? F('watch', 'borderline') : F('ok', 'normal');
    case 'egfr': return n < 60 ? F('high', 'reduced (CKD)') : n < 90 ? F('watch', 'mildly reduced') : F('ok', 'normal');
    case 'uacr': return n >= 30 ? F('high', 'albuminuria') : F('ok', 'normal');
    case 'bmi': return n >= 30 ? F('high', 'obese') : n >= 25 ? F('watch', 'overweight') : F('ok', 'healthy');
    case 'ast': return n > 40 ? F('watch', 'above range') : F('ok', 'normal');
    case 'alt': return n > 40 ? F('watch', 'above range') : F('ok', 'normal');
    default: return null;
  }
}
const UNIT: Record<string, string> = { ldl: ' mg/dL', apob: ' mg/dL', tc: ' mg/dL', hdl: ' mg/dL', sbp: ' mmHg', hba1c: '%', glucose: ' mg/dL', hscrp: ' mg/L', cac: '', lpa: ' mg/dL', egfr: '', uacr: ' mg/g', bmi: '', ast: ' U/L', alt: ' U/L' };
const NAME: Record<string, string> = { ldl: 'LDL cholesterol', apob: 'ApoB', tc: 'Total cholesterol', hdl: 'HDL', sbp: 'Systolic BP', hba1c: 'HbA1c', glucose: 'Fasting glucose', hscrp: 'hs-CRP', cac: 'Coronary calcium', lpa: 'Lp(a)', egfr: 'eGFR', uacr: 'Urine ACR', bmi: 'BMI', ast: 'AST', alt: 'ALT', family_history_dm: 'Family history of diabetes', smoker: 'Smoking', active: 'Physically active' };

function Drivers({ keys, inputs }: { keys: string[]; inputs: any }) {
  const p = usePalette();
  const tone = (l: string) => l === 'high' ? p.danger : l === 'watch' ? p.warn : p.success;
  return (
    <View style={{ gap: 6, marginTop: 8 }}>
      <T v="label" color={p.muted}>What's driving this</T>
      {keys.map((k) => {
        const v = inputs[k];
        if (v == null) return null;
        if (typeof v === 'boolean') return <Row key={k}><T v="body" style={{ flex: 1 }}>{NAME[k] ?? k}</T><Chip label={v ? 'yes' : 'no'} fg={v && (k === 'smoker') ? p.danger : p.muted} bg={p.surfaceAlt} /></Row>;
        const f = flag(k, v);
        return (
          <Row key={k}>
            <T v="body" style={{ flex: 1 }}>{NAME[k] ?? k}</T>
            <T v="num" style={{ width: 70, textAlign: 'right' }}>{typeof v === 'number' ? Math.round(v * 10) / 10 : v}{UNIT[k] ?? ''}</T>
            {f ? <Chip label={f.note} fg={tone(f.level)} bg={p.surfaceAlt} /> : <View style={{ width: 8 }} />}
          </Row>
        );
      })}
    </View>
  );
}

function band(p: any, s: string | undefined) {
  const t = (s || '').toLowerCase();
  const c = /high|severe|extensive/.test(t) ? { fg: p.danger, bg: p.dangerSoft } : /moder|borderline|elevated|stage|indeterm|prediab/.test(t) ? { fg: p.warn, bg: p.warnSoft } : { fg: p.success, bg: p.surfaceAlt };
  return s ? <Chip label={s} fg={c.fg} bg={c.bg} /> : null;
}

export function PredictionCards({ models, inputs = {} }: { models: any; inputs?: any }) {
  const p = usePalette();
  const [open, setOpen] = React.useState<Record<string, boolean>>({ prevent: true });
  const pv = models.prevent;
  const Tog = ({ id, children }: { id: string; children: React.ReactNode }) => (
    <Card onPress={() => setOpen((s) => ({ ...s, [id]: !s[id] }))}>{children}</Card>
  );

  return (
    <>
      <Section title="Cardiovascular · AHA PREVENT (2024)">
        <Tog id="prevent">
          {pv.ten_year ? (
            <>
              <Row><T v="small" style={{ flex: 1 }}>Outcome</T><T v="small" style={{ width: 60, textAlign: 'right' }}>10 yr</T><T v="small" style={{ width: 60, textAlign: 'right' }}>30 yr</T></Row>
              {Object.keys(pv.ten_year).map((k) => (
                <Row key={k} style={{ paddingVertical: 3 }}>
                  <T v="body" style={{ flex: 1 }}>{LBL[k]}</T>
                  <T v="num" style={{ fontSize: 15, width: 60, textAlign: 'right' }}>{pv.ten_year[k]}%</T>
                  <T v="num" style={{ fontSize: 15, width: 60, textAlign: 'right' }} color={pv.thirty_year?.[k] >= 20 ? p.danger : pv.thirty_year?.[k] >= 7.5 ? p.warn : undefined}>{pv.thirty_year?.[k]}%</T>
                </Row>
              ))}
              {open.prevent ? <Drivers inputs={inputs} keys={['ldl', 'apob', 'hdl', 'sbp', 'bp_treated', 'smoker', 'hba1c', 'hscrp', 'cac', 'lpa', 'egfr']} /> : <T v="small" color={p.faint} style={{ marginTop: 6 }}>Tap for what's driving it →</T>}
            </>
          ) : <T v="small">Needs: {pv.missing.join(', ')}</T>}
          <T v="small" color={p.faint} style={{ marginTop: 8 }}>{pv.citation}</T>
        </Tog>
      </Section>

      <Section title="Heart attack or stroke · Pooled Cohort Equations">
        <Tog id="cvd">
          <Row style={{ alignItems: 'center' }}><T v="display" style={{ flex: 1, fontSize: 30 }}>{models.cvd.risk ?? '—'}%</T>{band(p, models.cvd.band)}</Row>
          <T v="small" color={p.muted}>{models.cvd.outcome}</T>
          {models.cvd.enhancers?.length ? (
            <View style={{ marginTop: 8 }}>
              <T v="label" color={p.muted}>Risk enhancers (beyond the equation)</T>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>{models.cvd.enhancers.map((e: string) => <Chip key={e} label={e} fg={p.danger} bg={p.dangerSoft} />)}</View>
            </View>
          ) : null}
          {open.cvd ? <Drivers inputs={inputs} keys={['ldl', 'apob', 'tc', 'hdl', 'sbp', 'hscrp', 'cac', 'lpa']} /> : null}
          {models.cvd.caveat ? <T v="small" color={p.warn} style={{ marginTop: 8 }}>⚠ {models.cvd.caveat}</T> : null}
          <T v="small" color={p.faint} style={{ marginTop: 6 }}>{models.cvd.citation}</T>
        </Tog>
      </Section>

      <Section title="Metabolic, liver & kidney">
        {[
          { id: 'diabetes', title: 'Type 2 diabetes · 5 years', val: models.diabetes.already ? 'In range' : models.diabetes.risk != null ? `${models.diabetes.risk}%` : '—', m: models.diabetes, keys: ['hba1c', 'glucose', 'bmi', 'family_history_dm', 'active'] },
          { id: 'liver', title: 'Advanced liver fibrosis · FIB-4', val: models.liver.score ?? '—', m: models.liver, keys: ['ast', 'alt'] },
          { id: 'kidney', title: 'Kidney failure · 5 years', val: models.kidney.risk != null ? `${models.kidney.risk}%` : '—', m: models.kidney, keys: ['egfr', 'uacr'] },
        ].map((row) => (
          <Card key={row.id} onPress={() => setOpen((s) => ({ ...s, [row.id]: !s[row.id] }))} style={{ marginBottom: 10 }}>
            <Row style={{ alignItems: 'center' }}>
              <View style={{ flex: 1 }}><T v="h3">{row.title}</T><T v="small" color={p.faint}>{row.m.model}</T></View>
              <T v="num" style={{ fontSize: 20, marginRight: 8 }}>{row.val}</T>
              {band(p, row.m.band)}
            </Row>
            {open[row.id] ? (
              <>
                <T v="small" color={p.muted} style={{ marginTop: 6 }}>{row.m.outcome}</T>
                {row.m.band && /not applicable|above the CKD/.test(row.m.band) ? null : <Drivers inputs={inputs} keys={row.keys} />}
                <T v="small" color={p.faint} style={{ marginTop: 8 }}>{row.m.citation}</T>
              </>
            ) : null}
          </Card>
        ))}
      </Section>
    </>
  );
}
