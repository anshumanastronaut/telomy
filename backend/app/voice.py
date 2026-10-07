"""Sinc voice: speech → text → actions, plus voice-stress biomarkers.

Pipeline (phone today; Telomy Band later — same server contract):
  1. Capture   — push-to-talk now. Always-on mode = on-device VAD (Silero) gating a wake-word spotter ("Hey Sinc";
                 Porcupine / openWakeWord) so the main recogniser sleeps until speech; on the band a low-power keyword-
                 spotting core does this at < 1 mW. Speaker verification (ECAPA-TDNN embeddings, enrolled from 3 phrases,
                 updated with high-confidence utterances) drops other voices before anything leaves the device.
  2. Transcribe — Whisper (multilingual, 99 languages incl. Hindi/Tamil/Bengali; code-switching Hinglish) running locally
                 via faster-whisper; denoise (RNNoise/DeepFilterNet) for noisy rooms.
  3. Understand — an open intent engine (any sentence → meal, drink, smoke, caffeine, water, mood/stress, symptom, sleep,
                 activity, therapy, medication, routine or question). Claude does this when a key is configured; the
                 deterministic multilingual parser below always runs as the grounded fallback.
  4. Voice stress — acoustic features only (F0 mean/variability, jitter, shimmer, HNR, speech rate, pause ratio) compared
                 with the person's own baseline; fused with HRV like the Echo OS Cognitive Load Index. Raw audio is never
                 stored. Research-grade (evidence C); never a diagnosis.
"""
import io
import math
import re
import wave
from datetime import datetime, timedelta

import numpy as np

from . import db, engine, food

SCHEMA = """
CREATE TABLE IF NOT EXISTS voice_samples (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, language TEXT, text TEXT, features TEXT,
  stress REAL, intents TEXT, source TEXT);
"""
_MODEL = None


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


# ----------------------------------------------------------------------------- audio


def decode(data: bytes, filename: str = "audio.wav") -> np.ndarray:
    """Any container (wav / m4a / aac / webm) → mono float32 at 16 kHz."""
    if data[:4] == b"RIFF":
        w = wave.open(io.BytesIO(data))
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() > 1:
            a = a.reshape(-1, w.getnchannels()).mean(1)
        sr = w.getframerate()
    else:
        from faster_whisper.audio import decode_audio
        return decode_audio(io.BytesIO(data), sampling_rate=16000)
    if sr != 16000:
        x = np.linspace(0, len(a) - 1, int(len(a) * 16000 / sr))
        a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
    return a


def transcribe(audio: np.ndarray, language: str | None = None) -> dict:
    global _MODEL
    from faster_whisper import WhisperModel
    if _MODEL is None:
        _MODEL = WhisperModel("small", device="cpu", compute_type="int8")
    segs, info = _MODEL.transcribe(audio, language=language, vad_filter=True, beam_size=3)
    return {"text": " ".join(s.text.strip() for s in segs).strip(), "language": info.language,
            "language_probability": round(info.language_probability, 2), "model": "whisper-small (local, int8)"}


