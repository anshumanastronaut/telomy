"""In-session physiology: what happens inside the cryo chamber, the hyperbaric chamber, the sauna, under the red light.

Two halves:

1. ODE prior (simulation). A first-order physiological state model integrated at 1 Hz — each signal relaxes toward a
   phase- and stimulus-dependent target with its own time constant (dx/dt = (target − x) / τ). Targets and time
   constants are the literature-calibrated values from the Echo OS / Telomy Halo specification:
     • Whole-body cryotherapy  — Louis et al. 2020 (Eur J Appl Physiol): HR +8–20 bpm, RMSSD +50–100 % at 20 min,
       not significant at −60 °C; habituation ×0.8 per consecutive day; skin −8 to −15 °C in 3 min.
     • Cold-water immersion     — cold-shock response: HR +15–40 bpm and gasp in the first 30 s.
     • HBOT                     — StatPearls 2025; Lund 2003; PMC 2025 (1.3 ATA): HR −5 to −15 bpm, SpO₂ 99–100 %,
       HF power +40–60 %, compression spike +5–15 bpm.
     • Sauna                    — Laukkanen 2019 (73 °C, 30 min): peak HR 100–150, post HR −5 to −12 bpm; AJP-RICU 2025:
       FIR core +0.3–0.5 °C vs traditional +0.8 °C.
   Other modalities (PBM, PEMF, compression, vibroacoustic, H₂, float, breathwork, IHHT, EWOT, IV) use effect sizes from
   their trials and are graded C/D — the simulator says so.
   Every simulated trace is labelled "simulated (ODE prior)". Real traces arrive through ingest() from a chest strap,
   patch, watch or the machine's own telemetry (HBOT via flash buffer + MQTT merge) and replace the prior.

2. Session analytics (works on any trace). Peak HR rise, HRV suppression and rebound, the recovery constant k
   (exponential fit), thermoregulatory recovery index (TRI, minutes to rewarm 5 °C from the nadir), SpO₂ kinetics,
   cardiac load, perfusion change, PBM dose, signal quality and deterministic safety tiers (outside any model).
"""
import math
import random

SIGNALS = ["hr", "rmssd", "spo2", "skin", "core", "resp", "sbp", "eda", "perf"]
LABELS = {"hr": ("Heart rate", "bpm"), "rmssd": ("HRV (RMSSD)", "ms"), "spo2": ("SpO₂", "%"), "skin": ("Skin temperature", "°C"),
          "core": ("Core temperature (est.)", "°C"), "resp": ("Breathing rate", "/min"), "sbp": ("Systolic BP (proxy)", "mmHg"),
          "eda": ("Skin conductance (EDA)", "µS"), "perf": ("Perfusion index", "%")}
TAU = {"hr": 12, "rmssd": 40, "spo2": 60, "skin": 90, "core": 600, "resp": 15, "sbp": 30, "eda": 45, "perf": 60}  # seconds

# Literature validation targets (identical to the Echo OS PINN ValidationMetrics + cold-shock literature)
TARGETS = {
    "cryo": {"hr_peak_delta": (8, 20, "Louis et al. 2020"), "rebound_pct": (50, 100, "Louis et al. 2020"),
             "skin_drop": (-15, -8, "Cryotherapy skin-temperature studies")},
    "cold": {"hr_peak_delta": (15, 40, "Cold-shock response (Tipton 2017)")},
    "hbot": {"spo2_peak": (99, 100, "Clinical standard at ≥2 ATA, 100 % O₂"), "hr_stable_delta": (-15, -5, "Lund 2003; PMC 2025")},
    "sauna": {"hr_peak": (100, 150, "Laukkanen et al. 2019"), "hr_post_delta": (-12, -5, "Laukkanen et al. 2019"),
              "core_rise": (0.5, 1.1, "Laukkanen 2019; AJP-RICU 2025")},
    "sauna_ir": {"hr_peak": (80, 110, "AJP-RICU 2025"), "core_rise": (0.3, 0.6, "AJP-RICU 2025")},
}


