import Foundation

/// Real-time R-peak detector and HRV for single-lead ECG (Pan–Tompkins style, tuned for 100 Hz).
///
/// Pipeline per sample: baseline removal (moving average 0.6 s) → derivative → squaring → moving-window integration (150 ms)
/// → adaptive threshold (signal/noise peak estimates) with a 250 ms refractory period → R peak located as the largest |amplitude|
/// within ±100 ms of the integrator peak, refined to sub-sample time by parabolic interpolation (≈ 2 ms timing at 100 Hz).
/// RR intervals outside 300–2000 ms or > 30 % from the running median are flagged as artefacts and excluded from HRV.
public final class KYBeatDetector {
    public struct Beat: Equatable {
        public let time: Double      // seconds since the detector started
        public let rrMs: Double?     // interval from the previous beat
        public let valid: Bool       // usable for HRV
        public let amplitude: Double // µV, baseline-corrected
    }

    public struct Metrics: Equatable {
        public var heartRate: Double?       // bpm, last 8 valid beats
        public var rmssd60: Double?         // ms, valid successive differences in the last 60 s
        public var rmssd300: Double?        // ms, last 5 min
        public var sdnn60: Double?          // ms
        public var pnn50: Double?           // %, last 60 s
        public var quality: Double          // 0–1: valid beats ÷ beats in the last 30 s
        public var beatCount: Int
    }

    public let fs: Double
    private var n = 0                         // samples processed
    private var raw: [Double] = []            // recent raw samples (ring, 3 s)
    private var maWindow: [Double] = []
    private var maSum = 0.0
    private var hp: [Double] = []             // baseline-removed signal (ring, 3 s)
    private var prevHp = 0.0
    private var sq: [Double] = []
    private var sqSum = 0.0
    private var mwiPrev = 0.0, mwiPrev2 = 0.0
    private var spk = 0.0, npk = 0.0
    private var lastBeatSample = -100_000
    private var warm = 0
    private var beats: [Beat] = []
    private var lastBeatTime: Double?
    private var amplitudes: [Double] = []

    /// R-wave polarity learned from the first beats (+1 upright, −1 inverted electrode placement); 0 = not yet known.
    private var polarity: Double {
        guard amplitudes.count >= 5 else { return 0 }
        let sorted = amplitudes.sorted()
        let median = sorted[sorted.count / 2]
        return median >= 0 ? 1 : -1
    }

    private func score(_ v: Double, _ sign: Double) -> Double { sign == 0 ? abs(v) : v * sign }

    public init(sampleRate: Double = 100) {
        fs = sampleRate
    }

    private var maLen: Int { Int(0.6 * fs) }
    private var mwiLen: Int { max(3, Int(0.15 * fs)) }
    private var refractory: Int { Int(0.25 * fs) }
    private var search: Int { max(2, Int(0.10 * fs)) }
    private var keep: Int { Int(3 * fs) }

    /// Feed samples (µV); returns beats detected in this chunk.
    @discardableResult
    public func process(_ samples: [Int16]) -> [Beat] {
        var out: [Beat] = []
        for s in samples {
            let x = Double(s)
            raw.append(x); if raw.count > keep { raw.removeFirst(raw.count - keep) }
            maWindow.append(x); maSum += x
            if maWindow.count > maLen { maSum -= maWindow.removeFirst() }
            // baseline at the centre of the MA window: compare against the sample maLen/2 ago
            let centre = raw.count >= maLen / 2 + 1 ? raw[raw.count - 1 - maLen / 2] : x
            let h = centre - maSum / Double(maWindow.count)
            hp.append(h); if hp.count > keep { hp.removeFirst(hp.count - keep) }
            let d = h - prevHp; prevHp = h
            let q = d * d
            sq.append(q); sqSum += q
            if sq.count > mwiLen { sqSum -= sq.removeFirst() }
            let mwi = sqSum / Double(sq.count)
            n += 1
            warm += 1
            if warm < Int(2 * fs) {  // learn initial levels for 2 s
                spk = max(spk, mwi); npk = 0.25 * spk
                mwiPrev2 = mwiPrev; mwiPrev = mwi
                continue
            }
            // local maximum of the integrator one sample ago
            if mwiPrev > mwiPrev2 && mwiPrev >= mwi {
                let peak = mwiPrev
                let threshold = npk + 0.25 * (spk - npk)
                let idx = n - 2
                if peak > threshold && idx - lastBeatSample > refractory {
                    if let b = locate(atSample: idx) {
                        spk = 0.125 * peak + 0.875 * spk
                        lastBeatSample = idx
                        out.append(b)
                    }
                } else {
                    npk = 0.125 * peak + 0.875 * npk
                }
            }
            mwiPrev2 = mwiPrev; mwiPrev = mwi
        }
        return out
    }

