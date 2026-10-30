// Multi-device fusion: Telomy works with any subset of { chest ECG patch, smart ring, Apple Health } and never fails
// when a device is missing. Each metric has a priority order (most accurate source first); when several devices report
// the same metric we pick the best and keep the others for comparison. With one device we use it; with none, scores
// fall back to what's available and the UI shows honest empty states.
import { useEffect, useState } from 'react';
import { Band, bandAvailable, useBand } from './band';
import { Ring, type RingStatus } from '../../modules/ky-ecg';
import { startRingHistory } from './ringhistory';
import { HEALTH_LABEL, useHealth } from './health';
import { JCVital, type JcSnapshot } from './jcvitalsource';

export type SourceId = 'patch' | 'ring' | 'jcvital' | 'health';
export const SOURCE_LABEL: Record<SourceId, string> = { patch: 'Chest ECG patch', ring: 'Smart ring', jcvital: 'JCVital V8 band', health: HEALTH_LABEL };

// Which sources can provide each metric, best first. "patch" = KY-E-B1 single-lead ECG (gold for HR/HRV/rhythm),
// "ring" = PPG + IMU + temp, "health" = Apple Watch / iPhone via HealthKit.
export const METRIC_SOURCES: Record<string, SourceId[]> = {
  hr: ['patch', 'ring', 'jcvital', 'health'],
  hrv: ['patch', 'ring', 'health'],
  ecg: ['patch'],
  rhythm: ['patch'],
  spo2: ['ring', 'jcvital', 'health'],
  skinTemp: ['ring', 'jcvital'],
  respRate: ['patch', 'health'],
  motion: ['ring', 'health'],       // ring IMU for sleep; Health for daytime
  steps: ['health', 'jcvital'],
  distanceKm: ['health'],
  activeKcal: ['health'],
  workouts: ['health'],
  vo2max: ['health'],
  sleepStages: ['patch', 'health'], // our ECG model; else Apple sleep
};

export type Reading = { source: SourceId; value: number };
export type Fused = { value: number | null; source: SourceId | null; others: Reading[] };

/** Pick the highest-priority available reading for a metric; keep the rest for the comparison view. */
export function fuse(metric: string, readings: Partial<Record<SourceId, number>>): Fused {
  const order = METRIC_SOURCES[metric] ?? [];
  const present = order.filter((s) => typeof readings[s] === 'number') as SourceId[];
  if (!present.length) return { value: null, source: null, others: [] };
  const chosen = present[0];
  return { value: readings[chosen]!, source: chosen, others: present.slice(1).map((s) => ({ source: s, value: readings[s]! })) };
}

export type DeviceState = { id: SourceId; label: string; connected: boolean; detail: string };

export type DevicesSnapshot = {
  devices: DeviceState[];
  anyConnected: boolean;
  // live/last readings per metric with the chosen source + others (for comparison)
  live: Record<string, Fused>;
  ring: RingStatus | null;
};

/** Single hook the whole app can use to see every device and the fused readings. Safe with zero devices. */
export function useDevices(ageHint?: number | null): DevicesSnapshot {
  const band = useBand();
  const health = useHealth(2);
  const [ring, setRing] = useState<RingStatus | null>(bandAvailable ? Ring.status() : null);
  const [jc, setJc] = useState<JcSnapshot>(JCVital.status());
  useEffect(() => {
    if (!bandAvailable) return;
    // Subscribe FIRST, then kick off auto-connect — so the ring's status/data updates are never missed on a cold
    // start (the patch is handled the same way by useBand). Both are safe no-ops when nothing is paired.
    const a = Ring.onStatus(setRing), b = Ring.onData(setRing);
    setRing(Ring.status());
    startRingHistory();
    try { Ring.autoConnect(); } catch {}
    return () => { a.remove(); b.remove(); };
  }, []);
  useEffect(() => {
    // JCVital (ble-plx, cross-platform): continuous like the ring — reconnect the remembered band and keep it streaming.
    const s = JCVital.on(setJc); setJc(JCVital.status());
    JCVital.autoConnect();
    return () => s.remove();
  }, []);

  const bandConn = band.status?.state === 'streaming' || band.status?.state === 'connected';
  const ringConn = ring?.state === 'connected';
  const jcConn = jc.connected;
  const healthConn = health.connected === true;

  const devices: DeviceState[] = [
    { id: 'patch', label: SOURCE_LABEL.patch, connected: !!bandConn,
      detail: bandConn ? `Live${band.metrics?.hr ? ` · ${Math.round(band.metrics.hr)} bpm` : ''}` : 'Not connected' },
    { id: 'ring', label: SOURCE_LABEL.ring, connected: !!ringConn,
      detail: ringConn ? `Connected${ring?.battery != null && ring.battery >= 0 ? ` · ${ring.battery}%` : ''}` : ring?.state === 'scanning' ? 'Searching…' : 'Not connected' },
    { id: 'jcvital', label: SOURCE_LABEL.jcvital, connected: jcConn,
      detail: jcConn ? `Streaming${jc.hr ? ` · ${jc.hr} bpm` : ''}` : 'Not connected' },
    { id: 'health', label: SOURCE_LABEL.health, connected: healthConn,
      detail: healthConn ? `${health.today?.steps != null ? Math.round(health.today.steps).toLocaleString('en-IN') + ' steps today' : 'Connected'}` : 'Not connected' },
  ];

  const bm = band.metrics;
  const hy = health.today;
  const live: Record<string, Fused> = {
    hr: fuse('hr', { patch: bandConn ? bm?.hr : undefined, ring: ringConn ? ring?.hr : undefined, jcvital: jcConn ? jc.hr : undefined, health: hy?.restingHr }),
    hrv: fuse('hrv', { patch: bandConn && (bm?.hrvState === 'ok' || bm?.hrvState === 'active') ? bm?.rmssdSmooth : undefined, ring: ringConn ? ring?.hrv : undefined, health: hy?.hrvSdnn }),
    spo2: fuse('spo2', { ring: ringConn ? ring?.spo2 : undefined, jcvital: jcConn ? jc.spo2 : undefined, health: hy?.spo2 }),
    skinTemp: fuse('skinTemp', { ring: ringConn ? ring?.temp : undefined, jcvital: jcConn ? jc.temp : undefined }),
    steps: fuse('steps', { health: hy?.steps, jcvital: jcConn ? jc.steps : undefined }),
    vo2max: fuse('vo2max', { health: hy?.vo2max }),
  };

  return { devices, anyConnected: devices.some((d) => d.connected), live, ring };
}