def theta_from(profile: dict) -> dict:
    """Personal parameters (θ) from what the Vault knows. Population prior where data is missing."""
    age = profile.get("age", 40)
    hrv_night = profile.get("hrv", 50)
    fitness = min(1.0, max(0.0, ((profile.get("vo2max") or 40) - 25) / 30))
    metabolic = min(1.0, max(0.0, ((profile.get("hba1c") or 5.4) - 5.2) / 1.2 * 0.5 + ((profile.get("bmi") or 24) - 23) / 10 * 0.5))
    stiff = min(1.0, max(0.0, ((profile.get("pwv") or (6 + 0.06 * age)) - 6) / 6))
    return {
        "hr0": round(profile.get("rhr", 62) + 9, 1),             # seated, awake, pre-session
        "hrv0": round(max(12, hrv_night * 0.72), 1),               # seated daytime RMSSD ≈ 70 % of nocturnal
        "spo2_0": profile.get("spo2", 97.3), "sbp0": profile.get("sbp", 122), "skin0": 33.0, "core0": 36.8,
        "resp0": 14.5, "eda0": 2.0, "perf0": 3.0, "age": age,
        "sns": 1.0 + 0.25 * metabolic, "pns": max(0.45, 1.05 - 0.45 * metabolic - 0.15 * stiff + 0.2 * (fitness - 0.5)),
        "k": round(0.025 + 0.03 * fitness - 0.008 * metabolic, 4),  # 1/min HRV recovery constant (prior N(0.05, 0.02²) in docs)
        "vascular": max(0.45, 1.0 - 0.35 * metabolic - 0.3 * stiff),  # peripheral rewarming capacity (drives TRI)
        "thermal": 1.0, "fitness": fitness,
    }


def _phases(modality: str, p: dict) -> list[tuple[str, int]]:
    """(phase, seconds). Baseline 5 min and recovery 25 min frame every session."""
    m = p.get("minutes", 20)
    if modality in ("cryo", "cryo_local"):
        return [("baseline", 300), ("active", int(p.get("seconds", 180))), ("recovery", 1500)]
    if modality == "cold":
        return [("baseline", 300), ("active", int(p.get("minutes", 3) * 60)), ("recovery", 1500)]
    if modality in ("hbot", "hbot_mild"):
        return [("baseline", 300), ("compression", 600), ("stable", int(m * 60) - 1200), ("decompression", 600), ("recovery", 1200)]
    if modality == "contrast":
        out = [("baseline", 300)]
        for _ in range(int(p.get("rounds", 3))):
            out += [("hot", 600), ("cold", 120)]
        return out + [("recovery", 1200)]
    if modality == "ihht":
        out = [("baseline", 300)]
        for _ in range(int(p.get("cycles", 6))):
            out += [("hypoxic", 300), ("hyperoxic", 180)]
        return out + [("recovery", 900)]
    return [("baseline", 300), ("active", int(m * 60)), ("recovery", 1500)]