def acoustics(a: np.ndarray, sr: int = 16000) -> dict:
    """Prosody and voice-quality features from 40 ms frames (autocorrelation pitch tracker)."""
    if len(a) < sr // 2:
        return {"voiced_s": 0}
    a = a - a.mean()
    fl, hop = int(0.04 * sr), int(0.01 * sr)
    frames = [a[i:i + fl] for i in range(0, len(a) - fl, hop)]
    energy = np.array([float(np.sqrt(np.mean(f ** 2))) for f in frames])
    thr = max(1e-4, np.percentile(energy, 30) * 2.5)
    voiced = energy > thr
    f0, amp, hnr = [], [], []
    lo, hi = int(sr / 400), int(sr / 70)
    for f, v in zip(frames, voiced):
        if not v:
            f0.append(np.nan)
            continue
        f = f * np.hanning(len(f))
        ac = np.correlate(f, f, "full")[len(f) - 1:]
        if ac[0] <= 0:
            f0.append(np.nan)
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        r = ac[lag] / ac[0]
        if r < 0.3:
            f0.append(np.nan)
            continue
        f0.append(sr / lag)
        amp.append(float(np.max(np.abs(f))))
        hnr.append(10 * math.log10(max(r, 1e-6) / max(1 - r, 1e-6)))
    f0 = np.array(f0)
    good = f0[~np.isnan(f0)]
    if len(good) < 10:
        return {"voiced_s": round(voiced.sum() * hop / sr, 1)}
    periods = 1 / good
    jitter = float(np.mean(np.abs(np.diff(periods))) / np.mean(periods) * 100)
    shimmer = float(np.mean(np.abs(np.diff(amp))) / np.mean(amp) * 100) if len(amp) > 2 else None
    onsets = int(np.sum(np.diff(voiced.astype(int)) == 1))
    dur = len(a) / sr
    return {"duration_s": round(dur, 1), "voiced_s": round(voiced.sum() * hop / sr, 1), "f0_mean": round(float(np.median(good)), 1),
            "f0_sd": round(float(np.std(good)), 1), "f0_cv": round(float(np.std(good) / np.mean(good)), 3), "jitter_pct": round(jitter, 2),
            "shimmer_pct": round(shimmer, 2) if shimmer is not None else None, "hnr_db": round(float(np.median(hnr)), 1),
            "rate_per_s": round(onsets / dur, 2), "pause_ratio": round(1 - voiced.mean(), 2), "energy_db": round(20 * math.log10(float(energy[voiced].mean()) + 1e-9), 1)}


STRESS_W = {"f0_mean": 0.30, "f0_cv": -0.15, "jitter_pct": 0.20, "rate_per_s": 0.20, "pause_ratio": -0.10, "hnr_db": -0.15}


def stress_score(feat: dict) -> dict:
    """0–100 vs the person's own baseline (z-scores); falls back to a low-confidence population prior for the first 5 samples."""
    if not feat.get("f0_mean"):
        return {"score": None, "confidence": 0, "basis": "Not enough voiced speech (need ≥ 1 s)."}
    hist = [db.unj(r["features"], {}) for r in db.rows("SELECT features FROM voice_samples ORDER BY id DESC LIMIT 60")]
    hist = [h for h in hist if h.get("f0_mean")]
    z = 0.0
    if len(hist) >= 5:
        for k, w in STRESS_W.items():
            vals = [h[k] for h in hist if h.get(k) is not None]
            if feat.get(k) is None or len(vals) < 5:
                continue
            m, sd = float(np.mean(vals)), float(np.std(vals)) or 1e-6
            z += w * (feat[k] - m) / sd
        conf, basis = min(0.7, 0.3 + 0.01 * len(hist)), f"Compared with your own {len(hist)} recent voice samples."
    else:
        z = 0.6 * ((feat.get("rate_per_s", 3) - 3.2) / 1.0) + 0.4 * ((feat.get("jitter_pct", 1.2) - 1.2) / 0.6)
        conf, basis = 0.15, "Population prior — Telomy needs 5 samples to learn your normal voice."
    hb = engine.signal_baseline("hrv", days=7)
    hb30 = engine.signal_baseline("hrv", days=30)
    hrv_part = None
    if hb and hb30:
        hrv_part = max(0.0, min(1.0, 0.5 - (hb["mean"] - hb30["mean"]) / (hb30["sd"] * 4 or 1)))
    voice_part = 1 / (1 + math.exp(-z))
    score = 100 * (0.5 * voice_part + 0.5 * hrv_part) if hrv_part is not None else 100 * voice_part
    return {"score": round(score), "voice_component": round(100 * voice_part), "hrv_component": round(100 * hrv_part) if hrv_part is not None else None,
            "confidence": round(conf, 2), "basis": basis + (" Fused with your 7-day HRV (Echo OS cognitive-load style)." if hrv_part is not None else ""),
            "label": "high" if score >= 70 else "elevated" if score >= 55 else "typical",
            "note": "Voice-stress analysis is research-grade (evidence C) and never a diagnosis."}


