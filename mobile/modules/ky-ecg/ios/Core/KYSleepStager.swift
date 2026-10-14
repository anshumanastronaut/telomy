import Foundation

/// 4-class sleep staging (Wake · Light · Deep · REM) from single-lead ECG beats — wellness estimate, not a sleep study.
///
/// Port of telomy-lab/sleepstage (features.py + train_seq.py): 19 cardiorespiratory features per 30-s epoch
/// (HR, HRV time/frequency domain, DFA α1, ECG-derived respiration rate and regularity, position in the night),
/// per-night robust normalisation, then Conv1d(19→32,k5) → BiGRU(32) → Linear(64→4) over the whole night.
/// Trained on PhysioNet HMC (CC BY 4.0) with subject-wise CV; weights are loaded from JSON (`load(json:)`).
/// Approach after Sridhar et al. 2020 (IHR + deep sequence model) and Radha et al. 2019 (HRV + LSTM).
public final class KYSleepStager {
    public static let classes = ["Wake", "Light", "Deep", "REM"]
    static let nFeat = 19
    let H: Int
    let convW: [[[Double]]], convB: [Double]                 // (H, F, 5), (H)
    let gru: [String: [[Double]]], gruB: [String: [Double]]   // weight_ih_l0 (3H, H) …
    let outW: [[Double]], outB: [Double]                      // (4, 2H)

    public init?(json data: Data) {
        guard let o = try? JSONSerialization.jsonObject(with: data) as? [String: Any], let st = o["state"] as? [String: Any],
              let cw = st["conv.weight"] as? [[[Double]]], let cb = st["conv.bias"] as? [Double],
              let ow = st["out.weight"] as? [[Double]], let ob = st["out.bias"] as? [Double] else { return nil }
        convW = cw; convB = cb; outW = ow; outB = ob; H = cb.count
        var g: [String: [[Double]]] = [:], gb: [String: [Double]] = [:]
        for k in ["weight_ih_l0", "weight_hh_l0", "weight_ih_l0_reverse", "weight_hh_l0_reverse"] {
            guard let m = st["gru." + k] as? [[Double]] else { return nil }; g[k] = m
        }
        for k in ["bias_ih_l0", "bias_hh_l0", "bias_ih_l0_reverse", "bias_hh_l0_reverse"] {
            guard let v = st["gru." + k] as? [Double] else { return nil }; gb[k] = v
        }
        gru = g; gruB = gb
    }

    public struct Result {
        public var stages: [Int]            // per 30-s epoch: 0 wake, 1 light, 2 deep, 3 REM, -1 no data
        public var probabilities: [[Double]]
        public var minutes: [Double]        // per class
    }

    /// beats: beat times (s, any origin) and R amplitudes; epoch i covers [t0 + 30 i, +30).
    public func stage(beatTimes: [Double], amplitudes: [Double], t0: Double, epochs: Int) -> Result {
        let F = Self.epochFeatures(beats: beatTimes, amps: amplitudes, n: epochs, t0: t0)
        let G = Self.normalise(F)
        let P = forward(G)
        var stages = P.map { p in p.indices.max(by: { p[$0] < p[$1] })! }
        for i in 0..<epochs where F[i][0].isNaN { stages[i] = -1 }
        var mins = [0.0, 0, 0, 0]
        for s in stages where s >= 0 { mins[s] += 0.5 }
        return Result(stages: stages, probabilities: P, minutes: mins)
    }

    /// Bundled weights (KyEcgModels.bundle/sleep_stager.json).
    public static let shared: KYSleepStager? = {
        for b in [Bundle(for: KYSleepStager.self), Bundle.main] {
            if let u = b.url(forResource: "KyEcgModels", withExtension: "bundle"), let rb = Bundle(url: u),
               let f = rb.url(forResource: "sleep_stager", withExtension: "json"), let d = try? Data(contentsOf: f) { return KYSleepStager(json: d) }
        }
        return nil
    }()

