import Foundation

// MARK: - Filters

/// Second-order IIR section (RBJ cookbook, Butterworth Q = 1/√2), direct form I.
struct Biquad {
    private var b0 = 1.0, b1 = 0.0, b2 = 0.0, a1 = 0.0, a2 = 0.0
    private var x1 = 0.0, x2 = 0.0, y1 = 0.0, y2 = 0.0

    static func lowpass(_ fc: Double, fs: Double) -> Biquad { make(fc, fs, high: false) }
    static func highpass(_ fc: Double, fs: Double) -> Biquad { make(fc, fs, high: true) }

    private static func make(_ fc: Double, _ fs: Double, high: Bool) -> Biquad {
        let w = 2 * Double.pi * min(fc, 0.49 * fs) / fs, q = 1 / 2.0.squareRoot()
        let alpha = sin(w) / (2 * q), c = cos(w), a0 = 1 + alpha
        var f = Biquad()
        if high {
            f.b0 = (1 + c) / 2 / a0; f.b1 = -(1 + c) / a0; f.b2 = (1 + c) / 2 / a0
        } else {
            f.b0 = (1 - c) / 2 / a0; f.b1 = (1 - c) / a0; f.b2 = (1 - c) / 2 / a0  // bilinear LP: double zero at Nyquist
        }
        f.a1 = -2 * c / a0; f.a2 = (1 - alpha) / a0
        return f
    }

    mutating func step(_ x: Double) -> Double {
        let y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2 = x1; x1 = x; y2 = y1; y1 = y
        return y
    }
}

/// Running median over an odd window (centred output is delayed by window/2 samples).
struct RunningMedian {
    let size: Int
    private var buf: [Double] = []
    init(_ size: Int) { self.size = size | 1 }
    mutating func step(_ x: Double) -> Double {
        buf.append(x); if buf.count > size { buf.removeFirst() }
        let s = buf.sorted()
        return s[s.count / 2]
    }
}

/// Fixed-capacity ring indexed by absolute sample number.
struct SampleRing {
    private var data: [Double]
    private(set) var end = 0   // absolute index one past the newest sample
    init(capacity: Int) { data = Array(repeating: 0, count: capacity) }
    var capacity: Int { data.count }
    mutating func append(_ v: Double) { data[end % data.count] = v; end += 1 }
    func has(_ i: Int) -> Bool { i >= 0 && i < end && i >= end - data.count }
    subscript(i: Int) -> Double { data[((i % data.count) + data.count) % data.count] }
}

// MARK: - Analyzer

/// Real-time single-lead ECG analysis for wearable data (designed for 100 Hz; works at 125–500 Hz).
///
/// - Display: baseline removed by 200 ms + 600 ms median filters (de Chazal 2004); 40 Hz Butterworth low-pass (AHA monitoring band,
///   and a spectral zero at Nyquist that cancels 50 Hz mains when fs = 100 Hz).
/// - QRS detection: Pan–Tompkins (5–15 Hz band-pass, derivative, squaring, 150 ms integration, adaptive SPK/NPK thresholds,
///   200 ms refractory, T-wave discrimination by slope, search-back with half threshold after 1.66 × mean RR).
/// - Fiducial point: R peak (polarity learned from the first beats) on the display signal, parabolic interpolation
///   (Task Force 1996: ≥ 100 Hz acceptable with parabolic interpolation for time-domain HRV).
/// - Signal quality (Clifford/Behar SQIs on 10 s): bSQI vs an independent Elgendi detector, kSQI (kurtosis), pSQI (5–15 / 5–40 Hz
///   power), basSQI (1 − power < 1 Hz / power < 40 Hz).
/// - HRV: Lipponen & Tarvainen 2019 artefact detection/correction, then Task Force time-domain metrics. No spectral HRV at 100 Hz.
public final class KYAnalyzer {
    public enum Quality: String { case noContact = "no_contact", poor, acceptable, good, warmingUp = "warming_up" }

    public struct Beat: Equatable {
        public let sample: Double     // absolute sample index (sub-sample precision)
        public let rrMs: Double?
        public let amplitude: Double  // µV on the display signal
    }

    public struct Metrics: Equatable {
        public var heartRate: Double?
        public var meanNN60: Double?
        public var sdnn60: Double?
        public var rmssd60: Double?
        public var pnn50_60: Double?
        public var sdnn300: Double?
        public var rmssd300: Double?
        public var artefactPercent60: Double?
        public var irregularBeats60: Int
        public var hrvReliable: Bool
        public var quality: Quality
        public var sqi: [String: Double]
        public var beatCount: Int
    }

