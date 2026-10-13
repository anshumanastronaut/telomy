import Foundation

// Robust interpretation layer on top of KYAnalyzer: adaptive heart rate, artefact-aware HRV, motion/bad-data detection,
// activity and sleep state, and rhythm screening (wellness flags, not diagnoses).
// Thresholds marked [cal] are calibrated on PhysioNet (see docs/devices/KY_E_B1_ALGORITHMS.md and tools/validate).

// MARK: - Adaptive Kalman heart rate (after Li, Mark & Clifford 2008)

public struct KYKalmanHR {
    public private(set) var hr: Double?
    public private(set) var variance = 400.0          // bpm²
    private var lastTime: Double?
    private var nis = 1.0                               // EMA of normalised innovation squared
    private var outlierRun: [Double] = []
    public private(set) var lastUpdate: Double = -1e9

    public init() {}

    /// One beat. `quality` 0–1 scales the measurement noise; returns true if the beat was used.
    @discardableResult
    public mutating func update(time t: Double, rrMs: Double, quality: Double) -> Bool {
        guard rrMs >= 250, rrMs <= 2500 else { return false }
        let z = 60000 / rrMs
        guard let x = hr else { hr = z; variance = 64; lastTime = t; lastUpdate = t; return true }
        let dt = max(0.2, min(10, t - (lastTime ?? t)))
        lastTime = t
        // process noise: base 0.6 bpm²/s, inflated when innovations have been consistently large (real HR change)
        let q = 0.6 * dt * max(1, min(25, nis * nis))
        let p = variance + q
        // measurement noise: beat-to-beat HR jitters ±4 bpm with breathing at rest; poor quality inflates it
        let r = 16 / max(0.05, quality * quality)
        let s = p + r
        let innov = z - x
        let d2 = innov * innov / s
        if d2 > 16 {  // > 4 σ: outlier unless it keeps happening in the same direction (genuine fast change)
            outlierRun.append(innov)
            if outlierRun.count < 3 || !(outlierRun.allSatisfy { $0 > 0 } || outlierRun.allSatisfy { $0 < 0 }) {
                if outlierRun.count >= 3 { outlierRun.removeFirst() }
                variance = p
                return false
            }
        }
        outlierRun = []
        let k = p / s
        hr = x + k * innov
        variance = (1 - k) * p
        nis = 0.9 * nis + 0.1 * d2
        lastUpdate = t
        return true
    }

    /// Advance time without a beat (dropout): uncertainty grows.
    public mutating func coast(to t: Double) {
        guard let last = lastTime, t > last else { return }
        variance = min(900, variance + 0.6 * (t - last))
        lastTime = t
    }

    public var sd: Double { variance.squareRoot() }
}

// MARK: - Bad-data detector (2-s windows)

public enum KYWindowClass: String { case clean, noisy, motion, noContact = "no_contact", flat, saturated }

public struct KYNoiseMonitor {
    let fs: Double
    private var hf: Biquad, lf: Biquad, qrs1: Biquad, qrs2: Biquad
    private var buf: [Double] = [], hfPow = 0.0, lfPow = 0.0, qrsPow = 0.0, n = 0
    public private(set) var last: KYWindowClass = .clean
    public private(set) var motionIndex = 0.0  // EMA 0–1 over ~30 s

    public init(fs: Double) {
        self.fs = fs
        hf = .highpass(min(30, 0.45 * fs), fs: fs)     // muscle (EMG) band within the 100 Hz Nyquist
        lf = .lowpass(0.7, fs: fs)                      // baseline wander / electrode motion
        qrs1 = .highpass(5, fs: fs); qrs2 = .lowpass(15, fs: fs)
    }

    /// Feed raw µV; returns a class for every completed 2-s window.
    public mutating func feed(_ samples: [Int16], leadOn: Bool) -> [KYWindowClass] {
        var out: [KYWindowClass] = []
        for s in samples {
            let x = Double(s)
            buf.append(x)
            let h = hf.step(x), l = lf.step(x), q = qrs2.step(qrs1.step(x))
            hfPow += h * h; qrsPow += q * q
            lfPow += l * l
            n += 1
            if n >= Int(2 * fs) {
                out.append(classify(leadOn: leadOn))
                buf = []; hfPow = 0; lfPow = 0; qrsPow = 0; n = 0
            }
        }
        return out
    }