# ----------------------------------------------------------------------------- understanding (multilingual)

HI = {  # Hindi / Hinglish → English keywords (incl. common transcription variants)
    "अंडे": "eggs", "अंडा": "egg", "अंदे": "eggs", "दाल": "dal", "डाल": "dal", "चावल": "rice", "रोटी": "roti", "सब्ज़ी": "vegetables",
    "सब्जी": "vegetables", "चाय": "tea", "कॉफी": "coffee", "कॉफ़ी": "coffee", "पानी": "water", "सिगरेट": "cigarette", "दारू": "alcohol",
    "शराब": "alcohol", "वोडका": "vodka", "बीयर": "beer", "तनाव": "stress", "तनाअव": "stress", "टेंशन": "stress", "थकान": "tired", "थका": "tired",
    "नींद": "sleep", "सोया": "slept", "सो": "sleep", "दौड़": "run", "चला": "walked", "सिरदर्द": "headache", "खाया": "ate", "खाई": "ate", "काई": "ate", "खाए": "ate",
    "खाना": "meal", "पिया": "drank", "पी": "drank", "मीठा": "sweet", "चिकन": "chicken", "गिलास": "glass", "लीटर": "litre", "दो": "2", "तीन": "3",
    "चार": "4", "एक": "1", "पांच": "5", "कल": "yesterday", "आज": "today", "सुबह": "morning", "शाम": "evening", "रात": "night",
    "kal": "yesterday", "aaj": "today", "khaya": "ate", "khana": "meal", "piya": "drank", "daaru": "alcohol", "tension": "stress",
    "neend": "sleep", "anda": "egg", "ande": "eggs", "chawal": "rice", "paani": "water", "thaka": "tired",
}
NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "a couple of": 2, "a": 1, "an": 1, "half": 0.5}


def normalise(text: str) -> str:
    t = text.lower()
    for k, v in sorted(HI.items(), key=lambda x: -len(x[0])):
        t = re.sub(rf"(?<![\w]){re.escape(k)}(?![\w])", v, t) if k.isascii() else t.replace(k, f" {v} ")
    for k, v in NUM.items():
        t = re.sub(rf"\b{k}\b(?=\s+(boiled|eggs?|glass|cups?|cigarettes?|pegs?|beers?|shots?|litres?|liters?|hours?|minutes?))", str(v), t)
    return re.sub(r"\s+", " ", t).strip()


def _when(t: str, now: datetime) -> datetime:
    base = now - timedelta(days=1) if "yesterday" in t else now
    m = re.search(r"\b(?:at|around)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", t)
    if m:
        h = int(m.group(1)) % 12 + (12 if (m.group(3) == "pm" or (not m.group(3) and int(m.group(1)) < 7)) else 0)
        return base.replace(hour=h, minute=int(m.group(2) or 0), second=0)
    for word, h in (("morning", 8), ("lunch", 13), ("afternoon", 15), ("evening", 19), ("dinner", 21), ("night", 22)):
        if word in t:
            return base.replace(hour=h, minute=0, second=0)
    return base


def _num(t: str, words: str, default=1.0):
    m = re.search(rf"(\d+(?:\.\d+)?)\s*(?:x\s*)?(?:{words})", t)
    return float(m.group(1)) if m else default