    public let fs: Double
    public var leadOn = true { didSet { if !leadOn { quality = .noContact } } }

    // display path
    private var med1: RunningMedian, med2: RunningMedian
    private var rawRing: SampleRing, displayRing: SampleRing
    private var displayLP: Biquad
    private let baselineDelay: Int
    // Pan–Tompkins path
    private var ptHP: Biquad, ptLP: Biquad
    private var bpPrev: [Double] = [0, 0, 0, 0]
    private var mwiBuf: [Double] = []
    private var mwiSum = 0.0
    private var mwiRing: SampleRing, slopeRing: SampleRing
    private var m1 = 0.0, m2 = 0.0
    private var spk = 0.0, npk = 0.0, warm = 0
    private var lastQRSIndex = -1_000_000
    private var lastQRSSlope = 0.0
    private var pending: [(index: Int, slope: Double)] = []
    // Elgendi path (bSQI)
    private var elHP: Biquad, elLP: Biquad
    private var elSq: SampleRing
    private var elShort = 0.0, elLong = 0.0, elMeanAcc = 0.0
    private var elInBlock = false, elBlockStart = 0
    private var elBeats: [Int] = []
    // quality paths
    private var qrsBandHP: Biquad, qrsBandLP: Biquad, wideHP: Biquad, wideLP: Biquad, dcHP: Biquad, baseLP: Biquad, allLP: Biquad
    private var qrsPow: SampleRing, widePow: SampleRing, basePow: SampleRing, allPow: SampleRing

    private(set) var n = 0
    private var beats: [Beat] = []
    private var amplitudes: [Double] = []
    private var quality: Quality = .warmingUp
    private var sqi: [String: Double] = [:]
    private var lastSQIAt = 0

    public init(sampleRate fs: Double = 100) {
        self.fs = fs
        med1 = RunningMedian(Int(0.2 * fs)); med2 = RunningMedian(Int(0.6 * fs))
        baselineDelay = (Int(0.2 * fs) | 1) / 2 + (Int(0.6 * fs) | 1) / 2
        let cap = Int(12 * fs)
        rawRing = SampleRing(capacity: cap); displayRing = SampleRing(capacity: cap)
        mwiRing = SampleRing(capacity: cap); slopeRing = SampleRing(capacity: cap)
        displayLP = .lowpass(40, fs: fs)
        ptHP = .highpass(5, fs: fs); ptLP = .lowpass(15, fs: fs)
        elHP = .highpass(8, fs: fs); elLP = .lowpass(20, fs: fs)
        elSq = SampleRing(capacity: cap)
        qrsBandHP = .highpass(5, fs: fs); qrsBandLP = .lowpass(15, fs: fs)
        wideHP = .highpass(5, fs: fs); wideLP = .lowpass(40, fs: fs)
        dcHP = .highpass(0.05, fs: fs); baseLP = .lowpass(1, fs: fs); allLP = .lowpass(40, fs: fs)
        qrsPow = SampleRing(capacity: Int(10 * fs)); widePow = SampleRing(capacity: Int(10 * fs))
        basePow = SampleRing(capacity: Int(10 * fs)); allPow = SampleRing(capacity: Int(10 * fs))
    }

    /// Latest signal-quality class (cheap; `metrics` recomputes HRV).
    public var currentQuality: Quality { quality }

    /// Display-signal latency relative to the input, in samples (baseline median filters).
    public var displayDelay: Int { baselineDelay }

    // MARK: processing

    public struct Output {
        public var display: [Double] = []   // filtered samples, aligned to input samples (delayed by displayDelay)
        public var beats: [Beat] = []
    }

    public func process(_ samples: [Int16]) -> Output {
        var out = Output()
        for s in samples {
            let x = Double(s)
            rawRing.append(x)
            // display: x[n - delay] - baseline(n)
            let b = med2.step(med1.step(x))
            let idx = n - baselineDelay
            let clean = idx >= 0 ? displayLP.step(rawRing[idx] - b) : 0
            if idx >= 0 { displayRing.append(clean); out.display.append(clean) }
            stepPanTompkins(x)
            stepElgendi(x)
            stepQuality(x)
            n += 1
            out.beats += resolvePending()
        }
        if n - lastSQIAt >= Int(fs) { updateSQI(); lastSQIAt = n }
        return out
    }

