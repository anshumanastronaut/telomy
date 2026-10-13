import Foundation

/// Overnight metrics from beats + the whole-night sleep estimate (wellness, not diagnosis).
///
/// - Lowest heart rate: minimum of the 5-min mean HR while asleep, and when it happened (as a fraction of the sleep
///   period; Oura's "recovery index" idea: a low point early in the night suggests good recovery).
/// - HR drop: pre-sleep (in-bed, awake) mean HR vs mean HR asleep, in %.
/// - Overnight HRV: RMSSD per 5 min (clean, artefact-corrected, Task Force 1996); median asleep and last third of the night.
/// - Breathing rate: ECG-derived respiration (Charlton et al. 2016): per 64-s window, RR-interval and R-amplitude series
///   resampled to 4 Hz, 8-s moving-average detrend, Welch PSD peak in 0.16–0.5 Hz (9.6–30 br/min); "smart fusion"
///   (Karlen et al. 2013): kept when both agree within 4 br/min. Validated against the respiration belt on PhysioNet slpdb
///   (10 nights): MAE 1.4 br/min, 85 % of windows within 2 br/min (`telomy-lab/validate/edr`).
public enum KYNightMetrics {
    public struct Beat { public let t: Double; public let rr: Double?; public let amp: Double
        public init(t: Double, rr: Double?, amp: Double) { self.t = t; self.rr = rr; self.amp = amp } }

    /// - Parameters: beats with unix times; `asleep` per 30-s epoch starting at `t0` (unix).
    public static func compute(beats: [Beat], asleep: [Bool], t0: Double, epochSec: Double = 30) -> [String: Any] {
        var out: [String: Any] = [:]
        // clean RR: physiological range and < 20 % change from the previous interval
        var clean: [(t: Double, rr: Double, amp: Double)] = []
        var prev: Double?
        for b in beats {
            guard let rr = b.rr, rr > 300, rr < 2000 else { prev = nil; continue }
            if let p = prev, abs(rr - p) < 0.2 * p { clean.append((b.t, rr, b.amp)) }
            prev = rr
        }
        guard clean.count > 200 else { return out }
        func isAsleep(_ t: Double) -> Bool {
            let i = Int((t - t0) / epochSec); return i >= 0 && i < asleep.count && asleep[i]
        }
        guard let firstSleep = asleep.firstIndex(of: true), let lastSleep = asleep.lastIndex(of: true) else { return out }
        let onset = t0 + Double(firstSleep) * epochSec, wake = t0 + Double(lastSleep + 1) * epochSec

        // 5-min series (whole recording) for charts
        var hr5: [[Double]] = [], hrv5: [[Double]] = []
        var w = clean.first!.t
        let end = clean.last!.t
        var i0 = 0
        while w < end {
            while i0 < clean.count && clean[i0].t < w { i0 += 1 }
            var j = i0; var seg: [Double] = []
            while j < clean.count && clean[j].t < w + 300 { seg.append(clean[j].rr); j += 1 }
            if seg.count >= 150 {
                let mid = w + 150
                hr5.append([mid, 60000 / (seg.reduce(0, +) / Double(seg.count)), isAsleep(mid) ? 1 : 0])
                let d = zip(seg, seg.dropFirst()).map { $1 - $0 }
                hrv5.append([mid, (d.map { $0 * $0 }.reduce(0, +) / Double(d.count)).squareRoot(), isAsleep(mid) ? 1 : 0])
            }
            w += 300
        }
        out["hr5"] = hr5.map { [$0[0].rounded(), ($0[1] * 10).rounded() / 10, $0[2]] }
        out["hrv5"] = hrv5.map { [$0[0].rounded(), ($0[1] * 10).rounded() / 10, $0[2]] }

        let sleepHr = hr5.filter { $0[2] == 1 }
        if let low = sleepHr.min(by: { $0[1] < $1[1] }) {
            out["lowestHr"] = low[1]
            out["lowestHrAt"] = low[0]
            out["lowestHrPos"] = max(0, min(1, (low[0] - onset) / max(1, wake - onset)))  // 0 = sleep onset, 1 = final wake
        }
        if !sleepHr.isEmpty { out["avgSleepHr"] = sleepHr.map { $0[1] }.reduce(0, +) / Double(sleepHr.count) }
        // pre-sleep: clean beats in the 20 min before onset (in bed, awake)
        let pre = clean.filter { $0.t >= onset - 1200 && $0.t < onset }.map(\.rr)
        if pre.count >= 100, let avg = out["avgSleepHr"] as? Double {
            let preHr = 60000 / (pre.reduce(0, +) / Double(pre.count))
            out["preSleepHr"] = preHr
            out["hrDropPct"] = (preHr - avg) / preHr * 100
        }
        let sleepHrv = hrv5.filter { $0[2] == 1 }.map { $0[1] }.sorted()
        if !sleepHrv.isEmpty { out["sleepRmssd"] = sleepHrv[sleepHrv.count / 2] }
        let lateFrom = onset + 2 * (wake - onset) / 3
        let late = hrv5.filter { $0[2] == 1 && $0[0] >= lateFrom }.map { $0[1] }.sorted()
        if !late.isEmpty { out["lateRmssd"] = late[late.count / 2] }

        // breathing rate while asleep
        var rates: [Double] = []; var windows = 0
        var s = onset
        var k0 = 0
        while s + 64 <= wake {
            if isAsleep(s + 32) {
                windows += 1
                while k0 < clean.count && clean[k0].t < s { k0 += 1 }
                var k = k0; var tt: [Double] = [], rr: [Double] = [], aa: [Double] = []
                while k < clean.count && clean[k].t < s + 64 { tt.append(clean[k].t); rr.append(clean[k].rr); aa.append(clean[k].amp); k += 1 }
                if tt.count >= 40, let a = peakRate(tt, rr, from: s), let b = peakRate(tt, aa, from: s), abs(a - b) <= 4 {
                    rates.append((a + b) / 2)
                }
            }
            s += 32
        }
        if windows > 0 { out["respCoverage"] = Double(rates.count) / Double(windows) }
        if rates.count >= 20 && Double(rates.count) / Double(windows) >= 0.3 {
            let r = rates.sorted(); out["respRate"] = r[r.count / 2]
        }
        return out
    }

