// Telomy wellness scores, computed on the phone from the ECG band (works offline).
// Inputs: overnight-sleep captures (KYSleepNight + KYNightMetrics summaries) and per-minute band summaries
// (Documents/wellness/minutes). Every score is a wellness estimate, not a diagnosis. Methods and sources:
// docs/devices/WELLNESS_SCORES.md.
import { useCallback, useEffect, useState } from 'react';
import { Band, bandAvailable } from './band';
import { phoneActivity, type HealthSleepSegment } from '../../modules/ky-ecg';
import { healthConnected } from './health';
import { ringSamples, ringSleepRecords } from './ringhistory';
import { fuseNights, healthNights, ringOwnNights, sleepNeed, sleepRegularity, whoopNights, type SleepNeed, type WhoopNightIn } from './sleepfuse';
import { api } from './api';
import { syncDaily } from './sync';
import { syncVitals } from './vitalsync';
import { energyScore, illnessWatch, coachLine, fmtClock, fmtDur, isNight, knots, nightsFrom, recoveryScore, sleepScore, strainFromTrimp, stressFor, todayGuidance, vo2max, zonesFor, type Contributor, type DayEvent, type Guidance, type MinuteRec, type Night, type Score, type UserEventRec, localDate } from './wellness-core';
export * from './wellness-core';

/** Server day engine on the WHOOP 1 Hz stream (backend/app/whoop_day.py). */
export type WhoopDay = { ok: boolean; day: string; wornMin: number; restingHr: number; strain: number; trimp: number; zonesMin: number[];
  workouts: { start: number; end: number; min: number; avgHr: number; maxHr: number; kcal: number | null }[];
  stress: { avg: number | null; minutes: number; highMin: number } };

export type Wellness = {
  loading: boolean; nights: Night[]; naps: Night[]; last?: Night; sleep: Score | null; recovery: Score; age: number;
  today: { minutes: MinuteRec[]; zones: number[]; trimp: number; strain: number; stress: ReturnType<typeof stressFor>; worn: number; activeMin: number; source: 'patch' | 'whoop'; whoop?: WhoopDay };
  yesterdayTrimp: number | null; restingHr: number | null; vo2: number | null; reload: () => void; sessionsToday: DayEvent[]; userEvents: UserEventRec[];
  need: SleepNeed; sri: number | null; illness: ReturnType<typeof illnessWatch>;
  energy: Score; guidance: Guidance | null;
};

/** Must equal KYCapture.analysisVersion: nights analysed by an older version are re-analysed once on the phone. */
export const ANALYSIS_VERSION = '2026-10-14c (4-stage sleep, gaps = no data)';
const reanalysed = new Set<string>();
let pending: Promise<void> | null = null;
const reloaders = new Set<() => void>();