    /// Detector tuning (validated on PhysioNet; see docs/devices/KY_E_B1_ALGORITHMS.md).
    public struct Tuning {
        public var thresholdCoef = 0.2        // TH = noise + c · (QRS − noise), medians of last 8 peaks (Hamilton–Tompkins form; c tuned on MIT-BIH/AFDB train split)
        public var confirmDelay = 0.05        // s: a peak is final when nothing larger follows within this window (tuned)
        public var searchBackFactor = 1.66    // × median RR
        public var tWaveWindow = 0.36         // s
        public var tWaveSlope = 0.5
        public init() {}
    }
    public static var tuning = Tuning()

    private var candV = 0.0, candI = -1, lastMwi = 0.0
    private var qrsPeaks: [Double] = [], noisePeaks: [Double] = []
    private var lastQRSAmp = 0.0
    private var lastBeatN = 200  // first check 3 s after the 2-s start-up learn (fs = 100; reset() sets it from fs)
    /// Times the detector re-learned its levels after 3 s without a beat (diagnostic).
    public private(set) var relearns = 0

    private func median(_ v: [Double]) -> Double { let s = v.sorted(); return s.isEmpty ? 0 : s[s.count / 2] }

    private var detThreshold: Double {
        let q = median(qrsPeaks), nz = median(noisePeaks)
        return nz + Self.tuning.thresholdCoef * (q - nz)
    }

    private func stepPanTompkins(_ x: Double) {
        let bp = ptLP.step(ptHP.step(x))
        // five-point derivative (Pan & Tompkins 1985)
        let d = (2 * bp + bpPrev[0] - bpPrev[2] - 2 * bpPrev[3]) / 8
        bpPrev = [bp] + bpPrev.prefix(3)
        let sq = d * d
        let w = max(3, Int(0.15 * fs))
        mwiBuf.append(sq); mwiSum += sq
        if mwiBuf.count > w { mwiSum -= mwiBuf.removeFirst() }
        let mwi = mwiSum / Double(mwiBuf.count)
        mwiRing.append(mwi); slopeRing.append(abs(d))
        warm += 1
        if warm < Int(2 * fs) {
            // learn: QRS level ≈ max over 2 s, noise ≈ its mean
            spk = max(spk, mwi); npk += mwi / (2 * fs)
            if warm == Int(2 * fs) - 1 { qrsPeaks = [spk]; noisePeaks = [npk] }
            return
        }
        // delayed peak confirmation: the running maximum becomes a peak once nothing larger arrives for `confirmDelay`
        // only true local maxima (rising into the sample) can become candidates, so the decaying tail after a beat
        // is never mistaken for a noise peak (which would inflate the threshold)
        if mwi > candV && mwi > lastMwi { candV = mwi; candI = n }
        if candI >= 0 && n - candI >= Int(Self.tuning.confirmDelay * fs) {
            classifyPeak(candI, candV)
            candV = 0; candI = -1
        }
        lastMwi = mwi
        // recovery: a large artefact can lift the noise level to QRS size, after which every real beat is filed as noise
        // and the levels never come down (night of 2026-10-13: detector silent from 01:31 to morning). No accepted beat
        // for 3 s → re-learn both levels from the next 2 s, as at start-up.
        if n - lastBeatN > Int(3 * fs) {
            warm = 0; spk = 0; npk = 0; candV = 0; candI = -1
            lastBeatN = n + Int(2 * fs); relearns += 1  // 3 s of detection after the 2-s re-learn
            return
        }
        // search-back: no beat for 1.66 × median RR → largest local MWI maximum since the last beat above half threshold
        if let mean = medianRRSamples(), lastQRSIndex > 0, Double(n - lastQRSIndex) > Self.tuning.searchBackFactor * mean {
            var best = -1; var bestV = 0.0
            let from = lastQRSIndex + Int(0.2 * fs), to = n - Int(0.2 * fs)
            if from < to {
                for k in from..<to where mwiRing.has(k) && mwiRing[k] > bestV && mwiRing.has(k - 1) && mwiRing.has(k + 1)
                    && mwiRing[k] >= mwiRing[k - 1] && mwiRing[k] >= mwiRing[k + 1] { best = k; bestV = mwiRing[k] }
            }
            if best > 0 && bestV > 0.5 * detThreshold {
                push(&qrsPeaks, bestV)
                accept(best, peak: nil, slope: maxSlope(around: best))
            } else {
                lastQRSIndex = n - Int(0.2 * fs)  // nothing found; wait before searching again
            }
        }
    }