    private struct Table { let seg: Int; let kLo: Int; let bins: Int; let cosW: [Double]; let sinW: [Double] }
    /// Hann-windowed DFT kernels for bins 0.16–0.5 Hz at fs 4 Hz, nfft 1024, segment 128.
    private static let table: Table = {
        let fs = 4.0, nfft = 1024.0, seg = 128
        let kLo = Int((0.16 * nfft / fs).rounded(.up)), kHi = Int((0.5 * nfft / fs).rounded(.down))
        var c: [Double] = [], s: [Double] = []
        for kk in kLo...kHi {
            let w = 2 * Double.pi * Double(kk) / nfft
            for m in 0..<seg {
                let h = 0.5 - 0.5 * cos(2 * .pi * Double(m) / Double(seg - 1))
                c.append(h * cos(w * Double(m))); s.append(h * sin(w * Double(m)))
            }
        }
        return Table(seg: seg, kLo: kLo, bins: kHi - kLo + 1, cosW: c, sinW: s)
    }()

    /// Dominant frequency (br/min) of a beat-sampled series over a 64-s window.
    static func peakRate(_ t: [Double], _ v: [Double], from s: Double) -> Double? {
        let fs = 4.0, n = 256
        var x = [Double](repeating: 0, count: n)
        var j = 0
        for i in 0..<n {  // linear interpolation onto a 4 Hz grid
            let g = s + Double(i) / fs
            while j + 1 < t.count && t[j + 1] < g { j += 1 }
            if g <= t[0] { x[i] = v[0] } else if j + 1 >= t.count { x[i] = v[t.count - 1] }
            else { let f = (g - t[j]) / (t[j + 1] - t[j]); x[i] = v[j] + f * (v[j + 1] - v[j]) }
        }
        // 8-s moving-average detrend (edge-padded running sum)
        let k = Int(8 * fs), h = k / 2
        var pref = [Double](repeating: 0, count: n + k + 1)
        for i in 0..<(n + k) { pref[i + 1] = pref[i] + x[min(n - 1, max(0, i - h))] }
        let detr = (0..<n).map { i in x[i] - (pref[i + k] - pref[i]) / Double(k) }
        // Welch: 128-sample Hann segments, 50 % overlap, evaluated on a 1024-point grid in 0.16–0.5 Hz (precomputed tables)
        let tb = table
        var power = [Double](repeating: 0, count: tb.bins)
        var start = 0
        while start + tb.seg <= n {
            for bi in 0..<tb.bins {
                var re = 0.0, im = 0.0
                let base = bi * tb.seg
                for m in 0..<tb.seg {
                    let y = detr[start + m]
                    re += y * tb.cosW[base + m]; im -= y * tb.sinW[base + m]
                }
                power[bi] += re * re + im * im
            }
            start += tb.seg / 2
        }
        let kLo = tb.kLo
        guard let best = power.indices.max(by: { power[$0] < power[$1] }), power[best] > 0 else { return nil }
        return Double(kLo + best) * fs / 1024 * 60
    }
}