def _targets(modality: str, phase: str, t_in: float, p: dict, th: dict, hab: float) -> dict:
    """Signal targets for this phase. t_in = seconds into the phase."""
    T = {"hr": th["hr0"], "rmssd": th["hrv0"], "spo2": th["spo2_0"], "skin": th["skin0"], "core": th["core0"],
         "resp": th["resp0"], "sbp": th["sbp0"], "eda": th["eda0"], "perf": th["perf0"]}
    tau = dict(TAU)
    if phase == "baseline":
        return T, tau
    k_min = th["k"]
    if modality in ("cryo", "cryo_local", "cold") or (modality == "contrast" and phase == "cold"):
        local = modality == "cryo_local"
        if phase in ("active", "cold"):
            amb = p.get("chamber_c", p.get("water_c", 8 if modality != "cryo" else -120))
            if modality == "cold" or phase == "cold":
                shock = math.exp(-t_in / 25)  # cold-shock decays over ~30 s
                T["hr"] += (12 + 22 * shock) * th["sns"] * hab
                T["resp"] += 4 + 16 * shock
                T["skin"] = amb + 6
                tau["skin"] = 45
            else:
                depth = max(0.0, abs(min(amb, 0)) - 60) / 50  # Louis 2020: no effect at −60 °C, clear at −110 °C
                T["hr"] += (6 + 4 * depth) * th["sns"] * hab * (0.4 if local else 1)
                T["resp"] += 3 * depth
                T["skin"] = th["skin0"] - (0.11 * (abs(amb) - 30)) * th["thermal"] * (0.5 if local else 1)  # −110 °C → ≈ −9 °C in 3 min
                tau["skin"] = 22 if not local else 40
            T["rmssd"] = th["hrv0"] * (1 - 0.35 * min(1.0, hab + 0.2))
            T["sbp"] += 14 * th["sns"] * hab
            T["eda"] += 4 * th["sns"] * hab
            T["perf"] = th["perf0"] * 0.45
            tau["rmssd"] = 30
        else:  # recovery: parasympathetic rebound (β3 ≈ 0.06 /min) and rewarming from core blood flow
            amb = p.get("chamber_c", -120)
            depth = min(1.3, max(0.0, abs(min(amb, 0)) - 60) / 50) if modality in ("cryo", "cryo_local") else 0.7
            reb = (0.6 + 0.4 * depth) * th["pns"] * (0.75 + 0.25 * hab)
            T["rmssd"] = th["hrv0"] * (1 + reb)
            T["hr"] -= 3 * th["pns"]
            tau["rmssd"] = 60 / 0.06 / max(0.4, k_min / 0.04)
            tau["hr"] = 60 / (2 * k_min) / 3
            tau["skin"] = 60 / (0.048 * th["vascular"])  # TRI ≈ 14 min when vascular = 1 (healthy 12–18 min)
            T["perf"] = th["perf0"] * 1.1
    elif modality in ("hbot", "hbot_mild"):
        ata, o2 = p.get("ata", 2.0), p.get("o2_pct", 100) / 100
        s = (ata - 1.0) / 1.4
        if phase == "compression":
            T["hr"] += 8 * hab * (1 if t_in < 300 else 0.5)
            T["spo2"] = min(99.8, th["spo2_0"] + (2.3 * o2 + 0.6 * s))
            T["eda"] += 1.0
        elif phase == "stable":
            T["hr"] = th["hr0"] * (1 - (0.06 + 0.06 * s * o2))
            T["rmssd"] = th["hrv0"] * (1 + (0.12 + 0.2 * s * o2) * th["pns"])
            T["spo2"] = min(99.9, th["spo2_0"] + 2.5 * o2 + 0.6 * s)
            T["sbp"] += 4 * s  # baroreflex-mediated vasoconstriction
            tau["hr"] = 180
            tau["rmssd"] = 240
        elif phase == "decompression":
            T["hr"] = th["hr0"] * 0.96
            T["rmssd"] = th["hrv0"] * 1.15
            T["spo2"] = th["spo2_0"] + 0.8
        else:
            T["rmssd"] = th["hrv0"] * (1 + 0.1 * th["pns"])
            T["hr"] = th["hr0"] * 0.97
    elif modality in ("sauna", "sauna_ir") or (modality == "contrast" and phase == "hot"):
        temp = p.get("temp_c", 80 if modality != "sauna_ir" else 55)
        trad = modality != "sauna_ir"
        if phase in ("active", "hot"):
            T["core"] = th["core0"] + (0.022 if trad else 0.026) * (temp - 40) * th["thermal"]
            T["hr"] = th["hr0"] + (1.25 if trad else 0.8) * (temp - 35) * th["thermal"] * (1.1 - 0.25 * th["fitness"])
            T["skin"] = 39.2 if trad else 37.6
            T["rmssd"] = th["hrv0"] * 0.55
            T["eda"] += 7
            T["perf"] = th["perf0"] * 2.2
            T["resp"] += 3
            T["sbp"] -= 3
            tau["hr"] = 300
            tau["skin"] = 120
        else:
            T["hr"] = th["hr0"] - 8 * th["pns"]
            T["rmssd"] = th["hrv0"] * (1 + 0.22 * th["pns"])
            T["sbp"] -= 7
            tau["hr"] = 60 / (2 * k_min) / 2
            tau["core"] = 900
    elif modality == "ihht":
        if phase == "hypoxic":
            T["spo2"] = p.get("spo2_target", 86)
            T["hr"] += 9
            T["resp"] += 3
            tau["spo2"] = 50
        elif phase == "hyperoxic":
            T["spo2"] = 99.2
            T["hr"] -= 2
            tau["spo2"] = 40
    elif phase in ("active",):
        e = {  # (hr Δ, rmssd ×, sbp Δ, resp Δ, eda Δ, skin Δ, perf ×)
            "redlight": (-2, 1.08, -3, -0.5, -0.3, 0.8, 1.25), "pemf": (-3, 1.12, -2, -1.5, -0.5, 0.2, 1.05),
            "compression": (-3, 1.08, 4, -0.5, -0.2, 0.0, 1.0), "vibroacoustic": (-4, 1.18, -3, -3, -0.8, 0.1, 1.05),
            "h2_inhal": (-1, 1.03, 0, 0, 0, 0, 1.0), "float": (-6, 1.2, -6, -2.5, -1.0, 0.6, 1.1),
            "breathwork": (-2, 1.6, -4, -8.5, -0.6, 0.1, 1.05), "iv": (2, 0.98, 3, 0, 0.2, -0.2, 1.0),
            "ewot": (55, 0.45, 25, 10, 2.5, 1.0, 1.6), "halo": (-5, 1.22, -4, -3.5, -1.0, 0.9, 1.3),
            "wbv": (12, 0.85, 8, 3, 0.5, 0.3, 1.2), "acupuncture": (-3, 1.1, -3, -1, -0.4, 0.2, 1.05),
        }.get(modality, (0, 1.0, 0, 0, 0, 0, 1.0))
        T["hr"] += e[0]
        T["rmssd"] *= e[1]
        T["sbp"] += e[2]
        T["resp"] = max(5.5, T["resp"] + e[3])
        T["eda"] = max(0.3, T["eda"] + e[4])
        T["skin"] += e[5]
        T["perf"] *= e[6]
        if modality == "ewot":
            T["spo2"] = 99.0
        if modality == "breathwork":
            tau["rmssd"] = 25
    elif phase == "recovery":
        tail = {"vibroacoustic": 1.1, "float": 1.12, "breathwork": 1.1, "pemf": 1.06, "halo": 1.12, "redlight": 1.04}.get(modality, 1.0)
        T["rmssd"] = th["hrv0"] * tail
    return T, tau