export function useWellness(ageHint?: number | null): Wellness {
  const [state, setState] = useState<{ nights: Night[]; minutes: MinuteRec[]; age: number; sessions: DayEvent[]; userEvents: UserEventRec[]; whoopDay?: WhoopDay; recoveryDaily?: any } | null>(null);
  const load = useCallback(async () => {
    const caps = bandAvailable ? Band.listCaptures() : [];
    // nights recorded before the night metrics existed: re-analyse once (in the background) so they get them.
    // One shared job: every mounted instance waits for it, then all reload.
    // re-analyse: nights from older analysis versions, and nights left open (never stopped — e.g. the app was closed
    // or the band died) more than 6 h after they began. Never the session that is recording right now.
    const live = bandAvailable ? Band.captureId() : null;
    const now = Date.now() / 1000;
    const stale = (caps as any[]).filter((c) => isNight(c) && c.id !== live && !reanalysed.has(c.id) &&
      ((c.endedAt && c.analysis?.version !== ANALYSIS_VERSION) || (!c.endedAt && !c.summary?.sleep && now - c.startedAt > 6 * 3600)));
    if (stale.length && !pending) {
      pending = (async () => { for (const c of stale) { reanalysed.add(c.id); await Band.reanalyseCapture(c.id); } })()
        .finally(() => { pending = null; reloaders.forEach((r) => r()); });
    }
    if (pending) { await pending; return; }  // the finally() above reloads every instance
    const minutes = (bandAvailable ? await Band.wellnessRead('minutes', 8) : []) as MinuteRec[];
    let age = ageHint ?? null;
    if (age) Band.wellnessAppend('profile', { age });
    else age = ((await Band.wellnessRead('profile', 60)).filter((p) => p.age).pop()?.age as number) ?? 35;
    const dayStart = new Date(); dayStart.setHours(0, 0, 0, 0);
    const sessions: DayEvent[] = (caps as any[]).filter((c) => !isNight(c) && c.startedAt >= dayStart.getTime() / 1000)
      .map((c) => ({ t: c.startedAt, end: c.endedAt ?? c.startedAt, label: c.therapy }));
    const userEvents = ((bandAvailable ? await Band.wellnessRead('events', 2) : []) as UserEventRec[]).filter((e) => e.t >= dayStart.getTime() / 1000 - 6 * 3600);
    // every device's nights, one per sleep period (lib/sleepfuse.ts): patch > Apple Watch > ring > other Health
    const [segs, ring, phone] = await Promise.all([
      healthConnected().then((c) => (c && bandAvailable ? Band.healthSleep(21) : ([] as HealthSleepSegment[]))).catch(() => [] as HealthSleepSegment[]),
      ringSamples(Date.now() - 22 * 86400000, Date.now()).catch(() => []),
      phoneActivity(24 * 7).catch(() => []),
    ]);
    // WHOOP nights arrive through the Telomy server (NOOP self-hosted push); offline → simply none this load
    const wn = await api<{ nights: WhoopNightIn[] }>('/whoop/nights?days=21').then((r) => whoopNights(r.nights ?? [])).catch(() => [] as Night[]);
    const ro = ringOwnNights(await ringSleepRecords(Date.now() - 22 * 86400000, Date.now()).catch(() => []));
    const nights = fuseNights(nightsFrom(caps), healthNights(segs), ring, phone, wn, ro);
    const whoopDay = await api<WhoopDay>('/whoop/day').catch(() => undefined);
    // Fallback recovery from daily rhr/hrv/sleep signals, used when there's no fresh worn-device night to score.
    const recoveryDaily = await api<any>('/wellness/recovery-daily').catch(() => undefined);
    // real daily summaries → server (Vault, insights, twin, predictions run on them); throttled, queued offline
    const hdays = await healthConnected().then((c) => (c && bandAvailable ? Band.healthDaily(14) : [])).catch(() => []);
    syncDaily(nights, hdays);
    syncVitals();                               // upload the continuous patch/ring vitals to the longitudinal record
    setState({ nights, minutes, age: age!, sessions, userEvents, whoopDay: whoopDay?.ok ? whoopDay : undefined, recoveryDaily });
  }, [ageHint]);
  useEffect(() => { reloaders.add(load); load(); return () => { reloaders.delete(load); }; }, [load]);

  const nights = state?.nights ?? [];
  const age = state?.age ?? 35;
  // A short daytime session is a NAP, not "last night" — showing it as the night was the bug. The headline is the most
  // recent real overnight night; naps are kept separately (they stay unconfirmed — the user is the ground truth).
  const isNapNight = (n: Night) => { const mid = new Date(((n.start + n.end) / 2) * 1000).getHours(); return mid >= 10 && mid < 20 && n.tstMin < 240; };
  const realNights = nights.filter((n) => !isNapNight(n));
  const naps = nights.filter(isNapNight);
  const last = realNights[realNights.length - 1];
  const fresh = last && Date.now() / 1000 - last.end < 20 * 3600 ? last : undefined;  // today's night
  const mins = state?.minutes ?? [];
  const todayKey = localDate(Date.now() / 1000), yKey = localDate(Date.now() / 1000 - 86400);
  const byDay = (k: string) => mins.filter((m) => m.ts.startsWith(k));
  const strainByDate: Record<string, number> = {};
  for (let i = 1; i <= 14; i++) { const k = localDate(Date.now() / 1000 - i * 86400), d = byDay(k); if (d.length >= 60) strainByDate[k] = strainFromTrimp(zonesFor(d, age).trimp); }
  const before = fresh ? realNights.slice(0, -1) : realNights;
  const needLast = sleepNeed(before, fresh ? strainByDate[localDate(fresh.start - 6 * 3600)] ?? 0 : 0, strainByDate);
  const sri = sleepRegularity(realNights);
  const sleep = fresh ? sleepScore(fresh, nights, needLast.needMin, sri) : null;
  const dayTrimps = Array.from({ length: 8 }, (_, i) => localDate(Date.now() / 1000 - (7 - i) * 86400))
    .map((k) => byDay(k)).filter((d) => d.length >= 60).map((d) => zonesFor(d, age).trimp);
  const recoveryNight = recoveryScore(fresh, nights, sleep, dayTrimps.length && byDay(yKey).length >= 60 ? dayTrimps : []);
  const rd = state?.recoveryDaily;
  // No worn-device night to score? fall back to the daily-signals recovery from the server (rhr/hrv/sleep).
  const recovery: Score = recoveryNight.score != null ? recoveryNight
    : (rd && rd.score != null
        ? { score: rd.score, label: rd.label, contributors: rd.contributors ?? [], confidence: 'calibrating', calibrating: rd.note }
        : recoveryNight);
  const tm = byDay(todayKey);
  const { zones, trimp } = zonesFor(tm, age);
  const restings = mins.map((m) => m.resting).filter(Boolean) as number[];
  const restingHr = restings.length ? restings[restings.length - 1] : null;
  const calmRef = mins.filter((m) => m.rmssd && m.activity === 'rest' && m.sleep !== 'asleep').map((m) => m.rmssd!) ;
  const stress = stressFor(tm, restingHr ?? 65, calmRef);
  // Daytime: the patch only covers recorded sessions; when it covered < 1 h today and the WHOOP stream has the day,
  // strain / zones / stress / workouts come from the server's WHOOP day engine (all-day 1 Hz heart rate + motion).
  const wd = state?.whoopDay;
  const useWhoop = !!wd && tm.length < 60 && wd.wornMin >= 60;
  const today = useWhoop
    ? { minutes: tm, zones: wd!.zonesMin, trimp: wd!.trimp, strain: wd!.strain, worn: wd!.wornMin, source: 'whoop' as const, whoop: wd,
        activeMin: wd!.workouts.reduce((a, w) => a + w.min, 0),
        stress: { score: wd!.stress.minutes >= 30 ? Math.round((100 * wd!.stress.highMin) / wd!.stress.minutes) : null, stressMin: wd!.stress.highMin,
          calmMin: Math.max(0, wd!.stress.minutes - wd!.stress.highMin), minutes: wd!.stress.minutes, timeline: [] } }
    : { minutes: tm, zones, trimp, strain: strainFromTrimp(trimp), stress, worn: tm.length, source: 'patch' as const,
        activeMin: tm.filter((m) => m.activity === 'active').length };
  const energy = energyScore(recovery, sleep, today.stress?.score ?? null, today.strain);
  return {
    loading: !state, nights, naps, last: fresh, sleep, recovery, age,
    today, energy, guidance: todayGuidance(energy.score, recovery.score, today.stress?.score ?? null),
    yesterdayTrimp: byDay(yKey).length >= 60 ? zonesFor(byDay(yKey), age).trimp : null,
    restingHr, vo2: restingHr ? vo2max(age, restingHr) : null, reload: load, sessionsToday: state?.sessions ?? [], userEvents: state?.userEvents ?? [],
    need: sleepNeed(nights, today.strain, strainByDate), sri, illness: illnessWatch(nights),
  };
}
