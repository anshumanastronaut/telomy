// KY-E-B1 ECG band: typed JS API over the native KyEcg module (iOS). On platforms without the module
// (web, Expo Go, Android for now) `isAvailable` is false and every call is a no-op.
import { requireOptionalNativeModule } from 'expo';

type EventSubscription = { remove: () => void };

export type BandState = 'unsupported' | 'off' | 'unauthorized' | 'idle' | 'scanning' | 'connecting' | 'connected' | 'streaming';
export type SignalQuality = 'warming_up' | 'no_contact' | 'poor' | 'acceptable' | 'good';

export type BandStatus = {
  state: BandState;
  wantsStream: boolean;
  deviceId?: string;
  deviceName?: string;
  rememberedId?: string;
  rememberedName?: string;
  battery?: number;
  hardware?: string;
  firmware?: string;
  leadOn?: boolean;
  holterState?: string;
  /** The band is recording to its own memory, and its firmware pauses the live stream meanwhile. */
  liveBlockedByRecording?: boolean;
  holterStart?: number;
  droppedFrames: number;
  sampleRate: number;
  error?: string;
};

export type EcgFrame = { frame: number; t: number; fs: number; raw: number[]; display: number[] };
export type Beat = { t: number; rr?: number; amplitude: number };
export type BandMetrics = {
  t: number;
  hr?: number;
  meanNN60?: number;
  rmssd60?: number;
  sdnn60?: number;
  pnn50?: number;
  rmssd300?: number;
  sdnn300?: number;
  artefactPercent?: number;
  irregularBeats60: number;
  hrvReliable: boolean;
  quality: SignalQuality;
  sqi: { bSQI?: number; kSQI?: number; pSQI?: number; basSQI?: number };
  beats: number;
  droppedFrames: number;
  /** Adaptive (Kalman) heart rate is `hr`; `hr10` is the plain 10-s mean. */
  hrSd?: number;
  hr10?: number;
  hrConfidence: 'high' | 'medium' | 'low' | 'none';
  rmssdSmooth?: number;
  rmssd5?: number;
  hrvState: 'ok' | 'settling' | 'active' | 'irregular' | 'noisy';
  activity: 'rest' | 'light' | 'active' | 'moving' | 'unknown';
  sleep: 'awake' | 'asleep' | 'unknown';
  motionIndex: number;
  signal: 'clean' | 'noisy' | 'motion' | 'no_contact' | 'flat' | 'saturated';
  restingHr: number;
  earlyBeatsPerMin: number;
  afBurden60: number;
  openEvents: string[];
};
export type RhythmEvent = { type: string; start: number; end: number; detail: Record<string, number> };
export type SleepSummary = { totalSleepMin: number; efficiency: number; wasoMin: number; awakenings: number; hypnogram: number[]; onsetMin?: number; sleepHr?: number; sleepRmssd?: number };
export type RecordingEvent =
  | { phase: 'started'; total: number; from: number }
  | { phase: 'analysing'; frames: number }
  | { phase: 'progress'; received: number; total: number }
  | { phase: 'failed'; message: string }
  | { phase: 'completed'; path: string; frames: number; start: number; durationSec?: number; beats?: number; meanHr?: number; rmssd?: number; sdnn?: number; artefactPercent?: number; rr?: number[]; events?: RhythmEvent[]; sleep?: SleepSummary; captureId?: string };
export type HealthDay = {
  date: string; steps?: number; distanceKm?: number; activeKcal?: number; exerciseMin?: number; flights?: number;
  restingHr?: number; walkingHr?: number; hrvSdnn?: number; respRate?: number; spo2?: number; vo2max?: number;
  weightKg?: number; bodyFatPct?: number; sleepMin?: number; workouts?: { type: number; min: number; start: number; end?: number; kcal?: number; km?: number; source?: string }[];
};
/** One Apple Health sleep segment. stage: 0 awake, 1 core/light, 2 deep, 3 REM, 4 asleep (unstaged), 5 in bed. */
export type HealthSleepSegment = { start: number; end: number; stage: 0 | 1 | 2 | 3 | 4 | 5; source: string; watch: boolean };
/** On-device voice biomarkers (KYVoice.swift; same maths as backend voice.acoustics). */
export type VoiceFeatures = { voiced_s: number; duration_s?: number; f0_mean?: number; f0_sd?: number; f0_cv?: number; jitter_pct?: number;
  shimmer_pct?: number; hnr_db?: number; rate_per_s?: number; pause_ratio?: number; energy_db?: number };
export type UserEvent = { kind: string; label: string; note?: string; t?: number; amount?: string };
export type FoundDevice = { id: string; name: string; rssi: number };
export type CaptureMeta = {
  id: string; format: string; therapy: string; settings?: Record<string, unknown>; phases?: { phase: string; t: number; note?: string }[];
  startedAt: number; endedAt?: number; durationSec?: number; samples: number; pre?: Record<string, number>; post?: Record<string, number>;
  notes?: string; summary?: Record<string, unknown>; bundlePath?: string; bundleBytes?: number;
};