    private mutating func classify(leadOn: Bool) -> KYWindowClass {
        let m = buf.reduce(0, +) / Double(buf.count)
        let sd = (buf.map { ($0 - m) * ($0 - m) }.reduce(0, +) / Double(buf.count)).squareRoot()
        let sat = buf.filter { abs($0) >= 32000 }.count
        let deltas = zip(buf, buf.dropFirst()).map { abs($1 - $0) }
        let maxJump = deltas.max() ?? 0
        let c: KYWindowClass
        if !leadOn { c = .noContact }
        else if sat > 2 { c = .saturated }
        else if sd < 8 { c = .flat }                                         // < 8 µV: electrode not picking up ECG
        else {
            let emg = hfPow / max(1, qrsPow)                                  // muscle noise relative to QRS energy
            let wander = (lfPow / Double(n)).squareRoot()                     // baseline excursion RMS (µV)
            // [cal] on MIT-BIH NST "em"/"ma" records mixed into clean ECG at 0–12 dB SNR
            if wander > 1500 || maxJump > 4000 { c = .motion }
            else if emg > 0.35 || wander > 600 { c = .noisy }
            else { c = .clean }
        }
        last = c
        let bad = (c == .clean) ? 0.0 : 1.0
        motionIndex = 0.93 * motionIndex + 0.07 * bad  // ~30 s memory over 2-s windows
        return c
    }
}

// MARK: - HRV helpers

public enum KYRhythmStats {
    /// Shannon entropy of RR histogram (16 bins), after removing the 8 most extreme values (Dash et al. 2009).
    public static func shannonEntropy(_ rr: [Double]) -> Double {
        guard rr.count >= 16 else { return 0 }
        let m = rr.reduce(0, +) / Double(rr.count)
        let trimmed = rr.sorted { abs($0 - m) < abs($1 - m) }.dropLast(min(8, rr.count / 8))
        guard let lo = trimmed.min(), let hi = trimmed.max(), hi > lo else { return 0 }
        var bins = [Double](repeating: 0, count: 16)
        for v in trimmed { bins[min(15, Int((v - lo) / (hi - lo) * 16))] += 1 }
        let total = Double(trimmed.count)
        // normalised to 0–1 by the maximum entropy of 16 bins
        return -bins.filter { $0 > 0 }.map { ($0 / total) * log($0 / total) }.reduce(0, +) / log(16.0)
    }

    /// Turning point ratio: turning points / expected (2(n−2)/3) for a random series.
    public static func turningPointRatio(_ rr: [Double]) -> Double {
        guard rr.count >= 3 else { return 0 }
        var tp = 0
        for i in 1..<(rr.count - 1) where (rr[i] > rr[i - 1] && rr[i] > rr[i + 1]) || (rr[i] < rr[i - 1] && rr[i] < rr[i + 1]) { tp += 1 }
        return Double(tp) / (2 * Double(rr.count - 2) / 3)
    }

    /// Coefficient of sample entropy (Lake & Moorman 2011): SampEn − ln(2r) − ln(mean RR), r in seconds, m = 1.
    public static func cosEn(_ rrMs: [Double], r: Double = 0.03) -> Double? {
        let rr = rrMs.map { $0 / 1000 }
        guard rr.count >= 12 else { return nil }
        var rr2 = r
        for _ in 0..<5 {
            var a = 0, b = 0
            for i in 0..<(rr.count - 1) {
                for j in (i + 1)..<(rr.count - 1) where abs(rr[i] - rr[j]) <= rr2 {
                    b += 1
                    if abs(rr[i + 1] - rr[j + 1]) <= rr2 { a += 1 }
                }
            }
            if a >= 5 && b > 0 {
                let mean = rr.reduce(0, +) / Double(rr.count)
                // COSEn = SampEn + ln(2r) − ln(mean RR), seconds (Lake & Moorman 2011). The sign of ln(2r) was flipped
                // before 2026-10-13, which made every window pass the COSEn test.
                return -log(Double(a) / Double(b)) + log(2 * rr2) - log(mean)
            }
            rr2 += 0.01  // widen tolerance until enough matches (Lake & Moorman)
        }
        return nil
    }
}