    /// Night summary from the stage sequence (30-s epochs; -1 = no data, treated as wake for continuity).
    public static func summarize(_ stages: [Int]) -> [String: Any] {
        // -1 = no ECG (band disconnected): unknown, never counted as wake or sleep
        let s = stages
        let asleep = s.map { $0 > 0 }
        var out: [String: Any] = [:]
        // onset: first epoch that starts 10 min (20 epochs) of mostly sleep (≥ 16)
        var onset: Int?
        if s.count >= 20 { for i in 0...(s.count - 20) where asleep[i] && asleep[i..<(i + 20)].filter({ $0 }).count >= 16 { onset = i; break } }
        guard let on = onset, let last = asleep.lastIndex(of: true) else { return ["totalSleepMin": 0.0] }
        let span = Array(s[on...last])
        let known = span.filter { $0 >= 0 }
        let tst = Double(known.filter { $0 > 0 }.count) / 2
        var awak = 0, run = 0
        for v in span where v >= 0 { if v == 0 { run += 1 } else { if run >= 2 { awak += 1 }; run = 0 } }
        let mins = (0..<4).map { c in Double(known.filter { $0 == c }.count) / 2 }
        out["totalSleepMin"] = tst
        out["onsetMin"] = Double(s[0..<on].filter { $0 >= 0 }.count) / 2
        out["wasoMin"] = mins[0]
        out["awakenings"] = awak
        out["efficiency"] = known.isEmpty ? 0 : tst / (Double(known.count) / 2)
        out["noDataMin"] = Double(s.filter { $0 < 0 }.count) / 2
        out["lightMin"] = mins[1]; out["deepMin"] = mins[2]; out["remMin"] = mins[3]
        if tst > 0 { out["deepPct"] = mins[2] / tst; out["remPct"] = mins[3] / tst; out["lightPct"] = mins[1] / tst }
        if let r = span.firstIndex(of: 3) { out["remLatencyMin"] = Double(span[0..<r].filter { $0 >= 0 }.count) / 2 }
        // REM periods: ≥ 3 epochs of REM, separated by ≥ 15 min without REM → sleep cycles
        var cycles = 0, lastRem = -1000, i = 0
        while i < span.count {
            if span[i] == 3 {
                var j = i; while j < span.count && span[j] == 3 { j += 1 }
                if j - i >= 3 { if i - lastRem >= 30 { cycles += 1 }; lastRem = j }
                i = j
            } else { i += 1 }
        }
        out["remCycles"] = cycles
        return out
    }

    // MARK: network (eval mode: dropout off)

    func forward(_ G: [[Double]]) -> [[Double]] {
        let T = G.count, F = Self.nFeat
        // Conv1d k=5 padding 2 + ReLU
        var z = [[Double]](repeating: [Double](repeating: 0, count: H), count: T)
        for t in 0..<T {
            for o in 0..<H {
                var s = convB[o]
                for k in 0..<5 {
                    let ti = t + k - 2
                    if ti < 0 || ti >= T { continue }
                    let row = G[ti], w = convW[o]
                    for f in 0..<F { s += w[f][k] * row[f] }
                }
                z[t][o] = max(0, s)
            }
        }
        let fwd = runGRU(z, suffix: "", reverse: false), bwd = runGRU(z, suffix: "_reverse", reverse: true)
        return (0..<T).map { t in
            let h = fwd[t] + bwd[t]
            var logits = outB
            for c in 0..<4 { for j in 0..<(2 * H) { logits[c] += outW[c][j] * h[j] } }
            let m = logits.max()!, e = logits.map { exp($0 - m) }, s = e.reduce(0, +)
            return e.map { $0 / s }
        }
    }