def simulate(modality: str, params: dict, theta: dict, seed: int = 0, prior_sessions: int = 0, day_state: float = 1.0,
             step: int = 5, dt: int = 1) -> dict:
    """Integrate the ODE prior at 1 Hz; return a trace sampled every `step` seconds plus phase boundaries.

    prior_sessions = sessions of the same modality in the previous 5 days (habituation ×0.8 each, Louis 2020).
    day_state = that morning's HRV relative to baseline (alcohol the night before blunts the response).
    """
    rnd = random.Random(seed)
    hab = 0.8 ** prior_sessions if modality in ("cryo", "cold", "cryo_local") else 0.92 ** prior_sessions
    th = dict(theta)
    th["hrv0"] = theta["hrv0"] * day_state
    th["pns"] = theta["pns"] * (0.6 + 0.4 * day_state)
    x = {"hr": th["hr0"], "rmssd": th["hrv0"], "spo2": th["spo2_0"], "skin": th["skin0"], "core": th["core0"], "resp": th["resp0"],
         "sbp": th["sbp0"], "eda": th["eda0"], "perf": th["perf0"]}
    noise = {"hr": 1.4, "rmssd": 3.0, "spo2": 0.25, "skin": 0.08, "core": 0.01, "resp": 0.5, "sbp": 2.0, "eda": 0.12, "perf": 0.12}
    trace = {k: [] for k in SIGNALS}
    t_axis, phases, t = [], [], 0
    for phase, dur in _phases(modality, params):
        phases.append({"phase": phase, "start": t, "end": t + dur})
        for s in range(0, dur, dt):
            T, tau = _targets(modality, phase, s, params, th, hab)
            for k in SIGNALS:  # exact solution of dx/dt = (T − x)/τ over one step
                x[k] += (T[k] - x[k]) * (1 - math.exp(-dt / tau[k]))
            if t % step == 0:
                t_axis.append(t)
                for k in SIGNALS:
                    v = x[k] + rnd.gauss(0, noise[k])
                    if k == "spo2":
                        v = min(100.0, v)
                    trace[k].append(round(v, 2 if k in ("skin", "core", "eda", "perf") else 1))
            t += dt
    return {"t": t_axis, "signals": trace, "phases": phases, "step": step, "source": "simulated (ODE prior)",
            "habituation": round(hab, 2), "day_state": round(day_state, 2)}