def understand(text: str) -> dict:
    """Any sentence → list of intents (several per sentence allowed)."""
    t = normalise(text)
    now = datetime.fromisoformat(engine.now_iso())
    when = _when(t, now)
    out = []
    if re.search(r"\?$|^(what|why|how|when|should|is|are|can|does|do|kya|kaise|kyun)\b", t.strip()):
        out.append({"intent": "question", "text": text})
        return {"normalised": t, "intents": out}
    # routine — long descriptions with several times of day
    if (len(re.findall(r"\b\d{1,2}\s*(?:am|pm)\b|\bat \d{1,2}\b", t)) >= 3 or "routine" in t or "every day" in t or "everyday" in t) and len(t) > 120:
        out.append({"intent": "routine", "text": text})
        return {"normalised": t, "intents": out}
    if re.search(r"\b(cigarette|cigarettes|smoke|smoked|sutta|bidi)\b", t):
        out.append({"intent": "smoke", "count": int(_num(t, "cigarettes?|sutta|smokes?")), "ts": when.isoformat(timespec="minutes")})
    alc = re.search(r"\b(vodka|whisky|whiskey|rum|gin|beer|beers|wine|peg|pegs|alcohol|drinks)\b", t)
    if alc and re.search(r"\b(had|drank|drink|drinking|took|\d+\s*ml|peg|pegs|glass|beers?)\b", t):
        ml = _num(t, "ml", 0)
        pegs = _num(t, "pegs?|shots?|glass(?:es)?|beers?|drinks?", 1)
        kind = alc.group(1)
        abv = 0.05 if "beer" in kind else 0.13 if "wine" in kind else 0.40
        vol = ml or pegs * (330 if "beer" in kind else 150 if "wine" in kind else 60)
        grams = round(vol * abv * 0.789, 1)
        out.append({"intent": "alcohol", "drink": kind, "ml": vol, "grams_alcohol": grams, "std_drinks_india": round(grams / 10, 1), "ts": when.isoformat(timespec="minutes")})
    if re.search(r"\b(coffee|espresso|tea|chai)\b", t) and not alc:
        out.append({"intent": "caffeine", "drink": re.search(r"\b(coffee|espresso|tea|chai)\b", t).group(1), "cups": _num(t, "cups?", 1),
                    "late": when.hour >= 14, "ts": when.isoformat(timespec="minutes")})
    if re.search(r"\b(water)\b", t) and re.search(r"\d+(\.\d+)?\s*(l|litres?|liters?|glass(es)?)\b", t):
        litres = _num(t, "l\\b|litres?|liters?", 0) or _num(t, "glass(?:es)?", 1) * 0.25
        out.append({"intent": "water", "litres": litres})
    meal = re.search(r"\b(ate|had|eaten|lunch|dinner|breakfast|meal|snack)\b", t)
    foods = [k for k in food.FOODS if re.search(rf"\b{re.escape(k)}", t)] if hasattr(food, "FOODS") else []
    if (meal and foods) or len(foods) >= 2:
        out.append({"intent": "meal", "text": text if t == text.lower() else t, "foods": foods, "ts": when.isoformat(timespec="minutes")})
    mood = re.search(r"\b(stressed|stress|anxious|tired|exhausted|calm|happy|low|sad|angry|overwhelmed|great|good)\b", t)
    if mood:
        neg = mood.group(1) in ("stressed", "stress", "anxious", "tired", "exhausted", "low", "sad", "angry", "overwhelmed")
        out.append({"intent": "mood", "feeling": mood.group(1), "valence": -1 if neg else 1, "ts": when.isoformat(timespec="minutes")})
    sym = re.search(r"\b(headache|bloating|nausea|acidity|reflux|back pain|knee pain|cold|fever|cough|dizzy)\b", t)
    if sym:
        out.append({"intent": "symptom", "symptom": sym.group(1), "ts": when.isoformat(timespec="minutes")})
    sl = re.search(r"\b(slept|sleep)\b.*?(\d+(?:\.\d+)?)\s*(hours|hrs|h)\b", t)
    if sl:
        out.append({"intent": "sleep", "hours": float(sl.group(2))})
    ther = re.search(r"\b(cryo|cryotherapy|cold plunge|ice bath|sauna|hbot|hyperbaric|red light|pemf|compression|float)\b", t)
    if ther and re.search(r"\b(starting|start|entering|going into|about to|in the|getting in)\b", t):
        mod = {"cryo": "cryo", "cryotherapy": "cryo", "cold plunge": "cold", "ice bath": "cold", "sauna": "sauna", "hbot": "hbot_mild",
               "hyperbaric": "hbot_mild", "red light": "redlight", "pemf": "pemf", "compression": "compression", "float": "float"}[ther.group(1)]
        out.append({"intent": "therapy_start", "modality": mod})
    act = re.search(r"\b(bowl(?:ed|ing)?|bowling spell|golf|round of golf|ran|run|running|walked|walk|gym|lifted|cycled|swim|swam|yoga|played|match|practice|nets)\b", t)
    if act and not ther:
        dur = re.search(r"(\d+)\s*(min|mins|minutes|hours|hrs|h)\b", t)
        minutes = (int(dur.group(1)) * (60 if dur.group(2).startswith("h") else 1)) if dur else None
        out.append({"intent": "activity", "activity": act.group(1), "minutes": minutes, "text": text, "ts": when.isoformat(timespec="minutes")})
    med = re.search(r"\b(took|taken|had)\b.*\b(glutathione|vitamin d|magnesium|omega|metformin|statin|rosuvastatin|tablet|pill|medicine|supplement)\b", t)
    if med:
        out.append({"intent": "medication", "name": med.group(2), "ts": when.isoformat(timespec="minutes")})
    if not out:
        out.append({"intent": "note", "text": text})
    return {"normalised": t, "intents": out}