type Events = {
  onStatus: (s: BandStatus) => void;
  onDevice: (d: FoundDevice) => void;
  onEcg: (f: EcgFrame) => void;
  onBeat: (b: Beat) => void;
  onMetrics: (m: BandMetrics) => void;
  onRecording: (r: RecordingEvent) => void;
  onRhythm: (e: RhythmEvent) => void;
  onRingStatus: (s: RingStatus) => void;
  onRingData: (s: RingStatus) => void;
  onRingDevice: (d: FoundDevice) => void;
  onRingHistory: (h: RingHistory) => void;
  onRingSleep: (s: { nights: RingSleepRecord[] }) => void;
};

type Native = {
  ringStatus(): RingStatus; ringScan(): void; ringAutoConnect(): void; ringSyncHistory(): void;
  ringStartRaw(ecg: boolean, imu: boolean, ppg: boolean): void; ringStopRaw(): void;
  ringStartOvernight(): void; ringStopOvernight(): void; autoSleep(): boolean; setAutoSleep(on: boolean): void;
  phoneActivity(hours: number): Promise<PhoneActivity[]>;
  ringConnect(id: string): void; ringDisconnect(): void;
  ringForget(): void; ringStartMeasure(type: number): void; ringStopMeasure(type: number): void; ringReadBattery(): void;
  getStatus(): BandStatus;
  startScan(): void;
  stopScan(): void;
  connect(id: string): void;
  autoConnect(): void;
  disconnect(): void;
  forget(): void;
  startStream(): void;
  stopStream(): void;
  startRecording(): void;
  stopRecording(): void;
  syncRecording(): void;
  log(line: string): void;
  startCapture(meta: Record<string, unknown>): { id?: string; error?: string };
  markPhase(phase: string, note: string | null): void;
  updateCapture(meta: Record<string, unknown>): void;
  stopCapture(extra: Record<string, unknown>): { id?: string; bundlePath?: string; error?: string };
  captureId(): string | null;
  captureMeta(): Record<string, any> | null;
  listCaptures(): CaptureMeta[];
  deleteCapture(id: string): void;
  wellnessAppend(kind: string, record: Record<string, unknown>): void;
  addUserEvent(e: Record<string, unknown>): { captureId?: string; t?: number };
  healthAuthorize(): Promise<{ ok: boolean; error?: string }>;
  healthDaily(days: number): Promise<HealthDay[]>;
  healthSleep(days: number): Promise<HealthSleepSegment[]>;
  voiceFeatures(path: string, del: boolean): Promise<VoiceFeatures>;
  wellnessRead(kind: string, days: number): Promise<Record<string, any>[]>;
  reanalyseCapture(id: string): Promise<{ id?: string; summary?: Record<string, any>; error?: string }>;
  addListener<K extends keyof Events>(event: K, listener: Events[K]): EventSubscription;
};

export type RingStatus = { state: string; battery: number; name: string; hr?: number; hrv?: number; spo2?: number; temp?: number; rememberedId?: string;
  capturing?: boolean; overnight?: boolean; rawCounts?: Record<string, number> };
/** A longitudinal dump pulled from the ring's flash log. Each sample is one timestamped record; the "all" dump (type 9)
 *  carries hr and hrv together, which Telomy uses to study the HR↔HRV relationship and cross-check against the patch. */
/** A run of one activity from the phone's motion coprocessor (Apple's on-device classifier, 7 days of history). */
export type PhoneActivity = { type: 'still' | 'walking' | 'running' | 'cycling' | 'driving' | 'unknown'; start: number; end: number; confidence: number };
export const phoneActivity = (hours = 24): Promise<PhoneActivity[]> => native?.phoneActivity(hours) ?? Promise.resolve([]);
export type RingHistorySample = { t: number; hr?: number; hrv?: number; cvrr?: number; spo2?: number; temp?: number };
export type RingHistory = { type: number; samples: RingHistorySample[] };
/** Segment types: 241 deep, 242 light, 243 REM, 244 awake. `coverage` = segment seconds / record span (< 0.8 = cut by a BLE drop). */
export type RingSleepRecord = { start: number; end: number; coverage: number; segments: { type: number; start: number; len: number }[] };