# ----------------------------------------------------------------------------- analytics

def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _window(trace, key, a, b):
    return [v for t, v in zip(trace["t"], trace["signals"].get(key, [])) if a <= t < b and v is not None]


def analyse(modality: str, trace: dict, params: dict | None = None, age: float = 40) -> dict:
    """Session features + safety tier from any trace (simulated or real)."""
    params = params or {}
    ph = {p["phase"]: p for p in trace["phases"]}
    base = ph.get("baseline", {"start": 0, "end": 300})
    act_names = [p for p in ("active", "stable", "hot", "cold", "hypoxic", "compression") if p in ph]
    a0 = min(ph[p]["start"] for p in act_names) if act_names else base["end"]
    a1 = max(p["end"] for p in trace["phases"] if p["phase"] not in ("baseline", "recovery")) if act_names else a0
    rec = ph.get("recovery")
    f: dict = {"modality": modality, "source": trace.get("source", "device")}
    hr_pre, hrv_pre = _mean(_window(trace, "hr", base["start"], base["end"])), _mean(_window(trace, "rmssd", base["start"], base["end"]))
    act_hr = _window(trace, "hr", a0, a1)
    f["hr_pre"], f["rmssd_pre"] = r1(hr_pre), r1(hrv_pre)
    if act_hr:
        peak = max(act_hr[i:i + 3] and _mean(act_hr[i:i + 3]) for i in range(len(act_hr)))  # 15-s smoothed peak
        f["hr_peak"], f["hr_peak_delta"] = r1(peak), r1(peak - hr_pre)
        seg = [(t, v) for t, v in zip(trace["t"], trace["signals"]["hr"]) if a0 <= t < a1]
        f["t_peak_s"] = max(seg, key=lambda x: x[1])[0] - a0 if seg else None
        f["rmssd_min"] = r1(min(_window(trace, "rmssd", a0, a1) or [hrv_pre]))
        f["hrv_suppression_pct"] = r1((f["rmssd_min"] - hrv_pre) / hrv_pre * 100)
        cardiac = sum(1 for v in act_hr if v >= 100) * trace["step"] / 60
        f["cardio_load_min"] = r1(cardiac)
    if "stable" in ph:
        st = ph["stable"]
        f["hr_stable_delta"] = r1(_mean(_window(trace, "hr", st["start"] + (st["end"] - st["start"]) // 2, st["end"])) - hr_pre)
        f["rmssd_stable_pct"] = r1((_mean(_window(trace, "rmssd", st["start"] + 300, st["end"])) - hrv_pre) / hrv_pre * 100)
    sp = trace["signals"].get("spo2")
    if sp:
        f["spo2_pre"] = r1(_mean(_window(trace, "spo2", base["start"], base["end"])))
        f["spo2_peak"], f["spo2_min"] = r1(max(sp)), r1(min(sp))
        if modality in ("hbot", "hbot_mild", "ewot"):
            hit = next((t for t, v in zip(trace["t"], sp) if t >= a0 and v >= 99), None)
            f["t_spo2_99_min"] = r1((hit - a0) / 60) if hit is not None else None
    sk = trace["signals"].get("skin")
    if sk:
        skin_pre = _mean(_window(trace, "skin", base["start"], base["end"]))
        span = [(t, v) for t, v in zip(trace["t"], sk) if t >= a0]
        nadir_t, nadir = min(span, key=lambda x: x[1]) if span else (a0, skin_pre)
        hi_t, hi = max(span, key=lambda x: x[1]) if span else (a0, skin_pre)
        f["skin_pre"], f["skin_nadir"], f["skin_peak"] = r1(skin_pre), r1(nadir), r1(hi)
        f["skin_drop"] = r1(nadir - skin_pre)
        if nadir < skin_pre - 6:  # cold modalities: thermoregulatory recovery index
            back = next((t for t, v in span if t > nadir_t and v >= nadir + 5), None)
            f["tri_min"] = r1((back - nadir_t) / 60) if back else None  # Echo OS TRI: depends on how cold the chamber was
            half = next((t for t, v in span if t > nadir_t and v >= nadir + (skin_pre - nadir) / 2), None)
            f["rewarm_half_min"] = r1((half - nadir_t) / 60) if half else None  # temperature-independent personal trait
    co = trace["signals"].get("core")
    if co:
        f["core_rise"] = round(max(co) - co[0], 2)
    if rec:
        post_hr = _mean(_window(trace, "hr", rec["end"] - 300, rec["end"]))
        post_hrv = _mean(_window(trace, "rmssd", rec["start"] + 900, rec["start"] + 1260)) or _mean(_window(trace, "rmssd", rec["end"] - 300, rec["end"]))
        f["hr_post"], f["hr_post_delta"] = r1(post_hr), r1(post_hr - hr_pre)
        f["rmssd_post"], f["rebound_pct"] = r1(post_hrv), r1((post_hrv - hrv_pre) / hrv_pre * 100)
        # Recovery constant k: log-linear fit of the HRV gap closing during recovery
        pts = [(t - rec["start"], v) for t, v in zip(trace["t"], trace["signals"]["rmssd"]) if rec["start"] <= t < rec["end"]]
        if len(pts) > 20:
            top = max(v for _, v in pts[-36:])
            ys = [(t / 60, math.log(max(0.5, top - v))) for t, v in pts if top - v > 0.5]
            if len(ys) > 10:
                mx, my = _mean([a for a, _ in ys]), _mean([b for _, b in ys])
                sxx = sum((a - mx) ** 2 for a, _ in ys)
                slope = sum((a - mx) * (b - my) for a, b in ys) / sxx if sxx else 0
                k = max(0.005, -slope)
                if (f.get("rebound_pct") or 0) > 10 or modality in ("cryo", "cold", "sauna", "sauna_ir", "contrast"):
                    f["k_recovery"], f["half_life_min"] = round(k, 3), r1(math.log(2) / k)
    pe = trace["signals"].get("perf")
    if pe:
        f["perf_change_pct"] = r1((_mean(_window(trace, "perf", a0, a1)) - _mean(_window(trace, "perf", base["start"], base["end"]))) / 3 * 100)
    if modality == "redlight" and params.get("irradiance_mw_cm2"):
        f["dose_j_cm2"] = r1(params["irradiance_mw_cm2"] * params.get("minutes", 20) * 60 / 1000)
    sb = trace["signals"].get("sbp")
    if sb:
        f["sbp_peak_delta"] = r1(max(_window(trace, "sbp", a0, a1) or [0]) - _mean(_window(trace, "sbp", base["start"], base["end"])))
    f["sqi"] = 0.97 if f["source"].startswith("simulated") else trace.get("sqi", 0.9)
    f["safety"] = safety(modality, trace, f, age)
    f["vs_literature"] = against_literature(modality, f)
    return f


def r1(v):
    return None if v is None else round(v, 1)


def safety(modality: str, trace: dict, f: dict, age: float) -> dict:
    """Deterministic safety envelope — never a model output (Telomy DPR §6.2; Echo OS tiering)."""
    tier, reasons = 0, []
    hr_max = 220 - age
    s = trace["signals"]
    if max(s.get("hr") or [0]) > 0.9 * hr_max and modality not in ("ewot", "wbv"):
        tier, reasons = max(tier, 2), reasons + [f"Heart rate reached {round(max(s['hr']))} bpm (> 90% of age-predicted max)"]
    lo = min(s.get("spo2") or [100])
    floor = 80 if modality == "ihht" else 90
    if lo < floor:
        tier, reasons = 3, reasons + [f"SpO₂ fell to {lo}%"]
    elif modality != "ihht" and lo < 93:
        tier, reasons = max(tier, 1), reasons + [f"SpO₂ dipped to {lo}%"]
    if (f.get("sbp_peak_delta") or 0) > 35:
        tier, reasons = max(tier, 2), reasons + [f"Blood-pressure proxy rose {f['sbp_peak_delta']} mmHg"]
    if modality in ("sauna", "sauna_ir") and (f.get("core_rise") or 0) > 1.6:
        tier, reasons = max(tier, 2), reasons + [f"Estimated core temperature rose {f['core_rise']} °C"]
    return {"tier": tier, "reasons": reasons, "label": ["Normal", "Watch", "Staff check", "Stop session"][tier]}


def against_literature(modality: str, f: dict) -> list[dict]:
    key = "sauna_ir" if modality == "sauna_ir" else "cryo" if modality in ("cryo",) else modality
    out = []
    for metric, (lo, hi, src) in TARGETS.get(key, {}).items():
        v = f.get(metric)
        if v is None:
            continue
        out.append({"metric": metric, "value": v, "range": [lo, hi], "source": src,
                    "verdict": "typical" if lo <= v <= hi else "above" if v > hi else "below"})
    return out


def validate_prior(n: int = 40) -> dict:
    """Run the simulator across healthy-adult θ and check every literature target (the PINN pre-training gate)."""
    th = theta_from({"age": 38, "rhr": 60, "hrv": 55, "vo2max": 42, "hba1c": 5.3, "bmi": 23.5})
    runs = {"cryo": {"chamber_c": -120, "seconds": 180}, "cold": {"water_c": 8, "minutes": 3},
            "hbot": {"ata": 2.4, "o2_pct": 100, "minutes": 90}, "sauna": {"temp_c": 80, "minutes": 20},
            "sauna_ir": {"temp_c": 55, "minutes": 40}}
    report = {}
    for mod, p in runs.items():
        vals: dict[str, list] = {}
        for i in range(n):
            f = analyse(mod, simulate(mod, p, th, seed=i), p)
            for c in f["vs_literature"]:
                vals.setdefault(c["metric"], []).append(c["value"])
        report[mod] = []
        for metric, (lo, hi, src) in TARGETS["sauna_ir" if mod == "sauna_ir" else mod].items():
            m = _mean(vals.get(metric, [])) if vals.get(metric) else None
            report[mod].append({"metric": metric, "mean": r1(m), "range": [lo, hi], "source": src,
                                "pass": m is not None and lo <= m <= hi})
    report["all_pass"] = all(c["pass"] for k, v in report.items() if k != "all_pass" for c in v)
    return report