def act(parsed: dict, original: str) -> list[dict]:
    """Execute intents: write events/meals so every voice log feeds the correlation engine."""
    done = []
    for it in parsed["intents"]:
        k = it["intent"]
        if k == "smoke":
            for _ in range(it["count"]):
                db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", (it["ts"], "smoke", "Cigarette", None, db.j({"via": "voice"})))
            done.append({"intent": k, "message": f"Logged {it['count']} cigarette{'s' if it['count'] != 1 else ''} at {it['ts'][11:16]}."})
        elif k == "alcohol":
            db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)",
                     (it["ts"], "alcohol", f"{int(it['ml'])} ml {it['drink']}", None, db.j({**it, "via": "voice"})))
            done.append({"intent": k, "message": f"Logged {int(it['ml'])} ml {it['drink']} ≈ {it['grams_alcohol']} g alcohol ({it['std_drinks_india']} standard drinks)."})
        elif k == "caffeine":
            kind = "caffeine_late" if it["late"] else "caffeine"
            db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", (it["ts"], kind, f"{it['drink'].title()}", None, db.j({"via": "voice"})))
            done.append({"intent": k, "message": f"Logged {it['drink']} at {it['ts'][11:16]}" + (" — after 2 pm, Telomy will watch tonight's sleep." if it["late"] else ".")})
        elif k == "meal":
            a = food.analyze(it.get("text") or original)  # normalised English for non-English speech
            db.exec_("INSERT INTO meals (ts, name, analysis) VALUES (?,?,?)", (it["ts"], original[:120], db.j({**a, "source": "voice"})))
            done.append({"intent": k, "message": f"Meal logged: ~{round(a.get('kcal') or 0)} kcal, {round(a.get('protein') or 0)} g protein, score {a.get('score')}."})
        elif k == "mood":
            sev = 2 if it["valence"] < 0 else 4
            kind = "stress" if it["feeling"] in ("stressed", "stress", "anxious", "overwhelmed") else "mood"
            db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", (it["ts"], kind, it["feeling"].capitalize(), sev, db.j({"via": "voice", "note": original[:200]})))
            done.append({"intent": k, "message": f"Noted you feel {it['feeling']}."})
        elif k == "symptom":
            db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", (it["ts"], "symptom", it["symptom"].capitalize(), 2, db.j({"via": "voice"})))
            done.append({"intent": k, "message": f"Symptom logged: {it['symptom']}."})
        elif k == "activity":
            from . import activities
            done.append({"intent": k, **activities.log_from_voice(it)})
        elif k == "therapy_start":
            from . import therapy
            try:
                s = therapy.start_session(1, it["modality"])
                done.append({"intent": k, "session_id": s["id"], "message": f"{therapy.MODALITIES[it['modality']]['name']} started — tracking your response."})
            except PermissionError as e:
                done.append({"intent": k, "message": str(e)})
        elif k == "medication":
            db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", (it["ts"], "medication", it["name"].title(), None, db.j({"via": "voice"})))
            done.append({"intent": k, "message": f"Logged {it['name']}."})
        elif k == "water":
            done.append({"intent": k, "message": f"{it['litres']} L water noted."})
        elif k == "sleep":
            done.append({"intent": k, "message": f"Sleep {it['hours']} h noted (your ring data stays the source of truth)."})
        elif k == "routine":
            from . import routine
            r = routine.parse(it["text"])
            done.append({"intent": k, "routine": r, "message": f"Routine understood: {len(r['items'])} items. Review and save it."})
        elif k == "question":
            from . import sinc
            ans = sinc.ask(it["text"], None, "quick")
            done.append({"intent": k, "answer": ans.get("answer"), "message": ans.get("answer")})
        else:
            db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", (engine.now_iso(), "note", original[:80], None, db.j({"via": "voice"})))
            done.append({"intent": "note", "message": "Saved as a note in your Vault."})
    return done


