// Exercise & training: every session from every source on one timeline, each with a load, and a training status.
//  Sources: Apple Health workouts (80+ named types, recorded by iPhone/Watch/any gym app), sessions the iPhone's
//  motion coprocessor detected on its own (walk / run / cycle ≥ 10 min, not already a workout), and Telomy patch
//  sessions. Load = heart-rate-zone TRIMP when the patch or ring was worn (the same Edwards weighting as Strain),
//  else duration × the activity's typical intensity — clearly marked as an estimate.
//  Status = acute (7-day) : chronic (28-day, weekly mean) load ratio, Gabbett 2016. The ACWR is debated
//  (Impellizzeri 2020), so it is shown as guidance about change in load, not as an injury prediction.
import type { SFSymbol } from 'expo-symbols';
import type { HealthDay, PhoneActivity } from '../../modules/ky-ecg';
import { hrMax, type MinuteRec } from './wellness';

/** HKWorkoutActivityType raw value → name, SF Symbol, typical intensity (load per minute when no heart rate). */
export const WORKOUT: Record<number, { name: string; icon: SFSymbol; k: number }> = {
  1: { name: 'American football', icon: 'figure.american.football', k: 3.5 }, 2: { name: 'Archery', icon: 'figure.archery', k: 1.2 },
  3: { name: 'Australian football', icon: 'figure.australian.football', k: 3.5 }, 4: { name: 'Badminton', icon: 'figure.badminton', k: 3 },
  5: { name: 'Baseball', icon: 'figure.baseball', k: 2 }, 6: { name: 'Basketball', icon: 'figure.basketball', k: 3.5 },
  7: { name: 'Bowling', icon: 'figure.bowling', k: 1.3 }, 8: { name: 'Boxing', icon: 'figure.boxing', k: 4 },
  9: { name: 'Climbing', icon: 'figure.climbing', k: 3.5 }, 10: { name: 'Cricket', icon: 'figure.cricket', k: 2 },
  11: { name: 'Cross training', icon: 'figure.cross.training', k: 3.5 }, 12: { name: 'Curling', icon: 'figure.curling', k: 2 },
  13: { name: 'Cycling', icon: 'figure.outdoor.cycle', k: 3 }, 14: { name: 'Dance', icon: 'figure.dance', k: 2.5 },
  16: { name: 'Elliptical', icon: 'figure.elliptical', k: 3 }, 17: { name: 'Equestrian', icon: 'figure.equestrian.sports', k: 2 },
  18: { name: 'Fencing', icon: 'figure.fencing', k: 3 }, 19: { name: 'Fishing', icon: 'figure.fishing', k: 1 },
  20: { name: 'Functional strength', icon: 'figure.strengthtraining.functional', k: 3 }, 21: { name: 'Golf', icon: 'figure.golf', k: 1.5 },
  22: { name: 'Gymnastics', icon: 'figure.gymnastics', k: 3 }, 23: { name: 'Handball', icon: 'figure.handball', k: 3.5 },
  24: { name: 'Hiking', icon: 'figure.hiking', k: 2.5 }, 25: { name: 'Hockey', icon: 'figure.hockey', k: 3.5 },
  26: { name: 'Hunting', icon: 'figure.hunting', k: 1.5 }, 27: { name: 'Lacrosse', icon: 'figure.lacrosse', k: 3.5 },
  28: { name: 'Martial arts', icon: 'figure.martial.arts', k: 3.5 }, 29: { name: 'Mind & body', icon: 'figure.mind.and.body', k: 1 },
  31: { name: 'Paddle sports', icon: 'oar.2.crossed', k: 2.5 }, 32: { name: 'Play', icon: 'figure.play', k: 2.5 },
  33: { name: 'Recovery', icon: 'figure.cooldown', k: 0.8 }, 34: { name: 'Racquetball', icon: 'figure.racquetball', k: 3.5 },
  35: { name: 'Rowing', icon: 'figure.rower', k: 3.5 }, 36: { name: 'Rugby', icon: 'figure.rugby', k: 4 },
  37: { name: 'Running', icon: 'figure.run', k: 4 }, 38: { name: 'Sailing', icon: 'figure.sailing', k: 1.5 },
  39: { name: 'Skating', icon: 'figure.skating', k: 2.5 }, 40: { name: 'Snow sports', icon: 'figure.snowboarding', k: 3 },
  41: { name: 'Football', icon: 'figure.indoor.soccer', k: 3.5 }, 42: { name: 'Softball', icon: 'figure.softball', k: 2 },
  43: { name: 'Squash', icon: 'figure.squash', k: 4 }, 44: { name: 'Stair climbing', icon: 'figure.stair.stepper', k: 3.5 },
  45: { name: 'Surfing', icon: 'figure.surfing', k: 2.5 }, 46: { name: 'Swimming', icon: 'figure.pool.swim', k: 3.5 },
  47: { name: 'Table tennis', icon: 'figure.table.tennis', k: 2.5 }, 48: { name: 'Tennis', icon: 'figure.tennis', k: 3 },
  49: { name: 'Track & field', icon: 'figure.track.and.field', k: 3.5 }, 50: { name: 'Strength training', icon: 'figure.strengthtraining.traditional', k: 3 },
  51: { name: 'Volleyball', icon: 'figure.volleyball', k: 2.5 }, 52: { name: 'Walking', icon: 'figure.walk', k: 1.5 },
  53: { name: 'Water fitness', icon: 'figure.water.fitness', k: 2 }, 54: { name: 'Water polo', icon: 'figure.waterpolo', k: 4 },
  55: { name: 'Water sports', icon: 'water.waves', k: 2.5 }, 56: { name: 'Wrestling', icon: 'figure.wrestling', k: 4 },
  57: { name: 'Yoga', icon: 'figure.yoga', k: 1.3 }, 58: { name: 'Barre', icon: 'figure.barre', k: 2 },
  59: { name: 'Core training', icon: 'figure.core.training', k: 2.5 }, 60: { name: 'Cross-country skiing', icon: 'figure.skiing.crosscountry', k: 4 },
  61: { name: 'Downhill skiing', icon: 'figure.skiing.downhill', k: 3 }, 62: { name: 'Flexibility', icon: 'figure.flexibility', k: 1 },
  63: { name: 'HIIT', icon: 'figure.highintensity.intervaltraining', k: 4.5 }, 64: { name: 'Jump rope', icon: 'figure.jumprope', k: 4 },
  65: { name: 'Kickboxing', icon: 'figure.kickboxing', k: 4 }, 66: { name: 'Pilates', icon: 'figure.pilates', k: 2 },
  67: { name: 'Snowboarding', icon: 'figure.snowboarding', k: 3 }, 68: { name: 'Stairs', icon: 'figure.stairs', k: 3.5 },
  69: { name: 'Step training', icon: 'figure.step.training', k: 3 }, 70: { name: 'Wheelchair walk', icon: 'figure.roll', k: 2 },
  71: { name: 'Wheelchair run', icon: 'figure.roll.runningpace', k: 3.5 }, 72: { name: 'Tai chi', icon: 'figure.taichi', k: 1.2 },
  73: { name: 'Mixed cardio', icon: 'figure.mixed.cardio', k: 3.5 }, 74: { name: 'Hand cycling', icon: 'figure.hand.cycling', k: 3 },
  75: { name: 'Disc sports', icon: 'figure.disc.sports', k: 2.5 }, 76: { name: 'Fitness gaming', icon: 'gamecontroller', k: 2 },
  77: { name: 'Cardio dance', icon: 'figure.dance', k: 3 }, 78: { name: 'Social dance', icon: 'figure.socialdance', k: 2 },
  79: { name: 'Pickleball', icon: 'figure.pickleball', k: 3 }, 80: { name: 'Cool-down', icon: 'figure.cooldown', k: 0.8 },
  82: { name: 'Triathlon', icon: 'figure.open.water.swim', k: 4 }, 83: { name: 'Transition', icon: 'arrow.triangle.swap', k: 2 },
  84: { name: 'Underwater diving', icon: 'figure.open.water.swim', k: 2 }, 3000: { name: 'Workout', icon: 'figure.mixed.cardio', k: 2.5 },
};
export const WORKOUT_TYPE_COUNT = Object.keys(WORKOUT).length;
const DETECTED: Record<string, { name: string; icon: SFSymbol; k: number }> = {
  walking: { name: 'Walk (detected)', icon: 'figure.walk', k: 1.5 }, running: { name: 'Run (detected)', icon: 'figure.run', k: 4 },
  cycling: { name: 'Ride (detected)', icon: 'figure.outdoor.cycle', k: 3 },
};