    private func push(_ a: inout [Double], _ v: Double) { a.append(v); if a.count > 8 { a.removeFirst() } }

    private func classifyPeak(_ i: Int, _ v: Double) {
        let thr = detThreshold
        guard v > thr, i - lastQRSIndex > Int(0.2 * fs) else { push(&noisePeaks, v); return }
        let slope = maxSlope(around: i)
        let since = Double(i - lastQRSIndex) / fs
        if since < Self.tuning.tWaveWindow && slope < Self.tuning.tWaveSlope * lastQRSSlope {
            push(&noisePeaks, v)  // T wave
            return
        }
        push(&qrsPeaks, min(v, 4 * max(median(qrsPeaks), 1e-9)))  // cap so one giant beat can't hide the next ones
        accept(i, peak: nil, slope: slope)
    }

    private func medianRRSamples() -> Double? {
        let rr = beats.suffix(8).compactMap(\.rrMs)
        return rr.count >= 4 ? rr.sorted()[rr.count / 2] / 1000 * fs : nil
    }

    private func accept(_ i: Int, peak: Double?, slope: Double) {
        if let p = peak { spk = 0.125 * p + 0.875 * spk }
        lastQRSIndex = i
        lastBeatN = i
        lastQRSSlope = slope
        pending.append((i, slope))
    }

    private func maxSlope(around i: Int) -> Double {
        var m = 0.0
        for k in (i - Int(0.15 * fs))...i where slopeRing.has(k) { m = max(m, slopeRing[k]) }
        return m
    }

    private func meanRRSamples() -> Double? {
        let rr = beats.suffix(8).compactMap(\.rrMs)
        return rr.count >= 4 ? rr.reduce(0, +) / Double(rr.count) / 1000 * fs : nil
    }

    /// Locate the R peak once the delayed display signal covers the QRS window.
    private func resolvePending() -> [Beat] {
        var out: [Beat] = []
        let half = Int(0.10 * fs)
        // QRS centre ≈ integrator peak − 75 ms (half the 150 ms window) − band-pass group delay (~20 ms)
        let shift = Int(0.095 * fs)
        while let p = pending.first, displayRing.end - 1 >= p.index - shift + half {
            pending.removeFirst()
            // display ring index k holds input sample k (ring is filled from input index 0 onwards)
            let centre = p.index - shift
            let lo = centre - half, hi = centre + half
            let sign = polarity
            var j = -1; var best = -Double.infinity
            for k in lo...hi where displayRing.has(k) {
                let v = sign == 0 ? abs(displayRing[k]) : sign * displayRing[k]
                if v > best { best = v; j = k }
            }
            guard j >= 0 else { continue }
            var offset = 0.0
            if displayRing.has(j - 1) && displayRing.has(j + 1) {
                let f = { (k: Int) in sign == 0 ? abs(self.displayRing[k]) : sign * self.displayRing[k] }
                let a = f(j - 1), b = f(j), c = f(j + 1), den = a - 2 * b + c
                if den != 0 { offset = max(-0.5, min(0.5, 0.5 * (a - c) / den)) }
            }
            let sample = Double(j) + offset
            if let last = beats.last, sample - last.sample < 0.2 * fs { continue }  // duplicate (search-back overlap)
            let rr = beats.last.map { (sample - $0.sample) / fs * 1000 }
            let beat = Beat(sample: sample, rrMs: rr, amplitude: displayRing[j])
            beats.append(beat); if beats.count > 3000 { beats.removeFirst(beats.count - 3000) }
            amplitudes.append(displayRing[j]); if amplitudes.count > 15 { amplitudes.removeFirst() }
            out.append(beat)
        }
        return out
    }

    private var polarity: Double {
        guard amplitudes.count >= 5 else { return 0 }
        let s = amplitudes.sorted()
        return s[s.count / 2] >= 0 ? 1 : -1
    }