    private func runGRU(_ x: [[Double]], suffix: String, reverse: Bool) -> [[Double]] {
        let Wih = gru["weight_ih_l0" + suffix]!, Whh = gru["weight_hh_l0" + suffix]!
        let bih = gruB["bias_ih_l0" + suffix]!, bhh = gruB["bias_hh_l0" + suffix]!
        let T = x.count
        var h = [Double](repeating: 0, count: H)
        var out = [[Double]](repeating: [], count: T)
        func mv(_ W: [[Double]], _ v: [Double], _ row: Int) -> Double { var s = 0.0; for j in 0..<v.count { s += W[row][j] * v[j] }; return s }
        let order = reverse ? Array((0..<T).reversed()) : Array(0..<T)
        for t in order {
            let xt = x[t]
            var nh = [Double](repeating: 0, count: H)
            for i in 0..<H {
                let r = sigmoid(mv(Wih, xt, i) + bih[i] + mv(Whh, h, i) + bhh[i])
                let zg = sigmoid(mv(Wih, xt, H + i) + bih[H + i] + mv(Whh, h, H + i) + bhh[H + i])
                let n = tanh(mv(Wih, xt, 2 * H + i) + bih[2 * H + i] + r * (mv(Whh, h, 2 * H + i) + bhh[2 * H + i]))
                nh[i] = (1 - zg) * n + zg * h[i]
            }
            h = nh; out[t] = h
        }
        return out
    }

    private func sigmoid(_ x: Double) -> Double { 1 / (1 + exp(-x)) }

    // MARK: features (must match features.py exactly)

    static func interp(_ grid: [Double], _ t: [Double], _ v: [Double]) -> [Double] {
        var j = 0
        return grid.map { g in
            if g <= t[0] { return v[0] }
            if g >= t[t.count - 1] { return v[v.count - 1] }
            while j + 1 < t.count && t[j + 1] < g { j += 1 }
            while j > 0 && t[j] > g { j -= 1 }
            let f = (g - t[j]) / (t[j + 1] - t[j]); return v[j] + f * (v[j + 1] - v[j])
        }
    }

    static func hanning(_ n: Int) -> [Double] { n == 1 ? [1] : (0..<n).map { 0.5 - 0.5 * cos(2 * .pi * Double($0) / Double(n - 1)) } }

    /// |rfft|² at bins k (frequency k / (n·dt)); cos/sin tables cached per (n, bins) — the same sizes repeat every epoch.
    private static var twiddles: [String: (c: [Double], s: [Double])] = [:]
    private static let twLock = NSLock()
    static func power(_ x: [Double], bins: ClosedRange<Int>) -> [Double] {
        let n = x.count, key = "\(n):\(bins.lowerBound):\(bins.upperBound)"
        twLock.lock()
        var tw = twiddles[key]
        if tw == nil {
            var c = [Double](), sn = [Double]()
            c.reserveCapacity(bins.count * n); sn.reserveCapacity(bins.count * n)
            for k in bins { let w = 2 * Double.pi * Double(k) / Double(n); for i in 0..<n { c.append(cos(w * Double(i))); sn.append(sin(w * Double(i))) } }
            tw = (c, sn); twiddles[key] = tw
        }
        twLock.unlock()
        let (c, sn) = tw!
        return (0..<bins.count).map { b in
            var re = 0.0, im = 0.0; let o = b * n
            for i in 0..<n { re += x[i] * c[o + i]; im -= x[i] * sn[o + i] }
            return re * re + im * im
        }
    }

    static func arange(_ a: Double, _ b: Double, _ step: Double) -> [Double] {
        let n = Int(((b - a) / step).rounded(.up)); return (0..<max(0, n)).map { a + Double($0) * step }
    }

    static func bandPowers(_ t: [Double], _ rr: [Double], _ a: Double, _ b: Double) -> [Double] {
        let idx = t.indices.filter { t[$0] >= a && t[$0] < b }
        guard idx.count >= 60 else { return [.nan, .nan, .nan, .nan, .nan] }
        let g = arange(a, b, 0.25)
        var x = interp(g, idx.map { t[$0] }, idx.map { rr[$0] })
        let m = x.reduce(0, +) / Double(x.count); let hw = hanning(x.count)
        for i in x.indices { x[i] = (x[i] - m) * hw[i] }
        let n = Double(x.count), df = 1 / (n * 0.25)
        let kmax = Int((0.4 / df).rounded(.up))
        let p = power(x, bins: 0...kmax)
        func bp(_ lo: Double, _ hi: Double) -> Double { var s = 0.0; for k in 0...kmax { let f = Double(k) * df; if f >= lo && f < hi { s += p[k] } }; return s }
        let vlf = bp(0.003, 0.04), lf = bp(0.04, 0.15), hf = bp(0.15, 0.4)
        var best = -1.0, hff = Double.nan
        for k in 0...kmax { let f = Double(k) * df; if f >= 0.15 && f < 0.4 && p[k] > best { best = p[k]; hff = f } }
        if best <= 0 { hff = .nan }
        return [log(vlf + 1), log(lf + 1), log(hf + 1), lf / (hf + 1e-9), hff * 60]
    }

