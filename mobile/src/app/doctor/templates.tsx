// Care templates — reusable per-patient presets (focus, targets, trackers, note). A doctor builds 'Cardiac' or
// 'Metabolic' once and applies it to any patient in one tap from the patient chart. This screen manages the set:
// review what each contains, and remove ones no longer needed. New templates are saved from a patient's chart.
import { Stack } from 'expo-router';
import React from 'react';
import { Alert, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { staffOrg } from '@/lib/staff';
import { space, usePalette } from '@/lib/theme';
import { BackButton, Button, Card, Chip, Empty, ErrorState, Loading, Row, Screen, T, useToast } from '@/ui/core';

const TARGET_LABEL: Record<string, string> = { ldl: 'LDL', apob: 'ApoB', sbp: 'SBP', dbp: 'DBP', hba1c: 'HbA1c', a1c: 'HbA1c', crp: 'hs-CRP', tg: 'Triglycerides', rhr: 'Resting HR', vo2: 'VO₂max' };

export default function CareTemplates() {
  const p = usePalette();
  const { show } = useToast();
  const org = staffOrg();
  const { data, error, reload, loading } = useApi<any>(`/mgmt/clinic/care-templates?org=${encodeURIComponent(org)}`);

  const remove = (t: any) =>
    Alert.alert('Delete template?', `"${t.name}" will be removed. Patients it was already applied to keep their settings.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { try { await api(`/mgmt/clinic/care-templates/${t.id}`, { method: 'DELETE' }); show('Deleted', 'success'); reload(); } catch (e: any) { show(e.message, 'alert'); } } },
    ]);

  if (error) return <Screen edges={['top']}><Stack.Screen options={{ title: 'Care templates' }} /><ErrorState message={error} onRetry={reload} /></Screen>;
  if (!data) return <Screen edges={['top']}><Stack.Screen options={{ title: 'Care templates' }} /><Loading what="Loading templates…" /></Screen>;

  return (
    <Screen edges={['top']} onRefresh={reload} refreshing={loading}>
      <Stack.Screen options={{ title: 'Care templates' }} />
      <BackButton fallback="/doctor/profile" />
      <T v="h1">Care templates</T>
      <T v="small" color={p.muted}>Presets for how a patient's app is set up — focus, targets, trackers and a note. Apply one to a patient from their chart. Build a new one by setting up a patient, then “Save as template”.</T>

      {data.length === 0 ? (
        <Empty title="No templates yet" body="Open a patient, set their focus and targets under “Customise this patient's app”, then tap “Save current as a template”. It'll appear here and on every patient's chart." />
      ) : (
        data.map((t: any) => {
          const targets = Object.entries(t.targets || {});
          return (
            <Card key={t.id} style={{ gap: space[2] }}>
              <Row style={{ alignItems: 'center' }}>
                <T v="h3" style={{ flex: 1 }}>{t.name}</T>
                {t.created_by ? <T v="small" color={p.faint}>by {t.created_by}</T> : null}
              </Row>
              {(t.focus || []).length ? (
                <Row gap={6} style={{ flexWrap: 'wrap' }}>
                  {t.focus.map((f: string) => <Chip key={f} label={f} fg={p.teal} bg={p.tealSoft} />)}
                </Row>
              ) : null}
              {targets.length ? (
                <View style={{ gap: 2 }}>
                  <T v="label" color={p.muted}>Targets</T>
                  <Row gap={6} style={{ flexWrap: 'wrap' }}>
                    {targets.map(([k, v]) => <Chip key={k} label={`${TARGET_LABEL[k] || k.toUpperCase()} ≤ ${v}`} fg={p.copper} bg={p.copperSoft} />)}
                  </Row>
                </View>
              ) : null}
              {(t.track || []).length ? <T v="small" color={p.muted}>Track: {t.track.join(' · ')}</T> : null}
              {t.note ? <T v="small" color={p.muted} style={{ fontStyle: 'italic' }}>“{t.note}”</T> : null}
              <Button kind="ghost" title="Delete" icon="trash" onPress={() => remove(t)} style={{ alignSelf: 'flex-start' }} />
            </Card>
          );
        })
      )}
      <View style={{ height: space[6] }} />
    </Screen>
  );
}
