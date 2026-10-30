// Galaxy Watch (Samsung Health) — Android only. Reads what Samsung Health syncs into Health Connect and uploads it to
// the longitudinal record (source 'galaxy'). The user taps Allow on the Health Connect sheet; nothing is read before that.
import { Stack } from 'expo-router';
import React, { useCallback, useEffect, useState } from 'react';
import { AppState, View } from 'react-native';

import { Galaxy, GALAXY_AVAILABLE, type GalaxyLast, type GalaxyStatus } from '@/lib/galaxy';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

const NOTE: Record<GalaxyStatus, string> = {
  unsupported: 'Galaxy Watch sync is for Android phones. On iPhone, use the patch, ring or Apple Health.',
  unavailable: 'Health Connect is not available on this phone.',
  'update-required': 'Health Connect needs an update from the Play Store before Telomy can read it.',
  'needs-permission': 'Allow Telomy to read heart rate, SpO₂, sleep, steps, VO₂max and body composition that Samsung Health saves.',
  ready: 'Connected. New Samsung Health data uploads automatically whenever Telomy opens.',
};
const LABEL: Record<string, string> = { hr: 'Heart rate', rhr: 'Resting HR', spo2: 'SpO₂', steps: 'Steps', vo2max: 'VO₂max', body_fat_pct: 'Body fat', bmr: 'BMR', weight_kg: 'Weight', lean_mass_kg: 'Lean mass', sleep_tst_min: 'Sleep nights', sleep_deep_min: 'Deep', sleep_rem_min: 'REM', sleep_light_min: 'Light', sleep_awake_min: 'Awake' };

export default function GalaxyScreen() {
  const p = usePalette();
  const { toast, show } = useToast();
  const [status, setStatus] = useState<GalaxyStatus | null>(null);
  const [last, setLast] = useState<GalaxyLast | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => { setStatus(await Galaxy.status()); setLast(await Galaxy.last()); }, []);
  useEffect(() => {
    refresh();
    const s = AppState.addEventListener('change', (st) => { if (st === 'active') refresh(); });
    return () => s.remove();
  }, [refresh]);

  async function connect() {
    setBusy(true);
    const r = await Galaxy.connect();
    await refresh(); setBusy(false);
    show(r.ok ? 'Connected to Health Connect.' : (r.error ?? 'Not connected.'), r.ok ? 'success' : 'alert');
    if (r.ok) syncNow();
  }
  async function syncNow() {
    setBusy(true);
    const r = await Galaxy.sync(true);
    await refresh(); setBusy(false);
    show(r?.error ? `Sync failed: ${r.error}` : `Uploaded ${r?.sent ?? 0} readings.`, r?.error ? 'alert' : 'success');
  }

  const st = GALAXY_AVAILABLE ? status : 'unsupported';
  const ok = st === 'ready';
  const counts = last ? Object.entries(last.byMetric) : [];

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Galaxy Watch' }} />
      <View style={{ gap: space[1] }}>
        <T v="h1">Galaxy Watch</T>
        <T v="small" color={p.muted}>Your watch's computed health data, via Samsung Health and Health Connect, joins your Telomy record.</T>
      </View>

      <Card tone={ok ? 'teal' : 'copper'}>
        <Row>
          <Icon name="applewatch" color={ok ? p.teal : p.copper} />
          <View style={{ flex: 1 }}>
            <T v="label">{st == null ? 'Checking…' : ok ? 'Connected' : st === 'needs-permission' ? 'Permission needed' : 'Unavailable'}</T>
            <T v="small" color={p.muted}>{st == null ? 'Looking for Health Connect.' : NOTE[st]}</T>
          </View>
          {st === 'needs-permission' ? <Button kind="secondary" title="Allow" onPress={connect} disabled={busy} /> : null}
          {ok ? <Button kind="secondary" title={busy ? 'Syncing…' : 'Sync now'} onPress={syncNow} disabled={busy} /> : null}
        </Row>
      </Card>

      {ok ? (
        <Section title="Last upload">
          {!last ? (
            <Card><T v="small" color={p.muted}>Nothing uploaded yet. Tap Sync now. Samsung Health can take 30–60 minutes to pass new watch data to Health Connect.</T></Card>
          ) : last.error ? (
            <Card tone="copper"><T v="small">Last attempt failed: {last.error}. It will retry next time Telomy opens.</T></Card>
          ) : counts.length === 0 ? (
            <Card><T v="small" color={p.muted}>Connected, but Health Connect has no Samsung Health data yet. Open Samsung Health once and make sure the watch has synced.</T></Card>
          ) : (
            <Card style={{ gap: space[2] }}>
              <T v="small" color={p.muted}>{new Date(last.at).toLocaleString()} · {last.sent} readings</T>
              {counts.map(([k, n]) => (
                <Row key={k}><T v="body" style={{ flex: 1 }}>{LABEL[k] ?? k}</T><T v="num">{n}</T></Row>
              ))}
            </Card>
          )}
        </Section>
      ) : null}

      <Card>
        <T v="label">What this covers</T>
        <T v="small" color={p.muted}>Heart rate, resting HR, SpO₂, sleep with stages, steps, VO₂max, body fat, BMR, weight. Skeletal muscle, body water, HRV and Energy Score are not shared by Samsung Health through Health Connect.</T>
      </Card>
      {GALAXY_AVAILABLE && st !== 'unavailable' ? <Button kind="secondary" title="Health Connect settings" onPress={() => Galaxy.openSettings()} /> : null}
      {toast}
    </Screen>
  );
}