// MARK: - Insight engine

public final class KYInsight {
    public enum Activity: String { case rest, light, active, moving, unknown }
    public enum Sleep: String { case awake, asleep, unknown }

    public struct Event: Equatable {
        public let type: String       // af_pattern, pause, bradycardia, tachycardia_rest, early_beats, bigeminy, trigeminy, poor_signal
        public let start: Double      // seconds (analyzer sample clock)
        public var end: Double
        public var detail: [String: Double]
    }

    public struct State {
        public var hr: Double?
        public var hrSd: Double?
        public var hrConfidence: String            // high / medium / low / none
        public var lnRmssd: Double?
        public var rmssd: Double?                  // smoothed (exp of smoothed lnRMSSD), clean beats only, 60-s window
        public var rmssd5: Double?
        public var hrvState: String                // ok / settling / active / irregular / noisy
        public var activity: Activity
        public var sleep: Sleep
        public var motionIndex: Double
        public var windowClass: String
        public var restingHr: Double
        public var earlyBeatsPerMin: Double
        public var afBurden60: Double              // fraction of the last 60 min flagged AF pattern
        public var openEvents: [String]
    }

    let fs: Double
    public private(set) var kalman = KYKalmanHR()
    private var noise: KYNoiseMonitor
    private var beats: [(t: Double, rr: Double, clean: Bool, raw: Bool)] = []   // last 15 min
    private var windowsBad: [(t: Double, c: KYWindowClass)] = []
    private var lnRmssdSmooth: Double?
    private var restingHr: Double
    private var hrMinutes: [Double] = []                                        // clean 1-min HR medians (24 h)
    private var epochs: [(t: Double, p: Double)] = []                           // sleep probability per 30-s epoch
    private var epochStart: Double = 0
    private var sleepState: Sleep = .unknown
    private var afWindows: [(t: Double, af: Bool)] = []
    private var open: [String: Event] = [:]
    public private(set) var events: [Event] = []
    /// Validation logs (bounded): sleep epochs (t, features, p) and AF windows (t, features, decision).
    public var keepLogs = false
    public private(set) var epochLog: [(t: Double, f: [Double], p: Double)] = []
    public private(set) var afLog: [(t: Double, f: [Double], af: Bool)] = []
    public var onEvent: ((Event) -> Void)?
    private var now: Double = 0
    // raw ECG (last ~80 s) and clean-beat sample indices, for the P-wave check in AF screening
    private var raw = [Float](repeating: 0, count: 8192)
    private var rawCount = 0
    private var cleanBeatSamples: [Int] = []

    public init(sampleRate fs: Double = 100, restingHr: Double = 65) {
        self.fs = fs
        noise = KYNoiseMonitor(fs: fs)
        self.restingHr = restingHr
    }

    /// Feed raw samples (for the noise monitor) and the analyzer's beats for the same chunk; `t` = seconds at chunk end.
    public func process(samples: [Int16], beats newBeats: [KYAnalyzer.Beat], leadOn: Bool, quality: KYAnalyzer.Quality) {
        now += Double(samples.count) / fs
        for v in samples { raw[rawCount & 8191] = Float(v); rawCount += 1 }
        for c in noise.feed(samples, leadOn: leadOn) {
            windowsBad.append((now, c))
        }
        windowsBad.removeAll { $0.t < now - 900 }
        let windowClean = noise.last == .clean
        let q: Double = !leadOn ? 0 : quality == .good ? 1 : quality == .acceptable ? 0.7 : quality == .poor ? 0.25 : 0.5
        for b in newBeats {
            guard let rr = b.rrMs else { continue }
            let t = b.sample / fs
            let clean = windowClean && (quality == .good || quality == .acceptable)
            let used = kalman.update(time: t, rrMs: rr, quality: windowClean ? q : q * 0.4)
            beats.append((t, rr, clean, used))
            if clean { cleanBeatSamples.append(Int(b.sample.rounded())); if cleanBeatSamples.count > 80 { cleanBeatSamples.removeFirst() } }
        }
        kalman.coast(to: now)
        beats.removeAll { $0.t < now - 900 }
        updateHRV()
        updateRestingHr()
        updateEpoch()
        updateRhythm()
    }