export type Session = {
  id: string; start: number; end: number; name: string; icon: SFSymbol; source: 'Apple Health' | 'iPhone motion' | 'Telomy patch';
  device?: string; min: number; kcal?: number; km?: number; avgHr?: number; maxHr?: number; zones?: number[]; load: number; loadFromHr: boolean;
};

/** Heart-rate summary of a session from band minutes that fall inside it (needs ≥ 50 % coverage to trust it). */
function hrOf(start: number, end: number, mins: MinuteRec[], age: number) {
  const inside = mins.filter((m) => { const t = new Date(m.ts).getTime() / 1000; return t >= start && t <= end && m.hr && m.quality !== 'poor' && m.quality !== 'no_contact'; });
  if (inside.length < Math.max(3, (end - start) / 60 * 0.5)) return null;
  const max = hrMax(age), zones = [0, 0, 0, 0, 0];
  for (const m of inside) { const f = m.hr / max; if (f >= 0.5) zones[Math.min(4, Math.floor((f - 0.5) * 10))] += 1; }
  const trimp = zones.reduce((s, v, i) => s + v * (i + 1), 0);
  return { avgHr: inside.reduce((s, m) => s + m.hr, 0) / inside.length, maxHr: Math.max(...inside.map((m) => m.hr)), zones, trimp };
}