    /// Elgendi 2013: 8–20 Hz band-pass, squaring, MA 97 ms vs MA 611 ms + offset, blocks ≥ QRS width → beat.
    private func stepElgendi(_ x: Double) {
        let y = elLP.step(elHP.step(x))
        let sq = y * y
        elSq.append(sq)
        let ws = Double(max(3, Int(0.097 * fs))), wl = Double(max(9, Int(0.611 * fs)))
        elShort += (sq - elShort) * 2 / (ws + 1)
        elLong += (sq - elLong) * 2 / (wl + 1)
        elMeanAcc += (sq - elMeanAcc) / (10 * fs)
        let thr = elLong + 0.08 * elMeanAcc
        if elShort > thr {
            if !elInBlock { elInBlock = true; elBlockStart = n }
        } else if elInBlock {
            elInBlock = false
            if n - elBlockStart >= Int(0.08 * fs) {
                var j = elBlockStart; var best = 0.0
                for k in elBlockStart..<n where elSq.has(k) && elSq[k] > best { best = elSq[k]; j = k }
                elBeats.append(j); if elBeats.count > 200 { elBeats.removeFirst() }
            }
        }
    }

    private func stepQuality(_ x: Double) {
        let q = qrsBandLP.step(qrsBandHP.step(x)), w = wideLP.step(wideHP.step(x))
        let z = dcHP.step(x)  // remove the electrode DC offset before measuring baseline power
        let b = baseLP.step(z), a = allLP.step(z)
        qrsPow.append(q * q); widePow.append(w * w); basePow.append(b * b); allPow.append(a * a)
    }

    private func updateSQI() {
        guard leadOn else { quality = .noContact; return }
        guard n > Int(10 * fs) else { quality = .warmingUp; return }
        let w = Int(10 * fs)
        func mean(_ r: SampleRing) -> Double { var s = 0.0; var c = 0; for k in (r.end - w)..<r.end where r.has(k) { s += r[k]; c += 1 }; return c > 0 ? s / Double(c) : 0 }
        // kSQI on the display signal
        var vals: [Double] = []
        for k in (displayRing.end - w)..<displayRing.end where displayRing.has(k) { vals.append(displayRing[k]) }
        var ksqi = 0.0
        if vals.count > 10 {
            let m = vals.reduce(0, +) / Double(vals.count)
            let v2 = vals.map { ($0 - m) * ($0 - m) }.reduce(0, +) / Double(vals.count)
            let v4 = vals.map { pow($0 - m, 4) }.reduce(0, +) / Double(vals.count)
            ksqi = v2 > 0 ? v4 / (v2 * v2) : 0
        }
        let psqi = mean(widePow) > 0 ? mean(qrsPow) / mean(widePow) : 0
        let bas = mean(basePow), all = mean(allPow)
        let bassqi = all > 0 ? max(0, 1 - bas / all) : 0
        // bSQI: agreement between Pan–Tompkins and Elgendi beats in the last 10 s (match within 150 ms)
        let from = Double(n - w - Int(fs))
        let pt = beats.filter { $0.sample >= from }.map(\.sample)
        let el = elBeats.filter { Double($0) >= from }.map(Double.init)
        let tol = 0.15 * fs
        let matched = pt.filter { p in el.contains { abs($0 - p) <= tol } }.count
        let denom = pt.count + el.count - matched
        let bsqi = denom > 0 ? Double(matched) / Double(denom) : 0
        sqi = ["bSQI": bsqi, "kSQI": ksqi, "pSQI": psqi, "basSQI": bassqi]
        if pt.count < 3 { quality = .poor }
        // thresholds after Clifford/Behar; basSQI 0.9 because the filter-bank estimate reads ~0.01–0.02 below the spectral one
        else if bsqi >= 0.9 && ksqi > 5 && bassqi > 0.9 && (0.4...0.9).contains(psqi) { quality = .good }
        else if bsqi >= 0.8 && ksqi > 3 { quality = .acceptable }
        else { quality = .poor }
    }

    // MARK: HRV