    static func polyfitSlope(_ x: [Double], _ y: [Double]) -> Double {
        let n = Double(x.count), mx = x.reduce(0, +) / n, my = y.reduce(0, +) / n
        var sxy = 0.0, sxx = 0.0
        for i in x.indices { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) * (x[i] - mx) }
        return sxx > 0 ? sxy / sxx : 0
    }

    static func dfaA1(_ rr: [Double]) -> Double {
        guard rr.count >= 64 else { return .nan }
        let m = rr.reduce(0, +) / Double(rr.count)
        var y = [Double](); var c = 0.0
        for v in rr { c += v - m; y.append(c) }
        let ns = [4, 6, 8, 10, 12, 16]; var lf: [Double] = []
        for n in ns {
            let k = y.count / n; guard k >= 2 else { return .nan }
            var ss = 0.0
            let xs = (0..<n).map(Double.init)
            for s in 0..<k {
                let seg = Array(y[(s * n)..<(s * n + n)])
                let sl = polyfitSlope(xs, seg), mx = Double(n - 1) / 2, my = seg.reduce(0, +) / Double(n)
                for i in 0..<n { let r = seg[i] - (my + sl * (xs[i] - mx)); ss += r * r }
            }
            lf.append(log((ss / Double(k * n)).squareRoot()))
        }
        return polyfitSlope(ns.map { log(Double($0)) }, lf)
    }

    static func edrRate(_ t: [Double], _ amp: [Double], _ a: Double, _ b: Double) -> Double {
        let idx = t.indices.filter { t[$0] >= a && t[$0] < b }
        guard idx.count >= 30 else { return .nan }
        let g = arange(a, b, 0.25)
        var x = interp(g, idx.map { t[$0] }, idx.map { amp[$0] })
        let n = x.count, k = 32, h = k / 2
        // np.convolve(np.pad(x, 16, 'edge'), ones(32)/32, 'same')[16:16+n]
        let padded = [Double](repeating: x[0], count: h) + x + [Double](repeating: x[n - 1], count: h)
        let L = padded.count
        var conv = [Double](repeating: 0, count: L)
        for i in 0..<L {
            var s = 0.0
            for j in 0..<k { let idx2 = i + (k - 1) / 2 - j; if idx2 >= 0 && idx2 < L { s += padded[idx2] } }  // numpy 'same' offset
            conv[i] = s / Double(k)
        }
        for i in 0..<n { x[i] -= conv[h + i] }
        let hw = hanning(n); for i in 0..<n { x[i] *= hw[i] }
        let df = 1 / (Double(n) * 0.25)
        let lo = Int((0.16 / df).rounded(.up)), hi = Int((0.5 / df).rounded(.down))
        guard lo <= hi else { return .nan }
        let p = power(x, bins: lo...hi)
        let best = p.indices.max(by: { p[$0] < p[$1] })!
        return Double(lo + best) * df * 60
    }

    static func std(_ v: [Double]) -> Double { let m = v.reduce(0, +) / Double(v.count); return (v.map { ($0 - m) * ($0 - m) }.reduce(0, +) / Double(v.count)).squareRoot() }

    public static func epochFeatures(beats: [Double], amps: [Double], n: Int, t0: Double) -> [[Double]] {
        var tc: [Double] = [], rrc: [Double] = [], amc: [Double] = [], tAll: [Double] = []
        var prev: Double?
        for i in 1..<max(1, beats.count) {
            let rr = (beats[i] - beats[i - 1]) * 1000; tAll.append(beats[i])
            var ok = rr > 300 && rr < 2000
            if ok, let p = prev { ok = abs(rr - p) < 0.2 * rr } else if prev == nil { /* first interval: keep if in range */ }
            prev = rr
            if ok { tc.append(beats[i]); rrc.append(rr); amc.append(amps[i]) }
        }
        var F = [[Double]](repeating: [Double](repeating: .nan, count: nFeat), count: n)
        var resp = [Double](repeating: .nan, count: n)
        for i in 0..<n {
            let s0 = t0 + Double(i) * 30, mid = s0 + 15
            let e = tc.indices.filter { tc[$0] >= s0 && tc[$0] < s0 + 30 }
            let w5 = tc.indices.filter { tc[$0] >= mid - 150 && tc[$0] < mid + 150 }
            let allb = tAll.filter { $0 >= s0 && $0 < s0 + 30 }.count
            guard e.count >= 8 else { continue }
            let r = e.map { rrc[$0] }, r5 = w5.map { rrc[$0] }
            let d = zip(r, r.dropFirst()).map { $1 - $0 }, d5 = zip(r5, r5.dropFirst()).map { $1 - $0 }
            let hr = 60000 / (r.reduce(0, +) / Double(r.count))
            let hr5 = r5.count > 20 ? 60000 / (r5.reduce(0, +) / Double(r5.count)) : hr
            let slope = r5.count > 20 ? polyfitSlope(w5.map { tc[$0] - mid }, r5.map { 60000 / $0 }) * 60 : 0
            let bp = bandPowers(tc, rrc, mid - 150, mid + 150)
            resp[i] = edrRate(tc, amc, mid - 32, mid + 32)
            let rms = { (v: [Double]) in (v.map { $0 * $0 }.reduce(0, +) / Double(v.count)).squareRoot() }
            let a5 = w5.map { amc[$0] }
            F[i] = [hr, hr5, slope,
                    d.isEmpty ? .nan : log(rms(d) + 1),
                    d5.count > 5 ? log(rms(d5) + 1) : .nan,
                    r5.count > 5 ? log(std(r5) + 1) : .nan,
                    d5.count > 5 ? Double(d5.filter { abs($0) > 50 }.count) / Double(d5.count) : .nan,
                    bp[0], bp[1], bp[2], bp[3].isNaN ? .nan : log(bp[3] + 1e-3), bp[4],
                    r5.count >= 64 ? dfaA1(r5) : .nan,
                    w5.count > 20 ? log(std(a5) + 1) : .nan,
                    resp[i], .nan,
                    r5.count > 5 ? std(r5) / (r5.reduce(0, +) / Double(r5.count)) : .nan,
                    1 - Double(e.count) / Double(max(1, allb)), Double(i) / Double(max(1, n - 1))]
        }
        for i in 0..<n {
            let w = resp[max(0, i - 5)..<min(n, i + 6)].filter { !$0.isNaN }
            F[i][15] = w.count >= 4 ? std(Array(w)) : .nan
        }
        return F
    }

    static func percentile(_ s: [Double], _ q: Double) -> Double {
        let pos = q * Double(s.count - 1), lo = Int(pos.rounded(.down)), hi = min(s.count - 1, lo + 1)
        return s[lo] + (pos - Double(lo)) * (s[hi] - s[lo])
    }

    static func normalise(_ F: [[Double]]) -> [[Double]] {
        var G = F
        for j in 0..<nFeat where j != nFeat - 1 {
            let v = F.map { $0[j] }.filter { !$0.isNaN }.sorted()
            if v.count < 10 { for i in G.indices { G[i][j] = 0 }; continue }
            let med = percentile(v, 0.5)
            var iqr = percentile(v, 0.75) - percentile(v, 0.25); if iqr == 0 { iqr = 1 }
            for i in G.indices { let x = (F[i][j] - med) / iqr; G[i][j] = x.isNaN ? 0 : max(-5, min(5, x)) }
        }
        for i in G.indices where G[i][nFeat - 1].isNaN { G[i][nFeat - 1] = 0 }
        return G
    }
}
