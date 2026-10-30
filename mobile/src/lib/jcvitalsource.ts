// JCVital V8 band as a continuous, app-wide vitals source — behaves like the ring/patch, NOT a manual capture.
// A module-level singleton (survives screen changes) remembers the paired band, auto-connects it, opens the
// real-time stream (realTimeStep) and keeps it open, and turns each ~1 Hz real_time_step packet into a live snapshot
// + a ~10 s buffered row that lib/vitalsync.ts uploads to the longitudinal vault (POST /vitals/ingest).
//
// Scope note: the transport is react-native-ble-plx (JS), so streaming is continuous while the app is ACTIVE
// (foreground). True 24/7 background capture would need a native CoreBluetooth module (like the patch/ring) — a
// future step; for now the band streams whenever Telomy is open.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { BleSDK, DeviceKey } from '@yhmedical/ms-data-sdk';

import { bleManager } from './jcvital/BleManager';
import Constants from './jcvital/constants';

const REMEMBER = 'telomy.jcvital.id';
const BUFFER = 'telomy.jcvital.buf.v1';

export type JcSnapshot = { connected: boolean; hr?: number; spo2?: number; temp?: number; steps?: number; at: number };
type BufRow = { ts: number; hr?: number; spo2?: number; temp?: number };

let snap: JcSnapshot = { connected: false, at: 0 };
let resend: any = null;
let spo2Buf: number[] = [];
let buf: BufRow[] = [];
let lastBufTs = 0;
let wired = false;
let restored = false;
const subs = new Set<(s: JcSnapshot) => void>();

const num = (v: any): number | null => typeof v === 'number' ? v : (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v)) ? Number(v) : null);
const emit = () => subs.forEach((f) => f({ ...snap }));

async function restore() {
  if (restored) return; restored = true;
  try { buf = JSON.parse((await AsyncStorage.getItem(BUFFER)) || '[]'); } catch { buf = []; }
}
async function persist() { try { await AsyncStorage.setItem(BUFFER, JSON.stringify(buf.slice(-2000))); } catch {} }

function onParsed(arg: any) {
  // band payload: { data: { heart_rate, blood_oxygen, step, temp_data(×10), … }, data_type: 'real_time_step' }
  const data = (arg && arg[DeviceKey.Data]) || arg || {};
  const hr = num(data[DeviceKey.HeartRate] ?? data.heart_rate);
  const sp = num(data[DeviceKey.Blood_oxygen] ?? data.blood_oxygen);
  const tp = num(data.temp_data);
  const st = num(data.step);
  let changed = false;
  if (hr && hr > 0) { snap.hr = hr; changed = true; }
  if (sp && sp >= 70 && sp <= 100) { spo2Buf = [...spo2Buf, sp].slice(-10); const s = [...spo2Buf].sort((a, b) => a - b); snap.spo2 = s[Math.floor(s.length / 2)]; changed = true; }
  if (tp) { snap.temp = Math.round(tp / 10 * 10) / 10; changed = true; }
  if (st != null) snap.steps = st;
  if (!changed) return;
  snap.at = Date.now(); emit();
  const now = Math.floor(Date.now() / 1000);
  if (now - lastBufTs >= 10) { lastBufTs = now; buf.push({ ts: now, hr: snap.hr, spo2: snap.spo2, temp: snap.temp }); void persist(); }
}

function startStream() {
  try { bleManager.writeData(BleSDK.realTimeStep(true, false)); } catch {}
  if (resend) clearInterval(resend);
  resend = setInterval(() => { try { bleManager.writeData(BleSDK.realTimeStep(true, false)); } catch {} }, 20000);
}

function wire() {
  if (wired) return; wired = true;
  bleManager.deviceType = 'V8';
  bleManager.on(Constants.BLUE_CONNECTION_STATE, (c: boolean) => {
    snap.connected = c; snap.at = Date.now(); emit();
    if (c) startStream();
    else if (resend) { clearInterval(resend); resend = null; }
  });
  bleManager.on(Constants.BLUE_DATA_RECEIVED, onParsed);
}

export const JCVital = {
  /** Called app-wide on load/foreground (useDevices): reconnect the remembered band and keep it streaming. */
  async autoConnect() {
    wire(); await restore();
    try { await bleManager.init(); } catch {}
    try {
      const id = await AsyncStorage.getItem(REMEMBER);
      if (id && !bleManager.isConnected()) bleManager.connectDeviceById(id);
    } catch {}
  },
  scan(onFound: (d: any) => void) { wire(); bleManager.startScan(onFound); },
  stopScan() { try { bleManager.stopScan(); } catch {} },
  /** Pair + remember a band; it then auto-connects on every app start. */
  async connect(id: string) { wire(); try { await AsyncStorage.setItem(REMEMBER, id); } catch {}; bleManager.stopScan(); bleManager.connectDeviceById(id); },
  async forget() { try { bleManager.disconnectDevice(); } catch {}; try { await AsyncStorage.removeItem(REMEMBER); } catch {} },
  async isPaired() { try { return !!(await AsyncStorage.getItem(REMEMBER)); } catch { return false; } },
  status(): JcSnapshot { return { ...snap }; },
  on(cb: (s: JcSnapshot) => void) { subs.add(cb); return { remove() { subs.delete(cb); } }; },
  /** vitalsync: rows newer than `since` (unix s). The caller advances its own cursor. */
  rows(since: number): BufRow[] { return buf.filter((b) => b.ts > since); },
};