    private func locate(atSample idx: Int) -> Beat? {
        // `idx` counts the high-passed stream (one value per input sample). The integrator peak trails the QRS by ~mwiLen/2.
        let centre = idx - mwiLen / 2
        let pos = hp.count - 1 - (n - 1 - centre)
        let lo = max(0, pos - search), hi = min(hp.count - 1, pos + search)
        guard lo < hi else { return nil }
        let sign = polarity
        var j = lo
        for k in lo...hi where score(hp[k], sign) > score(hp[j], sign) { j = k }
        var offset = 0.0
        if j > 0 && j < hp.count - 1 {
            let a = score(hp[j - 1], sign), b = score(hp[j], sign), c = score(hp[j + 1], sign)
            let den = a - 2 * b + c
            if den != 0 { offset = max(-0.5, min(0.5, 0.5 * (a - c) / den)) }
        }
        // hp stream index → input sample index: the baseline filter centres on the sample maLen/2 earlier
        let hpIndex = Double(n - 1 - (hp.count - 1 - j))
        let t = (hpIndex - Double(maLen / 2) + offset) / fs
        amplitudes.append(hp[j]); if amplitudes.count > 15 { amplitudes.removeFirst() }
        var rr: Double?
        var valid = false
        if let last = lastBeatTime {
            let v = (t - last) * 1000
            rr = v
            let recent = beats.suffix(9).compactMap { $0.valid ? $0.rrMs : nil }.sorted()
            let median = recent.isEmpty ? v : recent[recent.count / 2]
            valid = v >= 300 && v <= 2000 && abs(v - median) <= 0.3 * median
        }
        lastBeatTime = t
        let beat = Beat(time: t, rrMs: rr, valid: valid, amplitude: hp[j])
        beats.append(beat)
        if beats.count > 2000 { beats.removeFirst(beats.count - 2000) }
        return beat
    }

    public var metrics: Metrics {
        let now = Double(n) / fs
        let valid = beats.filter { $0.valid && $0.rrMs != nil }
        let last8 = valid.suffix(8).compactMap(\.rrMs)
        func rmssd(_ window: Double) -> Double? {
            // successive differences only between consecutive valid beats
            var diffs: [Double] = []
            var prev: Beat?
            for b in beats where b.time >= now - window {
                if let p = prev, p.valid, b.valid, let a = p.rrMs, let c = b.rrMs { diffs.append(c - a) }
                prev = b
            }
            guard diffs.count >= 5 else { return nil }
            return (diffs.map { $0 * $0 }.reduce(0, +) / Double(diffs.count)).squareRoot()
        }
        let rr60 = valid.filter { $0.time >= now - 60 }.compactMap(\.rrMs)
        var sdnn: Double?
        var pnn: Double?
        if rr60.count >= 10 {
            let m = rr60.reduce(0, +) / Double(rr60.count)
            sdnn = (rr60.map { ($0 - m) * ($0 - m) }.reduce(0, +) / Double(rr60.count - 1)).squareRoot()
            let d = zip(rr60, rr60.dropFirst()).map { abs($1 - $0) }
            pnn = 100 * Double(d.filter { $0 > 50 }.count) / Double(max(1, d.count))
        }
        let recent = beats.filter { $0.time >= now - 30 && $0.rrMs != nil }
        let quality = recent.isEmpty ? 0 : Double(recent.filter(\.valid).count) / Double(recent.count)
        return Metrics(heartRate: last8.count >= 3 ? 60000 / (last8.reduce(0, +) / Double(last8.count)) : nil,
                       rmssd60: rmssd(60), rmssd300: rmssd(300), sdnn60: sdnn, pnn50: pnn, quality: quality, beatCount: beats.count)
    }

    public func reset() {
        n = 0; raw = []; maWindow = []; maSum = 0; hp = []; prevHp = 0; sq = []; sqSum = 0
        mwiPrev = 0; mwiPrev2 = 0; spk = 0; npk = 0; lastBeatSample = -100_000; warm = 0; beats = []; lastBeatTime = nil; amplitudes = []
    }
}