    // MARK: HRV (clean beats only, ≥ 80 % coverage, log-domain smoothing)

    private var hrvStateValue = "settling"
    private func updateHRV() {
        let win = beats.filter { $0.t >= now - 60 }
        let clean = win.filter(\.clean)
        let coverage = clean.reduce(0) { $0 + $1.rr } / 60000
        let raw = clean.map(\.rr)
        let irregular = afWindows.last.map { $0.af && $0.t > now - 120 } ?? false
        if irregular { hrvStateValue = "irregular"; return }
        if coverage < 0.8 || raw.count < 30 { hrvStateValue = noise.motionIndex > 0.4 ? "noisy" : "settling"; return }
        if currentActivity() == .active { hrvStateValue = "active" }
        let c = KYArtefacts.correct(raw)
        guard c.artefactPercent <= 5, let r = KYHRV.rmssd(c.nn), r > 0 else { hrvStateValue = "noisy"; return }
        let ln = log(r)
        // EMA in log domain; time constant ~30 s (updates arrive every frame ≈ 0.87 s)
        lnRmssdSmooth = lnRmssdSmooth.map { $0 + 0.03 * (ln - $0) } ?? ln
        if hrvStateValue != "active" { hrvStateValue = "ok" }
    }

    // MARK: resting HR: 10th percentile of clean minute medians (personal, adapts over days)

    private var minuteBucket: [Double] = []
    private var minuteStart: Double = 0
    private func updateRestingHr() {
        if let hr = kalman.hr, kalman.sd < 4, noise.last == .clean { minuteBucket.append(hr) }
        if now - minuteStart >= 60 {
            if minuteBucket.count >= 20 {
                let s = minuteBucket.sorted()
                hrMinutes.append(s[s.count / 2])
                if hrMinutes.count > 1440 { hrMinutes.removeFirst() }
                if hrMinutes.count >= 10 {
                    let sorted = hrMinutes.sorted()
                    let p10 = sorted[sorted.count / 10]
                    restingHr = 0.9 * restingHr + 0.1 * p10
                }
            }
            minuteBucket = []; minuteStart = now
        }
    }

    // MARK: activity (ECG-only: HR above personal resting + motion index)

    private func currentActivity() -> Activity {
        guard let hr = kalman.hr, kalman.sd < 8 else { return noise.motionIndex > 0.5 ? .moving : .unknown }
        if noise.motionIndex > 0.5 { return .moving }
        let reserve = (hr - restingHr) / max(20, 190 - restingHr)  // fraction of heart-rate reserve (age-agnostic default)
        if reserve > 0.35 { return .active }
        if reserve > 0.15 || noise.motionIndex > 0.2 { return .light }
        return .rest
    }

    // MARK: sleep (30-s epochs, logistic model [cal] on PhysioNet slpdb, hysteresis)

    public static var sleepCoef: [Double] = [0.0, -6.0, 1.2, -4.0, -0.8]  // bias, hrRel, lnRMSSD z, motion, hr sd