def command(text: str, features: dict | None = None, language: str | None = None, source: str = "typed") -> dict:
    parsed = understand(text)
    actions = act(parsed, text)
    st = stress_score(features) if features else None
    db.exec_("INSERT INTO voice_samples (ts, language, text, features, stress, intents, source) VALUES (?,?,?,?,?,?,?)",
             (engine.now_iso(), language, text[:500], db.j(features or {}), st["score"] if st else None, db.j(parsed["intents"]), source))
    return {"text": text, "language": language, "normalised": parsed["normalised"], "intents": parsed["intents"], "actions": actions, "stress": st}


def from_audio(data: bytes, filename: str = "audio.wav", language: str | None = None) -> dict:
    a = decode(data, filename)
    tr = transcribe(a, language)
    feat = acoustics(a)
    out = command(tr["text"], feat, tr["language"], "voice") if tr["text"] else {"text": "", "actions": [], "stress": stress_score(feat)}
    out["transcription"] = tr
    out["features"] = feat
    return out


def stress_trend() -> dict:
    rows = db.rows("SELECT ts, stress, language FROM voice_samples WHERE stress IS NOT NULL ORDER BY ts")
    return {"samples": rows[-60:], "n": len(rows), "baseline_ready": len(rows) >= 5,
            "how": "Pitch, pitch variability, jitter, harmonics-to-noise and speech rate vs your own baseline, fused with HRV. Audio is never stored."}


DESIGN = {
    "always_on": [
        "Stage 1 — voice-activity detection (Silero VAD, ~1 ms per 30 ms frame) wakes nothing until there is speech.",
        "Stage 2 — wake-word spotter ('Hey Sinc') on-device (Picovoice Porcupine or openWakeWord); custom phrase, < 1 % CPU on modern phones.",
        "Stage 3 — speaker verification (ECAPA-TDNN embedding vs your enrolled voiceprint, cosine ≥ 0.7); other voices are discarded on-device.",
        "Stage 4 — Whisper transcription (multilingual), denoised first; your corrections fine-tune vocabulary and the voiceprint adapts with each confident utterance.",
        "iOS allows background listening only with the audio background mode and shows the orange mic dot; Android needs a foreground service (type microphone).",
        "Telomy Band: a low-power keyword-spotting core listens at < 1 mW and wakes the phone only on 'Hey Sinc' — the battery-friendly always-on path.",
    ],
    "privacy": ["Raw audio never leaves the device or is stored; only text and numeric acoustic features.",
                "Separate DPDP consent for voice logging and for voice-stress analysis; revocable in the Consent centre."],
    "languages": "Whisper covers 99 languages incl. Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi and code-switched Hinglish.",
}