    public var metrics: Metrics {
        let nowSample = Double(n - baselineDelay)
        let window60 = beats.filter { $0.sample >= nowSample - 60 * fs }
        let window300 = beats.filter { $0.sample >= nowSample - 300 * fs }
        let c60 = KYArtefacts.correct(window60.compactMap(\.rrMs))
        let c300 = KYArtefacts.correct(window300.compactMap(\.rrMs))
        let reliable = (quality == .good || quality == .acceptable) && c60.nn.count >= 30 && c60.artefactPercent <= 5
        // Heart rate: mean of the NN intervals in the last 10 s — spans ~2 breaths, so respiratory sinus arrhythmia
        // (HR rising on inhalation, falling on exhalation) doesn't make the number swing beat to beat.
        let recent = KYArtefacts.correct(beats.filter { $0.sample >= nowSample - 10 * fs }.compactMap(\.rrMs)).nn
        let hr = recent.count >= 3 && quality != .noContact ? 60000 / (recent.reduce(0, +) / Double(recent.count)) : nil
        return Metrics(heartRate: hr,
                       meanNN60: c60.nn.isEmpty ? nil : c60.nn.reduce(0, +) / Double(c60.nn.count),
                       sdnn60: reliable ? KYHRV.sdnn(c60.nn) : nil,
                       rmssd60: reliable ? KYHRV.rmssd(c60.nn) : nil,
                       pnn50_60: reliable ? KYHRV.pnn50(c60.nn) : nil,
                       sdnn300: c300.nn.count >= 150 && c300.artefactPercent <= 5 ? KYHRV.sdnn(c300.nn) : nil,
                       rmssd300: c300.nn.count >= 150 && c300.artefactPercent <= 5 ? KYHRV.rmssd(c300.nn) : nil,
                       artefactPercent60: c60.raw > 0 ? c60.artefactPercent : nil,
                       irregularBeats60: c60.ectopic,
                       hrvReliable: reliable, quality: quality, sqi: sqi, beatCount: beats.count)
    }

    public func reset() {
        let fresh = KYAnalyzer(sampleRate: fs)
        med1 = fresh.med1; med2 = fresh.med2; rawRing = fresh.rawRing; displayRing = fresh.displayRing; displayLP = fresh.displayLP
        ptHP = fresh.ptHP; ptLP = fresh.ptLP; bpPrev = [0, 0, 0, 0]; mwiBuf = []; mwiSum = 0; mwiRing = fresh.mwiRing; slopeRing = fresh.slopeRing
        m1 = 0; m2 = 0; spk = 0; npk = 0; warm = 0; lastBeatN = Int(2 * fs); relearns = 0; lastQRSIndex = -1_000_000; lastQRSSlope = 0; pending = []
        candV = 0; candI = -1; qrsPeaks = []; noisePeaks = []
        elHP = fresh.elHP; elLP = fresh.elLP; elSq = fresh.elSq; elShort = 0; elLong = 0; elMeanAcc = 0; elInBlock = false; elBeats = []
        qrsBandHP = fresh.qrsBandHP; qrsBandLP = fresh.qrsBandLP; wideHP = fresh.wideHP; wideLP = fresh.wideLP; dcHP = fresh.dcHP; baseLP = fresh.baseLP; allLP = fresh.allLP
        qrsPow = fresh.qrsPow; widePow = fresh.widePow; basePow = fresh.basePow; allPow = fresh.allPow
        n = 0; beats = []; amplitudes = []; quality = .warmingUp; sqi = [:]; lastSQIAt = 0
    }
}

// MARK: - HRV

public enum KYHRV {
    public static func rmssd(_ nn: [Double]) -> Double? {
        guard nn.count >= 3 else { return nil }
        let d = zip(nn, nn.dropFirst()).map { $1 - $0 }
        return (d.map { $0 * $0 }.reduce(0, +) / Double(d.count)).squareRoot()
    }
    public static func sdnn(_ nn: [Double]) -> Double? {
        guard nn.count >= 3 else { return nil }
        let m = nn.reduce(0, +) / Double(nn.count)
        return (nn.map { ($0 - m) * ($0 - m) }.reduce(0, +) / Double(nn.count - 1)).squareRoot()
    }
    public static func pnn50(_ nn: [Double]) -> Double? {
        guard nn.count >= 3 else { return nil }
        let d = zip(nn, nn.dropFirst()).map { abs($1 - $0) }
        return 100 * Double(d.filter { $0 > 50 }.count) / Double(d.count)
    }
}

/// RR artefact detection and correction after Lipponen & Tarvainen (2019), J Med Eng Technol 43:173–181.
public enum KYArtefacts {
    public struct Result { public var nn: [Double]; public var raw: Int; public var ectopic: Int; public var corrected: Int
        public var artefactPercent: Double { raw > 0 ? 100 * Double(corrected) / Double(raw) : 0 } }

