import Foundation

/// Whole-night sleep/wake estimate from beat times only (used after a recording is synced).
///
/// Features per 30-s epoch (AASM epoch length): mean HR, ln RMSSD, SD of RR, fraction |ΔRR| > 50 ms, SD of HR.
/// Each is normalised to the person's own night (median / IQR), then averaged over centred windows of 3, 11 and 21 epochs
/// (plus HR instability in each window) and combined with time since start in a logistic model.
/// Trained and tested leave-one-subject-out on PhysioNet slpdb (10 subjects with sleep apnoea, 6 191 epochs):
/// accuracy 68 %, Cohen's κ 0.33. ECG-only sleep estimation is limited — the app labels it "estimated".
public enum KYSleepNight {
    static let weights: [Double] = [0.9684, 0.0079, 0.0343, 0.1315, 0.1157, -0.1293, -0.0360, 0.1006, 0.1904, 0.1858, -0.2087,
                                    -0.1256, -0.0747, 0.1413, 0.1932, 0.2312, -0.2922, -0.1840, -0.0647, 0.1431, 0.1597, 0.2263,
                                    -0.3379, -0.2232, -0.2137]

    public struct Result {
        public var probability: [Double]       // per epoch, P(asleep)
        public var asleep: [Bool]              // after 5-epoch median smoothing
        public var totalSleepMin: Double
        public var sleepOnsetMin: Double?      // minutes from start to first 10 min of sleep
        public var wakeAfterOnsetMin: Double
        public var efficiency: Double          // sleep / time from onset to last sleep epoch
        public var awakenings: Int             // wake bouts ≥ 2 epochs after onset
        public var sleepHr: Double?            // mean HR while asleep
        public var sleepRmssd: Double?         // median epoch RMSSD while asleep
    }

    static func percentile(_ s: [Double], _ q: Double) -> Double {
        guard !s.isEmpty else { return 0 }
        let pos = q * Double(s.count - 1), lo = Int(pos.rounded(.down)), hi = min(s.count - 1, lo + 1)
        return s[lo] + (s[hi] - s[lo]) * (pos - Double(lo))
    }

    static func std(_ v: [Double]) -> Double {
        let m = v.reduce(0, +) / Double(v.count)
        return (v.map { ($0 - m) * ($0 - m) }.reduce(0, +) / Double(v.count)).squareRoot()
    }

    /// `beats` = beat times in seconds from the recording start.
    public static func analyze(beats: [Double], durationSec: Double) -> Result? {
        let nEp = Int(durationSec / 30)
        guard nEp >= 20, beats.count > 100 else { return nil }
        // RR series, timestamped by the ending beat
        var rrT: [Double] = [], rr: [Double] = []
        for i in 1..<beats.count {
            let v = (beats[i] - beats[i - 1]) * 1000
            if v > 300 && v < 2000 { rrT.append(beats[i]); rr.append(v) }
        }
        var F = [[Double]](repeating: [.nan, .nan, .nan, .nan, .nan], count: nEp)
        var rmssdEpoch = [Double?](repeating: nil, count: nEp)
        var k = 0
        for e in 0..<nEp {
            var w: [Double] = []
            while k < rrT.count && rrT[k] < Double(e) * 30 { k += 1 }
            var j = k
            while j < rrT.count && rrT[j] < Double(e + 1) * 30 { w.append(rr[j]); j += 1 }
            guard w.count >= 10 else { continue }
            let d = zip(w, w.dropFirst()).map { $1 - $0 }
            let rm = (d.map { $0 * $0 }.reduce(0, +) / Double(d.count)).squareRoot()
            rmssdEpoch[e] = rm
            F[e] = [60000 / (w.reduce(0, +) / Double(w.count)), log(max(1, rm)), std(w),
                    Double(d.filter { abs($0) > 50 }.count) / Double(d.count), std(w.map { 60000 / $0 })]
        }
        // per-night robust z-score (median fill, IQR scale)
        var G = F
        for c in 0..<5 {
            let vals = F.map { $0[c] }.filter { !$0.isNaN }.sorted()
            guard !vals.isEmpty else { return nil }
            let med = percentile(vals, 0.5)
            var col = F.map { $0[c].isNaN ? med : $0[c] }
            let s = col.sorted()
            var iqr = percentile(s, 0.75) - percentile(s, 0.25)
            if iqr == 0 { iqr = 1 }
            col = col.map { ($0 - med) / iqr }
            for e in 0..<nEp { G[e][c] = col[e] }
        }
        var X = [[Double]](repeating: [], count: nEp)
        for e in 0..<nEp { X[e] = G[e] }
        for win in [3, 11, 21] {
            let h = win / 2
            for e in 0..<nEp {
                var sums = [Double](repeating: 0, count: 5)
                var hr: [Double] = []
                for i in (e - h)...(e + h) {
                    let row = G[min(nEp - 1, max(0, i))]  // edge padding
                    for c in 0..<5 { sums[c] += row[c] }
                    hr.append(row[0])
                }
                X[e] += sums.map { $0 / Double(win) } + [std(hr)]
            }
        }
        for e in 0..<nEp { X[e].append(Double(e) / 120) }
        let p = X.map { x -> Double in
            var z = weights[0]
            for (i, v) in x.enumerated() { z += weights[i + 1] * v }
            return 1 / (1 + exp(-z))
        }
        let raw = p.map { $0 > 0.5 }
        let asleep = (0..<nEp).map { e -> Bool in
            let w = raw[max(0, e - 2)...min(nEp - 1, e + 2)]
            return w.filter { $0 }.count * 2 > w.count
        }
        // summary
        var onset: Int?
        for e in 0..<max(0, nEp - 20) where asleep[e..<(e + 20)].filter({ $0 }).count >= 18 { onset = e; break }
        let lastSleep = asleep.lastIndex(of: true)
        var waso = 0.0, awakenings = 0, efficiency = 0.0
        if let o = onset, let l = lastSleep, l > o {
            let span = asleep[o...l]
            waso = Double(span.filter { !$0 }.count) * 0.5
            efficiency = Double(span.filter { $0 }.count) / Double(span.count)
            var run = 0
            for s in span { if !s { run += 1 } else { if run >= 2 { awakenings += 1 }; run = 0 } }
        }
        let sleepHrs = (0..<nEp).filter { asleep[$0] && !F[$0][0].isNaN }.map { F[$0][0] }
        let sleepRm = (0..<nEp).compactMap { asleep[$0] ? rmssdEpoch[$0] : nil }.sorted()
        return Result(probability: p, asleep: asleep, totalSleepMin: Double(asleep.filter { $0 }.count) * 0.5,
                      sleepOnsetMin: onset.map { Double($0) * 0.5 }, wakeAfterOnsetMin: waso, efficiency: efficiency,
                      awakenings: awakenings, sleepHr: sleepHrs.isEmpty ? nil : sleepHrs.reduce(0, +) / Double(sleepHrs.count),
                      sleepRmssd: sleepRm.isEmpty ? nil : sleepRm[sleepRm.count / 2])
    }
}