    private var epochBeats: [Double] = []
    private func updateEpoch() {
        if epochStart == 0 { epochStart = now }
        guard now - epochStart >= 30 else { return }
        let ep = beats.filter { $0.t >= epochStart && $0.t < now && $0.clean }.map(\.rr)
        let motion = Double(windowsBad.filter { $0.t >= epochStart && $0.c != .clean }.count) / 15
        epochStart = now
        guard ep.count >= 10 else {
            epochs.append((now, motion > 0.3 ? 0.05 : 0.5))
            if keepLogs { epochLog.append((now, [], -1)) }
            smoothSleep(); return
        }
        let f = KYInsight.epochFeatures(rr: ep, restingHr: restingHr, motion: motion)
        let c = KYInsight.sleepCoef
        let z = c[0] + c[1] * f[0] + c[2] * f[1] + c[3] * f[2] + c[4] * f[3]
        epochs.append((now, 1 / (1 + exp(-z))))
        if keepLogs { epochLog.append((now, f + [motion], 1 / (1 + exp(-z)))) }
        if epochs.count > 2880 { epochs.removeFirst() }
        smoothSleep()
    }

    /// Features: relative HR vs resting, ln RMSSD (centred), motion fraction, HR SD within the epoch (bpm).
    public static func epochFeatures(rr: [Double], restingHr: Double, motion: Double) -> [Double] {
        let hr = rr.map { 60000 / $0 }
        let mhr = hr.reduce(0, +) / Double(hr.count)
        let sd = (hr.map { ($0 - mhr) * ($0 - mhr) }.reduce(0, +) / Double(hr.count)).squareRoot()
        let c = KYArtefacts.correct(rr)
        let lnr = log(max(1, KYHRV.rmssd(c.nn) ?? 1)) - 3.4
        return [(mhr - restingHr) / restingHr, lnr, motion, sd / 10]
    }

    private func smoothSleep() {
        // asleep after 10 min (20 epochs) mostly sleep-like; awake after 2 consecutive clearly-awake epochs
        let last20 = epochs.suffix(20).map(\.p)
        let last2 = epochs.suffix(2).map(\.p)
        if last20.count == 20 && last20.filter({ $0 > 0.5 }).count >= 16 { sleepState = .asleep }
        else if last2.count == 2 && last2.allSatisfy({ $0 < 0.3 }) { sleepState = .awake }
        else if sleepState == .unknown && epochs.count >= 4 { sleepState = .awake }
    }

    // MARK: rhythm screening (raw RR, never artefact-corrected — correction would erase AF irregularity)

    public static var afThresholds = (nrmssd: 0.15, shannon: 0.80, tprLo: 0.40, tprHi: 1.40, cosen: -1.4)  // afdb train split after the COSEn sign fix (2026-10-13); test Se 91.7% Sp 99.4%, nsrdb FP 3.5% of windows

    private var lastRhythmCheck: Double = 0