    static func quartileDeviation(_ v: [Double]) -> Double {
        guard v.count >= 4 else { return v.map(abs).max() ?? 0 }
        let s = v.sorted()
        return (s[(3 * s.count) / 4] - s[s.count / 4]) / 2
    }

    static func median(_ v: ArraySlice<Double>) -> Double { let s = v.sorted(); return s.isEmpty ? 0 : s[s.count / 2] }

    public static func correct(_ rrIn: [Double], alpha: Double = 5.2, c1: Double = 0.13, c2: Double = 0.17) -> Result {
        // physiological gate first: anything outside 250–2500 ms is an artefact
        let rr = rrIn
        let n = rr.count
        guard n >= 6 else { return Result(nn: rr.filter { $0 >= 250 && $0 <= 2500 }, raw: n, ectopic: 0, corrected: rr.filter { $0 < 250 || $0 > 2500 }.count) }
        var drr = [0.0] + zip(rr, rr.dropFirst()).map { $1 - $0 }
        drr[0] = drr.count > 1 ? drr[1] : 0
        func local(_ v: [Double], _ i: Int, _ half: Int) -> [Double] { Array(v[max(0, i - half)...min(v.count - 1, i + half)]) }
        var th1 = [Double](repeating: 0, count: n), th2 = th1, mrr = th1, medRR = th1
        for i in 0..<n {
            th1[i] = max(1e-6, alpha * quartileDeviation(local(drr, i, 45)))
            medRR[i] = median(rr[max(0, i - 5)...min(n - 1, i + 5)])
            mrr[i] = rr[i] - medRR[i]
        }
        for i in 0..<n { th2[i] = max(1e-6, alpha * quartileDeviation(local(mrr, i, 45))) }
        let drrs = (0..<n).map { drr[$0] / th1[$0] }
        let mrrs = (0..<n).map { mrr[$0] < 0 ? 2 * mrr[$0] / th2[$0] : mrr[$0] / th2[$0] }
        enum Kind { case ok, ectopic, longShort, missed, extra }
        var kind = [Kind](repeating: .ok, count: n)
        var i = 0
        while i < n - 2 {
            if abs(drrs[i]) <= 1 { i += 1; continue }
            let s11 = drrs[i]
            let s12 = s11 > 0 ? max(drrs[max(0, i - 1)], drrs[i + 1]) : min(drrs[max(0, i - 1)], drrs[i + 1])
            let s22 = s11 >= 0 ? min(drrs[i + 1], drrs[i + 2]) : max(drrs[i + 1], drrs[i + 2])
            if (s11 > 1 && s12 < -c1 * s11 - c2) || (s11 < -1 && s12 > -c1 * s11 + c2) {
                kind[i] = .ectopic; i += 1; continue
            }
            if abs(mrrs[i]) > 3 || (s11 > 1 && s22 < -1) || (s11 < -1 && s22 > 1) {
                // tolerance: the paper's Th2, widened to 10 % of the local median so strong respiratory arrhythmia doesn't
                // turn a clean missed/extra detection into an interpolated beat
                let tol = max(th2[i], 0.1 * medRR[i])
                if abs(rr[i] / 2 - medRR[i]) < tol { kind[i] = .missed; i += 2; continue }
                if i + 1 < n && abs(rr[i] + rr[i + 1] - medRR[i]) < tol { kind[i] = .extra; i += 2; continue }
                kind[i] = .longShort
            }
            i += 1
        }
        for k in 0..<n where rr[k] < 250 || rr[k] > 2500 { kind[k] = kind[k] == .ok ? .longShort : kind[k] }
        var nn: [Double] = []
        var corrected = 0, ectopic = 0
        var k = 0
        while k < n {
            switch kind[k] {
            case .ok: nn.append(rr[k])
            case .missed: nn += [rr[k] / 2, rr[k] / 2]; corrected += 1
            case .extra where k + 1 < n: nn.append(rr[k] + rr[k + 1]); corrected += 1; k += 1
            case .ectopic, .longShort, .extra:
                if kind[k] == .ectopic { ectopic += 1 }
                corrected += 1
                // linear interpolation between the nearest good neighbours
                let prev = nn.last
                let next = (k + 1..<n).first { kind[$0] == .ok }.map { rr[$0] }
                if let p = prev, let q = next { nn.append((p + q) / 2) } else if let v = prev ?? next { nn.append(v) }
            }
            k += 1
        }
        return Result(nn: nn, raw: n, ectopic: ectopic, corrected: corrected)
    }
}
