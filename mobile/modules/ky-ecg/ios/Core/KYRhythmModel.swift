import Foundation

/// Rhythm classifier (Normal · AF · Other · Noisy) on a 30-s single-lead window — screening, not diagnosis.
/// Gradient-boosted trees (150 × 4, ≤ 15 leaves) trained on PhysioNet CinC 2017 (8,528 single-lead ECGs) resampled to
/// 100 Hz and run through the Telomy beat detector; 5-fold CV challenge F1 0.78, AF Se 79 % / Sp 98 %
/// (telomy-lab/af2017). Features mirror train_af.py exactly (verified by kyval parity).
public final class KYRhythmModel {
    public static let classes = ["Normal", "AF", "Other", "Noisy"]
    struct Tree { let f: [Int]; let t: [Double]; let l: [Int]; let r: [Int]; let leaf: [Bool]; let v: [Double] }
    let trees: [[Tree]], base: [Double]
    public let afThreshold: Double

    public init?(json data: Data) {
        guard let o = try? JSONSerialization.jsonObject(with: data) as? [String: Any], let b = o["baseline"] as? [Double],
              let tr = o["trees"] as? [[[String: Any]]] else { return nil }
        base = b; afThreshold = o["af_threshold"] as? Double ?? 0.5
        trees = tr.map { it in it.map { d in
            Tree(f: d["f"] as! [Int], t: (d["t"] as! [NSNumber]).map(\.doubleValue), l: d["l"] as! [Int], r: d["r"] as! [Int],
                 leaf: (d["leaf"] as! [Int]).map { $0 != 0 }, v: (d["v"] as! [NSNumber]).map(\.doubleValue))
        } }
    }

    public static let shared: KYRhythmModel? = {
        for b in [Bundle(for: KYRhythmModel.self), Bundle.main] {
            if let u = b.url(forResource: "KyEcgModels", withExtension: "bundle"), let rb = Bundle(url: u),
               let f = rb.url(forResource: "rhythm_model", withExtension: "json"), let d = try? Data(contentsOf: f) { return KYRhythmModel(json: d) }
        }
        return nil
    }()

    public func predict(_ x: [Double]) -> [Double] {
        var raw = base
        for it in trees {
            for (c, t) in it.enumerated() {
                var i = 0
                while !t.leaf[i] { i = x[t.f[i]] <= t.t[i] ? t.l[i] : t.r[i] }
                raw[c] += t.v[i]
            }
        }
        let m = raw.max()!, e = raw.map { exp($0 - m) }, s = e.reduce(0, +)
        return e.map { $0 / s }
    }

    // MARK: features (train_af.py `features`, without n_beats)

    static func median(_ v: [Double]) -> Double {
        let s = v.sorted(), n = s.count
        return n == 0 ? .nan : n % 2 == 1 ? s[n / 2] : (s[n / 2 - 1] + s[n / 2]) / 2
    }
    static func std(_ v: [Double]) -> Double { let m = v.reduce(0, +) / Double(v.count); return (v.map { ($0 - m) * ($0 - m) }.reduce(0, +) / Double(v.count)).squareRoot() }

    /// x: raw window (µV, 100 Hz); beats: sample indices within the window; amps: R amplitudes.
    public static func features(x: [Double], beats: [Double], amps: [Double]) -> [Double] {
        let fs = 100.0, dur = Double(x.count) / fs
        let rr = zip(beats, beats.dropFirst()).map { ($1 - $0) / fs * 1000 }
        let r = Array(rr.filter { $0 > 250 && $0 < 2500 }.suffix(64))
        var f: [String: Double] = [:]
        f["beat_cov"] = rr.isEmpty ? 0 : (rr.reduce(0, +) / 1000) / dur
        let d = zip(x, x.dropFirst()).map { $1 - $0 }
        f["hf_noise"] = log(d.map(abs).reduce(0, +) / Double(max(1, d.count)) + 1) - log(std(x) + 1)
        f["flat_frac"] = Double(d.filter { abs($0) < 2 }.count) / Double(max(1, d.count))
        if r.count >= 6 {
            let m = r.reduce(0, +) / Double(r.count), dd = zip(r, r.dropFirst()).map { $1 - $0 }
            f["hr"] = 60000 / m; f["rr_cv"] = std(r) / m
            f["nrmssd"] = (dd.map { $0 * $0 }.reduce(0, +) / Double(dd.count)).squareRoot() / m
            f["pnn50"] = Double(dd.filter { abs($0) > 50 }.count) / Double(dd.count)
            f["pnn20"] = Double(dd.filter { abs($0) > 20 }.count) / Double(dd.count)
            f["shannon"] = KYRhythmStats.shannonEntropy(r); f["tpr"] = KYRhythmStats.turningPointRatio(r)
            f["cosen"] = KYRhythmStats.cosEn(r) ?? -9
            f["irr_frac"] = Double(zip(dd, r.dropFirst()).filter { abs($0) / $1 > 0.1 }.count) / Double(dd.count)
            let med = median(r)
            f["mad_ratio"] = median(dd.map(abs)) / med
            f["range_ratio"] = (r.max()! - r.min()!) / med; f["min_ratio"] = r.min()! / med; f["max_ratio"] = r.max()! / med
            let sd1 = std(dd) / 2.0.squareRoot(), v = std(r) * std(r)
            f["sd1_sd2"] = sd1 / max(1e-9, 2 * v - sd1 * sd1).squareRoot()
        }
        if amps.count > 4 { f["amp_cv"] = std(amps) / (amps.map(abs).reduce(0, +) / Double(amps.count) + 1) }
        let (pw, pa) = pwave(x, beats); f["pwave"] = pw; f["pwave_amp"] = pa
        let order = ["hr", "rr_cv", "nrmssd", "pnn50", "pnn20", "shannon", "tpr", "cosen", "sd1_sd2", "irr_frac", "mad_ratio", "range_ratio",
                     "min_ratio", "max_ratio", "pwave", "pwave_amp", "amp_cv", "beat_cov", "hf_noise", "flat_frac"]
        return order.map { let v = f[$0] ?? 0; return v.isFinite ? v : 0 }
    }

    static func pwave(_ x: [Double], _ beats: [Double]) -> (Double, Double) {
        var segs: [[Double]] = []
        for b in beats {
            let s = Int(b.rounded(.toNearestOrEven))
            if s - 30 < 0 || s - 10 > x.count { continue }
            guard s - 9 <= x.count else { continue }
            var y = Array(x[(s - 30)..<(s - 9)])
            guard y.count == 21 else { continue }
            let mx = 10.0, my = y.reduce(0, +) / 21
            var sxy = 0.0, sxx = 0.0
            for k in 0..<21 { sxy += (Double(k) - mx) * (y[k] - my); sxx += (Double(k) - mx) * (Double(k) - mx) }
            let sl = sxy / sxx
            for k in 0..<21 { y[k] -= my + sl * (Double(k) - mx) }
            segs.append(y)
        }
        guard segs.count >= 8 else { return (-1, 0) }
        let t = (0..<21).map { k in segs.reduce(0) { $0 + $1[k] } / Double(segs.count) }
        let tsd = (t.map { $0 * $0 }.reduce(0, +) / 21).squareRoot()
        if tsd < 8 { return (0, tsd) }
        let c = segs.map { y -> Double in
            let ysd = (y.map { $0 * $0 }.reduce(0, +) / 21).squareRoot()
            return zip(y, t).map { $0 * $1 }.reduce(0, +) / 21 / (ysd * tsd + 1e-9)
        }
        return (median(c), tsd)
    }
}