export const Ring = {
  status: (): RingStatus | null => native?.ringStatus() ?? null,
  scan: () => native?.ringScan(),
  /** Reconnect to the last-known ring in the background (used by the app's auto-connect on launch). */
  autoConnect: () => native?.ringAutoConnect(),
  /** Pull everything logged since the last sync (also runs automatically every ~10 min while connected). */
  syncHistory: () => native?.ringSyncHistory(),
  /** Research capture of the ring's raw streams (ECG / IMU / PPG + PPI) to Documents/ring-raw. */
  startRaw: (o: { ecg: boolean; imu: boolean; ppg: boolean }) => native?.ringStartRaw(o.ecg, o.imu, o.ppg),
  stopRaw: () => native?.ringStopRaw(),
  /** Overnight mode: live HR + movement, motion-gated SpO₂/temp, ring sleep score pulled at stop. */
  startOvernight: () => native?.ringStartOvernight(),
  stopOvernight: () => native?.ringStopOvernight(),
  /** Automatic sleep detection (default on): starts/stops the night from patch and/or ring signals, no tap needed. */
  autoSleep: (): boolean => native?.autoSleep() ?? false,
  setAutoSleep: (on: boolean) => native?.setAutoSleep(on),
  connect: (id: string) => native?.ringConnect(id),
  disconnect: () => native?.ringDisconnect(),
  forget: () => native?.ringForget(),
  /** 0 = live heart rate, 2 = SpO2, 4 = temperature (never 1 — that is blood-pressure estimation in this SDK). */
  startMeasure: (type: number) => native?.ringStartMeasure(type),
  stopMeasure: (type: number) => native?.ringStopMeasure(type),
  readBattery: () => native?.ringReadBattery(),
  onStatus(cb: (s: RingStatus) => void) { return native ? native.addListener('onRingStatus', cb) : { remove() {} }; },
  onData(cb: (s: RingStatus) => void) { return native ? native.addListener('onRingData', cb) : { remove() {} }; },
  onHistory(cb: (h: RingHistory) => void) { return native ? native.addListener('onRingHistory', cb) : { remove() {} }; },
  /** The ring's own sleep records (its accelerometer-based detection), decoded from Health_HistorySleep. */
  onSleep(cb: (s: { nights: RingSleepRecord[] }) => void) { return native ? native.addListener('onRingSleep', cb) : { remove() {} }; },
};

const native = requireOptionalNativeModule<Native>('KyEcg');

export const isAvailable = native != null;

const noop = () => {};
export const Band = {
  getStatus: (): BandStatus | null => native?.getStatus() ?? null,
  startScan: () => native?.startScan(),
  stopScan: () => native?.stopScan(),
  connect: (id: string) => native?.connect(id),
  autoConnect: () => native?.autoConnect(),
  disconnect: () => native?.disconnect(),
  forget: () => native?.forget(),
  startStream: () => native?.startStream(),
  stopStream: () => native?.stopStream(),
  startRecording: () => native?.startRecording(),
  stopRecording: () => native?.stopRecording(),
  syncRecording: () => native?.syncRecording(),
  /** Write a line to the on-phone diagnostic log (Documents/ky-debug). */
  log: (line: string) => native?.log(line),
  startCapture: (meta: Record<string, unknown>) => native?.startCapture(meta) ?? { error: 'Band module unavailable' },
  markPhase: (phase: string, note?: string) => native?.markPhase(phase, note ?? null),
  updateCapture: (meta: Record<string, unknown>) => native?.updateCapture(meta),
  stopCapture: (extra: Record<string, unknown>) => native?.stopCapture(extra) ?? { error: 'Band module unavailable' },
  captureId: () => native?.captureId() ?? null,
  /** Meta of the session being captured (survives app relaunch), or null. */
  captureMeta: (): Record<string, any> | null => native?.captureMeta() ?? null,
  listCaptures: (): CaptureMeta[] => native?.listCaptures() ?? [],
  deleteCapture: (id: string) => native?.deleteCapture(id),
  /** Log a user event (meal, supplement, alcohol, custom…) into the running capture and the on-phone store. */
  /** Ask for read access to Apple Health (steps, energy, exercise, vitals, sleep, workouts). */
  healthAuthorize: async () => (native ? native.healthAuthorize() : { ok: false, error: 'Not available' }),
  /** Daily Apple Health summaries for the last `days` days, oldest first. */
  healthDaily: async (days: number): Promise<HealthDay[]> => (native ? native.healthDaily(days) : []),
  /** Voice biomarkers from a recording, computed on the phone; `del` deletes the audio file right after reading it. */
  voiceFeatures: async (path: string, del = true): Promise<VoiceFeatures> => (native?.voiceFeatures ? native.voiceFeatures(path, del) : { voiced_s: 0 }),
  /** Raw Apple Health sleep segments (Watch stages when present), oldest first. */
  healthSleep: async (days: number): Promise<HealthSleepSegment[]> => (native?.healthSleep ? native.healthSleep(days) : []),
  addUserEvent: (e: UserEvent) => native?.addUserEvent(e as any) ?? { },
  /** Append a record to the on-phone wellness store (Documents/wellness/<kind>/<day>.jsonl). */
  wellnessAppend: (kind: string, record: Record<string, unknown>) => native?.wellnessAppend(kind, record),
  /** Records from the last `days` days of the on-phone wellness store, oldest first. */
  wellnessRead: async (kind: string, days: number): Promise<Record<string, any>[]> => (native ? native.wellnessRead(kind, days) : []),
  /** Re-run the current analysis over a saved session's raw ECG (off the main thread). */
  reanalyseCapture: async (id: string) => (native ? native.reanalyseCapture(id) : { error: 'Band module unavailable' }),
  on<K extends keyof Events>(event: K, listener: Events[K]): { remove: () => void } {
    return native ? native.addListener(event, listener) : { remove: noop };
  },
};