    /// P-wave consistency in [-1, 1]: median correlation of each beat's pre-QRS segment (300–100 ms before R, linearly
    /// detrended) with the average of those segments over the last ≤ 40 clean beats. Sinus rhythm ≈ 0.6–0.9; AF (no
    /// organised atrial activity) ≈ 0–0.3. 0 when the averaged segment is flat (no P wave visible). nil if too few beats.
    /// Gate is off (nil): the KY-E-B1 chest lead shows P waves of only ~30 µV, too small to judge (2026-10-13). The score
    /// is still logged (afLog f[4]) for research with other leads.
    public static var pWaveMax: Double? = nil
    func pWaveScore() -> Double? {
        let a = Int(0.30 * fs), b = Int(0.10 * fs), len = a - b + 1
        let oldest = rawCount - 8192
        let idx = cleanBeatSamples.suffix(40).filter { $0 - a > oldest && $0 - b < rawCount }
        guard idx.count >= 15 else { return nil }
        var segs: [[Double]] = []
        for s in idx {
            var y = (0..<len).map { Double(raw[(s - a + $0) & 8191]) }
            let n = Double(len), mx = (n - 1) / 2, my = y.reduce(0, +) / n
            var sxy = 0.0, sxx = 0.0
            for k in 0..<len { sxy += (Double(k) - mx) * (y[k] - my); sxx += (Double(k) - mx) * (Double(k) - mx) }
            let slope = sxy / sxx
            for k in 0..<len { y[k] -= my + slope * (Double(k) - mx) }
            segs.append(y)
        }
        let tmpl = (0..<len).map { k in segs.reduce(0) { $0 + $1[k] } / Double(segs.count) }
        let tsd = (tmpl.map { $0 * $0 }.reduce(0, +) / Double(len)).squareRoot()
        guard tsd >= 8 else { return 0 }  // < 8 µV: no averaged P wave
        let corr = segs.map { y -> Double in
            let ysd = (y.map { $0 * $0 }.reduce(0, +) / Double(len)).squareRoot()
            return ysd > 0 ? zip(y, tmpl).map { $0 * $1 }.reduce(0, +) / Double(len) / (ysd * tsd) : 0
        }.sorted()
        return corr[corr.count / 2]
    }
    private func updateRhythm() {
        guard now - lastRhythmCheck >= 5 else { return }
        lastRhythmCheck = now
        let cleanWin = beats.filter { $0.t >= now - 60 && $0.clean }
        let rr = cleanWin.map(\.rr)
        // poor signal episodes
        let bad = windowsBad.filter { $0.t >= now - 30 }
        let badFrac = bad.isEmpty ? 0 : Double(bad.filter { $0.c != .clean }.count) / Double(bad.count)
        track("poor_signal", active: badFrac > 0.7, minDuration: 60, detail: ["fraction": badFrac])
        guard noise.last != .noContact else { return }

        // AF pattern on the last 64 clean beats
        if rr.count >= 40 {
            let w = Array(rr.suffix(64))
            let mean = w.reduce(0, +) / Double(w.count)
            let d = zip(w, w.dropFirst()).map { $1 - $0 }
            let nrmssd = (d.map { $0 * $0 }.reduce(0, +) / Double(d.count)).squareRoot() / mean
            let se = KYRhythmStats.shannonEntropy(w)
            let tpr = KYRhythmStats.turningPointRatio(w)
            let ce = KYRhythmStats.cosEn(Array(w.suffix(32))) ?? -9
            let th = KYInsight.afThresholds
            let ps = pWaveScore()
            // optional P-wave gate (off for this band, see pWaveMax)
            let af = nrmssd > th.nrmssd && se > th.shannon && tpr > th.tprLo && tpr < th.tprHi && ce > th.cosen
                && (KYInsight.pWaveMax.map { pm in ps.map { $0 < pm } ?? true } ?? true)
            afWindows.append((now, af))
            if keepLogs { afLog.append((now, [nrmssd, se, tpr, ce, ps ?? -1], af)) }
            afWindows.removeAll { $0.t < now - 3600 }
            track("af_pattern", active: af, minDuration: 30, detail: ["nrmssd": nrmssd, "shannon": se, "tpr": tpr, "cosen": ce, "pwave": ps ?? -1])
        }
        // pauses: an RR > 2.0 s between two clean beats
        if let p = cleanWin.last(where: { $0.rr > 2000 && $0.t > now - 5 }) {
            emitPoint("pause", at: p.t, detail: ["rr_ms": p.rr])
        }
        // early beats: Lipponen–Tarvainen ectopic classification on the raw clean series (last 60 s)
        if rr.count >= 20 {
            let c = KYArtefacts.correct(rr)
            earlyPerMin = Double(c.ectopic) * 60 / max(1, rr.reduce(0, +) / 1000)
            // bigeminy/trigeminy: alternating short-long patterns
            let pattern = KYInsight.ectopyPattern(Array(rr.suffix(24)))
            track("bigeminy", active: pattern == 2, minDuration: 15, detail: [:])
            track("trigeminy", active: pattern == 3, minDuration: 15, detail: [:])
            track("early_beats", active: earlyPerMin >= 6, minDuration: 60, detail: ["per_min": earlyPerMin])
        }
        // context-aware rate flags (awake thresholds; lower limit relaxed during sleep)
        if let hr = kalman.hr, kalman.sd < 6 {
            let asleep = sleepState == .asleep
            track("bradycardia", active: hr < (asleep ? 35 : 40), minDuration: 30, detail: ["hr": hr])
            track("tachycardia_rest", active: hr > 100 && currentActivity() == .rest && !asleep, minDuration: 60, detail: ["hr": hr])
            track("very_high_hr", active: hr > 150 && currentActivity() != .active, minDuration: 30, detail: ["hr": hr])
        }
    }

