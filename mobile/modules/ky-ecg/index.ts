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
};

type Native = {
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
  wellnessRead(kind: string, days: number): Promise<Record<string, any>[]>;
  reanalyseCapture(id: string): Promise<{ id?: string; summary?: Record<string, any>; error?: string }>;
  addListener<K extends keyof Events>(event: K, listener: Events[K]): EventSubscription;
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
