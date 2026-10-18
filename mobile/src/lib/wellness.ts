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
import { illnessWatch, coachLine, fmtClock, fmtDur, isNight, knots, nightsFrom, recoveryScore, sleepScore, strainFromTrimp, stressFor, vo2max, zonesFor, type Contributor, type DayEvent, type MinuteRec, type Night, type Score, type UserEventRec, localDate } from './wellness-core';
export * from './wellness-core';

export type Wellness = {
  loading: boolean; nights: Night[]; last?: Night; sleep: Score | null; recovery: Score; age: number;
  today: { minutes: MinuteRec[]; zones: number[]; trimp: number; strain: number; stress: ReturnType<typeof stressFor>; worn: number; activeMin: number };
  yesterdayTrimp: number | null; restingHr: number | null; vo2: number | null; reload: () => void; sessionsToday: DayEvent[]; userEvents: UserEventRec[];
  need: SleepNeed; sri: number | null; illness: ReturnType<typeof illnessWatch>;
};

/** Must equal KYCapture.analysisVersion: nights analysed by an older version are re-analysed once on the phone. */
export const ANALYSIS_VERSION = '2026-10-14c (4-stage sleep, gaps = no data)';
const reanalysed = new Set<string>();
let pending: Promise<void> | null = null;
const reloaders = new Set<() => void>();

export function useWellness(ageHint?: number | null): Wellness {
  const [state, setState] = useState<{ nights: Night[]; minutes: MinuteRec[]; age: number; sessions: DayEvent[]; userEvents: UserEventRec[] } | null>(null);
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
    setState({ nights, minutes, age: age!, sessions, userEvents });
  }, [ageHint]);
  useEffect(() => { reloaders.add(load); load(); return () => { reloaders.delete(load); }; }, [load]);

  const nights = state?.nights ?? [];
  const age = state?.age ?? 35;
  const last = nights[nights.length - 1];
  const fresh = last && Date.now() / 1000 - last.end < 20 * 3600 ? last : undefined;  // today's night
  const mins = state?.minutes ?? [];
  const todayKey = localDate(Date.now() / 1000), yKey = localDate(Date.now() / 1000 - 86400);
  const byDay = (k: string) => mins.filter((m) => m.ts.startsWith(k));
  const strainByDate: Record<string, number> = {};
  for (let i = 1; i <= 14; i++) { const k = localDate(Date.now() / 1000 - i * 86400), d = byDay(k); if (d.length >= 60) strainByDate[k] = strainFromTrimp(zonesFor(d, age).trimp); }
  const before = fresh ? nights.slice(0, -1) : nights;
  const needLast = sleepNeed(before, fresh ? strainByDate[localDate(fresh.start - 6 * 3600)] ?? 0 : 0, strainByDate);
  const sri = sleepRegularity(nights);
  const sleep = fresh ? sleepScore(fresh, nights, needLast.needMin, sri) : null;
  const dayTrimps = Array.from({ length: 8 }, (_, i) => localDate(Date.now() / 1000 - (7 - i) * 86400))
    .map((k) => byDay(k)).filter((d) => d.length >= 60).map((d) => zonesFor(d, age).trimp);
  const recovery = recoveryScore(fresh, nights, sleep, dayTrimps.length && byDay(yKey).length >= 60 ? dayTrimps : []);
  const tm = byDay(todayKey);
  const { zones, trimp } = zonesFor(tm, age);
  const restings = mins.map((m) => m.resting).filter(Boolean) as number[];
  const restingHr = restings.length ? restings[restings.length - 1] : null;
  const calmRef = mins.filter((m) => m.rmssd && m.activity === 'rest' && m.sleep !== 'asleep').map((m) => m.rmssd!) ;
  const stress = stressFor(tm, restingHr ?? 65, calmRef);
  return {
    loading: !state, nights, last: fresh, sleep, recovery, age,
    today: { minutes: tm, zones, trimp, strain: strainFromTrimp(trimp), stress, worn: tm.length,
      activeMin: tm.filter((m) => m.activity === 'active').length },
    yesterdayTrimp: byDay(yKey).length >= 60 ? zonesFor(byDay(yKey), age).trimp : null,
    restingHr, vo2: restingHr ? vo2max(age, restingHr) : null, reload: load, sessionsToday: state?.sessions ?? [], userEvents: state?.userEvents ?? [],
    need: sleepNeed(nights, strainFromTrimp(trimp), strainByDate), sri, illness: illnessWatch(nights),
  };
}