    private var earlyPerMin = 0.0

    /// 2 = bigeminy (every 2nd beat early), 3 = trigeminy, 0 = none. Needs ≥ 4 cycles.
    public static func ectopyPattern(_ rr: [Double]) -> Int {
        guard rr.count >= 12 else { return 0 }
        let med = rr.sorted()[rr.count / 2]
        let short = rr.map { $0 < 0.85 * med }
        for k in [2, 3] {
            var cycles = 0, best = 0
            var i = 0
            while i + k <= short.count {
                let block = short[i..<(i + k)]
                if block.filter({ $0 }).count == 1 { cycles += 1; best = max(best, cycles); i += k } else { cycles = 0; i += 1 }
            }
            if best >= 4 { return k }
        }
        return 0
    }

    private func track(_ type: String, active: Bool, minDuration: Double, detail: [String: Double]) {
        if active {
            if var e = open[type] { e.end = now; e.detail = detail; open[type] = e }
            else { open[type] = Event(type: type, start: now, end: now, detail: detail) }
            if let e = open[type], e.end - e.start >= minDuration, !events.contains(where: { $0.type == type && $0.start == e.start }) {
                events.append(e); onEvent?(e)
            }
        } else if let e = open[type] {
            open[type] = nil
            if let i = events.firstIndex(where: { $0.type == type && $0.start == e.start }) { events[i].end = e.end; onEvent?(events[i]) }
        }
        if events.count > 500 { events.removeFirst(events.count - 500) }
    }

    private func emitPoint(_ type: String, at t: Double, detail: [String: Double]) {
        guard !events.contains(where: { $0.type == type && abs($0.start - t) < 1 }) else { return }
        let e = Event(type: type, start: t, end: t, detail: detail)
        events.append(e); onEvent?(e)
    }

    // MARK: state

    public var currentSleep: Sleep { sleepState }

    public var state: State {
        let hr = kalman.hr
        let stale = now - kalman.lastUpdate > 15
        let sd = kalman.sd
        let conf = hr == nil || stale ? "none" : sd < 2.5 ? "high" : sd < 5 ? "medium" : "low"
        let r = lnRmssdSmooth.map { exp($0) }
        let afRecent = afWindows.filter { $0.t >= now - 3600 }
        return State(hr: stale ? nil : hr, hrSd: stale ? nil : sd, hrConfidence: conf,
                     lnRmssd: lnRmssdSmooth, rmssd: hrvStateValue == "ok" || hrvStateValue == "active" ? r : nil,
                     rmssd5: rmssd5(), hrvState: hrvStateValue, activity: currentActivity(), sleep: sleepState,
                     motionIndex: noise.motionIndex, windowClass: noise.last.rawValue, restingHr: restingHr,
                     earlyBeatsPerMin: earlyPerMin,
                     afBurden60: afRecent.isEmpty ? 0 : Double(afRecent.filter(\.af).count) / Double(afRecent.count),
                     openEvents: open.values.filter { $0.end - $0.start >= 15 }.map(\.type))
    }

    // 5-min RMSSD changes slowly; recompute at most every 10 s (it was recomputed on every state read)
    private var rmssd5Cache: (at: Double, v: Double?) = (-1e9, nil)
    private func rmssd5() -> Double? {
        if now - rmssd5Cache.at < 10 { return rmssd5Cache.v }
        let v = computeRmssd5(); rmssd5Cache = (now, v); return v
    }
    private func computeRmssd5() -> Double? {
        let w = beats.filter { $0.t >= now - 300 && $0.clean }
        guard w.reduce(0, { $0 + $1.rr }) / 300_000 >= 0.8 else { return nil }
        let c = KYArtefacts.correct(w.map(\.rr))
        return c.artefactPercent <= 5 ? KYHRV.rmssd(c.nn) : nil
    }

    public func setRestingHr(_ v: Double) { if v > 30 && v < 120 { restingHr = v } }
}
