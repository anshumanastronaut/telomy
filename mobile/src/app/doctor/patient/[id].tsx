// Doctor's patient chart — the clinical workspace, not a data dump. Built the way a doctor works: understand the
// case (360 + AI summary), review what's flagged (findings awaiting sign-off), then ACT — prescribe an
// evidence-graded Longevity Rx, prescribe a contraindication-screened therapy (with the patient's own N-of-1
// response), and sign. Everything is drafted by Sinc from the patient's Vault; nothing is ordered until the
// doctor signs. Overview from /mgmt/clinic/patients/{id}/overview, actions from /plan.
import { router, Stack, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { Alert, Pressable, TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { BackButton, Button, Card, Chip, ErrorState, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

const GOALS: { key: string; label: string }[] = [
  { key: 'heart', label: 'Heart & lipids' }, { key: 'metabolic', label: 'Blood sugar' }, { key: 'longevity', label: 'Healthy ageing' },
  { key: 'sleep', label: 'Sleep' }, { key: 'recovery', label: 'Recovery' }, { key: 'muscle', label: 'Muscle' },
];
// What a doctor can turn on for a patient's own app
const FOCUS: [string, string][] = [['heart', 'Heart & lipids'], ['metabolic', 'Blood sugar'], ['bp', 'Blood pressure'], ['liver', 'Liver'], ['kidney', 'Kidney'], ['inflammation', 'Inflammation'], ['weight', 'Weight'], ['sleep', 'Sleep'], ['recovery', 'Recovery'], ['muscle', 'Muscle']];
const TRACK: [string, string][] = [['bp', 'Blood pressure'], ['glucose', 'Glucose'], ['weight', 'Weight'], ['steps', 'Steps'], ['sleep', 'Sleep'], ['symptoms', 'Symptoms'], ['meals', 'Meals'], ['mood', 'Mood'], ['pain', 'Pain']];
const TARGET_DEF: Record<string, { label: string; unit: string; def: number; step: number }> = {
  ldl: { label: 'LDL', unit: 'mg/dL', def: 70, step: 5 }, apob: { label: 'ApoB', unit: 'mg/dL', def: 80, step: 5 },
  hba1c: { label: 'HbA1c', unit: '%', def: 5.6, step: 0.1 }, sbp: { label: 'Systolic BP', unit: 'mmHg', def: 125, step: 5 },
  weight: { label: 'Weight', unit: 'kg', def: 75, step: 1 }, steps: { label: 'Steps/day', unit: '', def: 8000, step: 500 }, hscrp: { label: 'hs-CRP', unit: 'mg/L', def: 1, step: 0.5 },
};
const TEST_CATS = ['Heart', 'Metabolic', 'Liver', 'Kidney', 'Imaging', 'Cancer screening', 'Ageing', 'Hormones', 'Nutrients', 'Blood', 'Genetics'];

export default function DoctorPatient() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const p = usePalette();
  const { toast, show } = useToast();
  const [goal, setGoal] = React.useState('heart');
  const [signed, setSigned] = React.useState<Record<string, boolean>>({});
  const [chosen, setChosen] = React.useState<Record<string, boolean>>({});
  const [thAdded, setThAdded] = React.useState<Record<string, boolean>>({});
  const [thBusy, setThBusy] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const ov = useApi<any>(`/mgmt/clinic/patients/${id}/overview`, [id]);
  const plan = useApi<any>(`/mgmt/clinic/patients/${id}/plan?goal=${goal}`, [id, goal]);
  const cfg = useApi<any>(`/mgmt/clinic/patients/${id}/care-config`, [id]);

  // doctor-set care config (what the patient's app measures, shows and prioritises)
  const [focus, setFocus] = React.useState<string[]>([]);
  const [track, setTrack] = React.useState<string[]>([]);
  const [targets, setTargets] = React.useState<Record<string, number>>({});
  const [cfgNote, setCfgNote] = React.useState('');
  const loaded = React.useRef(false);
  React.useEffect(() => {
    if (cfg.data && !loaded.current) { loaded.current = true; setFocus(cfg.data.focus ?? []); setTrack(cfg.data.track ?? []); setTargets(cfg.data.targets ?? {}); setCfgNote(cfg.data.note ?? ''); }
  }, [cfg.data]);

  // order tests & scans
  const tcat = useApi<any[]>('/mgmt/clinic/tests');
  const ordered = useApi<any[]>(`/mgmt/clinic/patients/${id}/ordered-tests`, [id]);
  const templates = useApi<any[]>(`/mgmt/clinic/care-templates?org=${encodeURIComponent(staffOrg())}`);
  const [selTest, setSelTest] = React.useState<Record<string, boolean>>({});
  const [testReason, setTestReason] = React.useState('');
  const [showTests, setShowTests] = React.useState(false);
  async function orderTests() {
    const ids = Object.keys(selTest).filter((k) => selTest[k]);
    if (!ids.length) { show('Select at least one test.', 'alert'); return; }
    try { await api(`/mgmt/clinic/patients/${id}/order-tests`, { body: { test_ids: ids, reason: testReason } }); show(`Ordered ${ids.length} test(s) — the patient will see them.`, 'success'); setSelTest({}); setTestReason(''); setShowTests(false); ordered.reload(); }
    catch (e: any) { show(e.message, 'alert'); }
  }

  if (ov.error) return <Screen edges={['top']}><ErrorState message={ov.error} onRetry={ov.reload} /></Screen>;
  if (!ov.data) return <Screen edges={['top']}><Loading what="Opening the chart…" /></Screen>;

  const pt = ov.data.patient ?? {};
  const rm = ov.data.risk_models ?? {};
  const awaiting: any[] = plan.data?.awaiting ?? [];
  const rx = plan.data?.rx ?? {};
  const sup: any[] = rx.supplements ?? [];
  const med: any[] = rx.medicines ?? [];
  const therapies = plan.data?.therapies ?? {};
  const thOptions: any[] = (therapies.options ?? []).filter((t: any) => t.status !== 'not_suitable');
  const thResponse: any[] = therapies.response ?? [];

  const gradeTone = (g: string) => g === 'A' ? { fg: p.teal, bg: p.tealSoft } : g === 'B' ? { fg: p.teal, bg: p.tealSoft }
    : g === 'C' ? { fg: p.copper, bg: p.copperSoft } : { fg: p.faint, bg: p.surfaceAlt };

  async function signFinding(fid: string) {
    try { await api(`/mgmt/clinic/patients/${id}/findings/${fid}/sign`, { method: 'POST' }); setSigned((s) => ({ ...s, [fid]: true })); show('Signed.', 'success'); }
    catch (e: any) { show(e.message, 'alert'); }
  }
  async function prescribe() {
    const pick = [...sup, ...med].filter((i) => chosen[i.id]).map((i) => i.id);
    if (!pick.length) { show('Select at least one item to prescribe.', 'alert'); return; }
    setBusy(true);
    try { await api(`/mgmt/clinic/patients/${id}/prescribe`, { body: { goal, chosen: pick } }); show(`Prescribed ${pick.length} item(s) · signed.`, 'success'); setChosen({}); plan.reload(); }
    catch (e: any) { show(e.message, 'alert'); } finally { setBusy(false); }
  }
  const toggle = (arr: string[], set: (v: string[]) => void, k: string) => set(arr.includes(k) ? arr.filter((x) => x !== k) : [...arr, k]);
  const bump = (k: string, dir: number) => setTargets((t) => ({ ...t, [k]: Math.round(((t[k] ?? TARGET_DEF[k].def) + dir * TARGET_DEF[k].step) * 10) / 10 }));
  async function saveConfig() {
    try { await api(`/mgmt/clinic/patients/${id}/care-config`, { method: 'PUT', body: { focus, track, targets, note: cfgNote } }); show('Saved — your patient will see this in their app.', 'success'); cfg.reload(); }
    catch (e: any) { show(e.message, 'alert'); }
  }
  function applyTemplate(t: any) {
    setFocus(t.focus ?? []); setTrack(t.track ?? []); setTargets(t.targets ?? {}); setCfgNote(t.note ?? '');
    show(`Loaded "${t.name}" — review and save.`, 'success');
  }
  function saveTemplate() {
    Alert.prompt?.('Save as template', 'Name this preset (e.g. Cardiac patient)', async (name?: string) => {
      if (!name) return;
      try { await api('/mgmt/clinic/care-templates', { body: { name, focus, track, targets, note: cfgNote } }); show('Template saved.', 'success'); templates.reload(); }
      catch (e: any) { show(e.message, 'alert'); }
    });
  }

  const RxRow = ({ i }: { i: any }) => {
    const t = gradeTone(i.evidence);
    const on = !!chosen[i.id];
    return (
      <Card onPress={() => setChosen((c) => ({ ...c, [i.id]: !c[i.id] }))} style={{ marginBottom: space[2], borderWidth: on ? 2 : 1, borderColor: on ? p.teal : p.border }}>
        <Row style={{ alignItems: 'flex-start' }} gap={space[2]}>
          <View style={{ width: 20, height: 20, borderRadius: 6, borderWidth: 2, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.teal : 'transparent', alignItems: 'center', justifyContent: 'center', marginTop: 2 }}>
            {on ? <T v="small" color="#fff">✓</T> : null}
          </View>
          <View style={{ flex: 1 }}>
            <Row style={{ justifyContent: 'space-between' }}><T v="h3" style={{ flex: 1 }}>{i.name}</T><Chip label={`${i.evidence}`} fg={t.fg} bg={t.bg} /></Row>
            <T v="small" color={p.muted}>{i.dose}{i.price ? ` · ₹${i.price}/mo` : ''}{i.rx ? ' · Rx' : ''}</T>
            <T v="small" style={{ marginTop: 4 }}>{i.why}</T>
            {(i.interactions ?? []).length ? <T v="small" color={p.warn} style={{ marginTop: 4 }}>⚠ {i.interactions.map((x: any) => x.note).join(' · ')}</T> : null}
          </View>
        </Row>
      </Card>
    );
  };

  return (
    <Screen edges={['top']} onRefresh={() => { ov.reload(); plan.reload(); }} refreshing={ov.loading}>
      <Stack.Screen options={{ title: pt.name ?? 'Patient' }} />
      <BackButton fallback="/doctor/patients" />

      {/* case header */}
      <Card>
        <T v="h2">{pt.name ?? `#${id}`}</T>
        <T v="small" color={p.muted}>{[pt.age ? `${Math.round(pt.age)} y` : null, pt.sex, pt.city].filter(Boolean).join(' · ') || '—'}{pt.linked ? ' · live record' : ' · no linked record'}</T>
        {pt.conditions?.length ? <Row style={{ flexWrap: 'wrap', marginTop: 6 }}>{pt.conditions.map((c: string) => <Chip key={c} label={c} fg={p.danger} bg={p.dangerSoft} />)}</Row> : null}
      </Card>

      <Button kind="secondary" icon="sparkles" title="Ask Sinc about this patient"
        onPress={() => router.push(`/doctor/copilot?pid=${id}&name=${encodeURIComponent(pt.name ?? '')}` as any)} />

      {ov.data.ai_summary?.text ? (
        <Card tone="teal">
          <Row><T v="label" style={{ flex: 1 }}>Assessment · Sinc draft</T><Chip label="review" fg={p.teal} bg={p.surface} /></Row>
          <T v="body" style={{ marginTop: 4 }}>{ov.data.ai_summary.text}</T>
        </Card>
      ) : null}

      {/* doctor configures the patient's own app */}
      <Section title="Customise this patient's app">
        <Card style={{ gap: space[1] }}>
          <T v="small" color={p.muted}>What their app measures, shows and prioritises. Saved changes appear on their own screens.</T>

          {(templates.data ?? []).length ? (
            <>
              <T v="label" color={p.muted} style={{ marginTop: 8 }}>Apply a template</T>
              <Row style={{ flexWrap: 'wrap' }} gap={6}>
                {templates.data!.map((t) => <Pressable key={t.id} onPress={() => applyTemplate(t)}><Chip label={t.name} fg={p.teal} bg={p.tealSoft} /></Pressable>)}
              </Row>
            </>
          ) : null}

          <T v="label" color={p.muted} style={{ marginTop: 10 }}>Focus areas</T>
          <Row style={{ flexWrap: 'wrap' }} gap={6}>
            {FOCUS.map(([k, l]) => <Pressable key={k} onPress={() => toggle(focus, setFocus, k)}><Chip label={l} fg={focus.includes(k) ? '#fff' : p.muted} bg={focus.includes(k) ? p.teal : p.surfaceAlt} /></Pressable>)}
          </Row>

          <T v="label" color={p.muted} style={{ marginTop: 12 }}>Targets</T>
          {Object.entries(TARGET_DEF).map(([k, d]) => {
            const on = targets[k] != null;
            return (
              <Row key={k} style={{ alignItems: 'center' }}>
                <Pressable style={{ flex: 1 }} onPress={() => setTargets((t) => { const n = { ...t }; if (on) delete n[k]; else n[k] = d.def; return n; })}>
                  <T v="body" color={on ? undefined : p.faint}>{d.label}{d.unit ? ` (${d.unit})` : ''}</T>
                </Pressable>
                {on ? (
                  <Row gap={10} style={{ alignItems: 'center' }}>
                    <Pressable onPress={() => bump(k, -1)}><Chip label="−" fg={p.teal} bg={p.tealSoft} /></Pressable>
                    <T v="num" style={{ width: 56, textAlign: 'center' }}>{targets[k]}</T>
                    <Pressable onPress={() => bump(k, 1)}><Chip label="+" fg={p.teal} bg={p.tealSoft} /></Pressable>
                  </Row>
                ) : <Chip label="off" fg={p.faint} bg={p.surfaceAlt} />}
              </Row>
            );
          })}

          <T v="label" color={p.muted} style={{ marginTop: 12 }}>What to track</T>
          <Row style={{ flexWrap: 'wrap' }} gap={6}>
            {TRACK.map(([k, l]) => <Pressable key={k} onPress={() => toggle(track, setTrack, k)}><Chip label={l} fg={track.includes(k) ? '#fff' : p.muted} bg={track.includes(k) ? p.teal : p.surfaceAlt} /></Pressable>)}
          </Row>

          <T v="label" color={p.muted} style={{ marginTop: 12 }}>Note to the patient</T>
          <TextInput value={cfgNote} onChangeText={setCfgNote} placeholder="e.g. Let's get your ApoB under 80 — recheck in 12 weeks." placeholderTextColor={p.faint} multiline
            style={{ borderWidth: 1, borderColor: p.border, borderRadius: 10, padding: 10, minHeight: 64, color: p.text, fontFamily: 'HankenGrotesk_400Regular', marginTop: 4, textAlignVertical: 'top' }} />
          <Button kind="primary" title="Save to patient's app" onPress={saveConfig} style={{ marginTop: 10 }} />
          <Button kind="ghost" title="Save current as a template" onPress={saveTemplate} />
          {cfg.data?.set_by ? <T v="small" color={p.faint} style={{ marginTop: 4 }}>Last set by {cfg.data.set_by}{cfg.data.set_at ? ` · ${cfg.data.set_at.slice(0, 10)}` : ''}</T> : null}
        </Card>
      </Section>

      {/* findings awaiting review — with Sign */}
      <Section title={`Findings awaiting your review · ${awaiting.length}`}>
        {!plan.data ? <Loading what="Loading plan…" /> : awaiting.length ? awaiting.map((f: any) => (
          <Card key={f.id} style={{ marginBottom: space[2], opacity: signed[f.id] ? 0.5 : 1 }}>
            <T v="h3">{f.title}</T>
            <T v="small" color={p.muted} style={{ marginTop: 4 }} numberOfLines={4}>{f.body}</T>
            <Row style={{ justifyContent: 'space-between', marginTop: 10, alignItems: 'center' }}>
              <Chip label={`${Math.round((f.confidence ?? 0) * 100)}% confidence`} fg={p.muted} bg={p.surfaceAlt} />
              <Button kind={signed[f.id] ? 'ghost' : 'secondary'} title={signed[f.id] ? 'Signed ✓' : 'Sign off'} disabled={!!signed[f.id]} onPress={() => signFinding(f.id)} />
            </Row>
          </Card>
        )) : <Card><T v="small">Nothing awaiting review.</T></Card>}
      </Section>

      {/* Prescribe — Longevity Rx */}
      <Section title="Prescribe · Longevity Rx">
        <Row style={{ flexWrap: 'wrap', marginBottom: space[2] }} gap={6}>
          {GOALS.map((g) => <Pressable key={g.key} onPress={() => setGoal(g.key)}><Chip label={g.label} fg={goal === g.key ? '#fff' : p.muted} bg={goal === g.key ? p.teal : p.surfaceAlt} /></Pressable>)}
        </Row>
        {!plan.data ? <Loading what="Drafting…" /> : (
          <>
            {med.length ? <><T v="label" color={p.muted} style={{ marginBottom: 6 }}>Medicines (triggered by their data)</T>{med.map((i) => <RxRow key={i.id} i={i} />)}</> : null}
            {sup.length ? <><T v="label" color={p.muted} style={{ marginBottom: 6, marginTop: 4 }}>Supplements</T>{sup.map((i) => <RxRow key={i.id} i={i} />)}</> : null}
            {!med.length && !sup.length ? <Card><T v="small">No Rx indicated for this goal from their current data.</T></Card> : null}
            <Button kind="primary" title={busy ? 'Signing…' : 'Approve & sign selected'} disabled={busy} onPress={prescribe} style={{ marginTop: 4 }} />
            <T v="small" color={p.faint} style={{ marginTop: 6 }}>Telomy Formulas are FSSAI nutraceuticals. Rx medicines are prescriber-gated. You sign before anything is ordered.</T>
          </>
        )}
      </Section>

      {/* Prescribe therapy — screened + N-of-1 response */}
      <Section title="Prescribe therapy">
        {!plan.data ? <Loading what="Screening…" /> : (
          <Card style={{ gap: space[2] }}>
            {thOptions.slice(0, 12).map((t: any) => {
              const resp = thResponse.find((r: any) => r.modality === t.modality);
              const tone = t.status === 'ok' ? { fg: p.teal, bg: p.tealSoft } : { fg: p.warn, bg: p.warnSoft };
              return (
                <Row key={t.modality} style={{ alignItems: 'center' }}>
                  <View style={{ flex: 1 }}>
                    <T v="body">{t.name}</T>
                    {resp?.verdict ? <T v="small" color={resp.verdict === 'helped' ? p.teal : p.muted}>Their data: {resp.verdict}</T> : <T v="small" color={p.faint}>{t.summary}</T>}
                  </View>
                  <Chip label={t.status === 'ok' ? 'suitable' : 'caution'} fg={tone.fg} bg={tone.bg} />
                  <Button kind="ghost" disabled={thAdded[t.modality] || thBusy === t.modality}
                    title={thAdded[t.modality] ? 'Added ✓' : thBusy === t.modality ? '…' : 'Prescribe'}
                    onPress={async () => {
                      setThBusy(t.modality);
                      try {
                        await api(`/mgmt/clinic/patients/${id}/prescribe-therapy`, { body: { modality: t.modality } });
                        setThAdded((s) => ({ ...s, [t.modality]: true }));
                        show(`${t.name} prescribed — sessions booked, visible in the patient's app.`, 'success');
                        plan.reload();
                      } catch (e: any) { show(e.message, 'alert'); } finally { setThBusy(null); }
                    }} />
                </Row>
              );
            })}
          </Card>
        )}
      </Section>

      {/* order tests & scans */}
      <Section title="Order tests & scans">
        <Card style={{ gap: space[1] }}>
          {(ordered.data ?? []).length ? ordered.data!.map((o: any) => (
            <Row key={o.id} style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <View style={{ flex: 1 }}><T v="body">{o.name}</T><T v="small" color={p.faint}>{o.category}{o.reason ? ` · ${o.reason}` : ''}</T></View>
              <Chip label={o.status} fg={o.status === 'ordered' ? p.copper : p.teal} bg={o.status === 'ordered' ? p.copperSoft : p.tealSoft} />
            </Row>
          )) : <T v="small" color={p.muted}>Nothing ordered yet.</T>}
          <Button kind={showTests ? 'ghost' : 'secondary'} title={showTests ? 'Close catalogue' : '+ Order a test or scan'} onPress={() => setShowTests(!showTests)} />
          {showTests ? (
            <View style={{ gap: 6 }}>
              <TextInput value={testReason} onChangeText={setTestReason} placeholder="Reason (optional) — e.g. confirm fatty liver" placeholderTextColor={p.faint}
                style={{ borderWidth: 1, borderColor: p.border, borderRadius: 10, padding: 10, color: p.text, fontFamily: 'HankenGrotesk_400Regular' }} />
              {TEST_CATS.map((cat) => {
                const items = (tcat.data ?? []).filter((t: any) => t.category === cat);
                if (!items.length) return null;
                return (
                  <View key={cat}>
                    <T v="label" color={p.muted} style={{ marginTop: 6 }}>{cat}</T>
                    {items.map((t: any) => (
                      <Pressable key={t.id} onPress={() => setSelTest((s) => ({ ...s, [t.id]: !s[t.id] }))}>
                        <Row style={{ paddingVertical: 6 }} gap={10}>
                          <View style={{ width: 18, height: 18, borderRadius: 5, borderWidth: 2, borderColor: selTest[t.id] ? p.teal : p.border, backgroundColor: selTest[t.id] ? p.teal : 'transparent', alignItems: 'center', justifyContent: 'center' }}>{selTest[t.id] ? <T v="small" color="#fff">✓</T> : null}</View>
                          <T v="body" style={{ flex: 1 }}>{t.name}</T>
                          <T v="small" color={p.faint}>₹{t.price} · {t.evidence}</T>
                        </Row>
                      </Pressable>
                    ))}
                  </View>
                );
              })}
              <Button kind="primary" title="Order selected tests" onPress={orderTests} />
            </View>
          ) : null}
        </Card>
      </Section>

      {/* the 360 at a glance */}
      {(rm.prevent?.ten_year?.total_cvd != null) ? (
        <Section title="Risk (PREVENT)">
          <Card style={{ gap: space[1] }}>
            <Row style={{ justifyContent: 'space-between' }}><T v="body">10-yr total CVD</T><T v="body">{rm.prevent.ten_year.total_cvd}%</T></Row>
            {rm.prevent.thirty_year?.total_cvd != null ? <Row style={{ justifyContent: 'space-between' }}><T v="body">30-yr total CVD</T><T v="body">{rm.prevent.thirty_year.total_cvd}%</T></Row> : null}
          </Card>
        </Section>
      ) : null}

      <View style={{ height: space[8] }} />
      {toast}
    </Screen>
  );
}