export function buildSessions(days: HealthDay[], motion: PhoneActivity[], captures: any[], mins: MinuteRec[], age: number): Session[] {
  const out: Session[] = [];
  for (const d of days) for (const w of d.workouts ?? []) {
    const def = WORKOUT[w.type] ?? WORKOUT[3000];
    const end = w.end ?? w.start + w.min * 60, hr = hrOf(w.start, end, mins, age);
    out.push({ id: `hk-${w.start}`, start: w.start, end, name: def.name, icon: def.icon, source: 'Apple Health', device: w.source, min: w.min,
      kcal: w.kcal, km: w.km, avgHr: hr?.avgHr, maxHr: hr?.maxHr, zones: hr?.zones, load: hr ? hr.trimp : w.min * def.k, loadFromHr: !!hr });
  }
  const overlaps = (a: number, b: number) => out.some((s) => a < s.end && b > s.start);
  for (const m of motion) {
    const def = DETECTED[m.type]; const min = (m.end - m.start) / 60;
    if (!def || min < 10 || overlaps(m.start, m.end)) continue;
    const hr = hrOf(m.start, m.end, mins, age);
    out.push({ id: `cm-${m.start}`, start: m.start, end: m.end, name: def.name, icon: def.icon, source: 'iPhone motion', min: Math.round(min),
      avgHr: hr?.avgHr, maxHr: hr?.maxHr, zones: hr?.zones, load: hr ? hr.trimp : min * def.k, loadFromHr: !!hr });
  }
  for (const c of captures) {
    if (c.therapyId === 'sleep' || c.therapyId === 'overnight_sleep' || !c.endedAt) continue;
    if (overlaps(c.startedAt, c.endedAt)) continue;
    const min = Math.round((c.endedAt - c.startedAt) / 60); if (min < 5) continue;
    const hr = hrOf(c.startedAt, c.endedAt, mins, age);
    out.push({ id: `cap-${c.id}`, start: c.startedAt, end: c.endedAt, name: c.therapy ?? 'Session', icon: 'waveform.path.ecg', source: 'Telomy patch', min,
      avgHr: hr?.avgHr ?? c.summary?.meanHr, maxHr: hr?.maxHr, zones: hr?.zones, load: hr ? hr.trimp : min * 1.5, loadFromHr: !!hr });
  }
  return out.sort((a, b) => b.start - a.start);
}

/** Daily loads for the last n days (index n-1 = today). */
export function dailyLoads(sessions: Session[], n: number) {
  const day0 = new Date(); day0.setHours(0, 0, 0, 0);
  const loads = Array.from({ length: n }, () => 0);
  for (const s of sessions) {
    const i = n - 1 - Math.floor((day0.getTime() / 1000 - new Date(new Date(s.start * 1000).setHours(0, 0, 0, 0)).getTime() / 1000) / 86400);
    if (i >= 0 && i < n) loads[i] += s.load;
  }
  return loads;
}

/** Acute:chronic load ratio (7-day sum vs mean weekly load over 28 days) and what it suggests. */
export function trainingStatus(loads28: number[]) {
  const acute = loads28.slice(-7).reduce((a, b) => a + b, 0);
  const chronic = loads28.reduce((a, b) => a + b, 0) / 4;
  if (chronic < 1) return { ratio: null as number | null, acute, chronic, label: 'Building a baseline', tone: 'muted' as const, advice: 'Log or record a few sessions and Telomy will show how your load is changing.' };
  const r = acute / chronic;
  if (r < 0.8) return { ratio: r, acute, chronic, label: 'Recovering', tone: 'info' as const, advice: 'This week is lighter than your usual. Good after a hard block; keep it short-lived to hold fitness.' };
  if (r <= 1.3) return { ratio: r, acute, chronic, label: 'Productive', tone: 'good' as const, advice: 'Load is in step with what your body is used to: the range where fitness builds steadily.' };
  if (r <= 1.5) return { ratio: r, acute, chronic, label: 'Pushing', tone: 'warn' as const, advice: 'Load is rising faster than usual. Fine for a planned block; watch recovery and sleep.' };
  return { ratio: r, acute, chronic, label: 'Spiking', tone: 'bad' as const, advice: 'This week is far above your usual. Ease off or add a rest day; sudden spikes raise injury and illness risk.' };
}
