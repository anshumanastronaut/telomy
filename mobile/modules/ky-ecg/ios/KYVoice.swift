import AVFoundation
import Foundation

/// On-device voice biomarkers from a short recording (push-to-talk or the 20-s read-aloud check-in).
/// Same features and maths as the server (backend/app/voice.py `acoustics`), so baselines line up:
/// 40 ms Hann frames every 10 ms, energy-gated voicing, autocorrelation pitch (70–400 Hz, r ≥ 0.3),
/// jitter (period-to-period), shimmer (peak-to-peak), HNR from the autocorrelation peak, onset rate, pause ratio.
/// The audio file is deleted as soon as it has been read when `delete` is true: raw audio is never kept.
enum KYVoice {
    static func features(path: String, delete: Bool) -> [String: Any] {
        let url = path.hasPrefix("file://") ? URL(string: path)! : URL(fileURLWithPath: path)
        defer { if delete { try? FileManager.default.removeItem(at: url) } }
        guard let a = read16k(url), a.count >= 8000 else { return ["voiced_s": 0] }
        return acoustics(a, sr: 16000)
    }

    /// Any AVFoundation-readable file → mono Float at 16 kHz.
    static func read16k(_ url: URL) -> [Float]? {
        guard let f = try? AVAudioFile(forReading: url) else { return nil }
        let inFmt = f.processingFormat
        guard let outFmt = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 16000, channels: 1, interleaved: false),
              let conv = AVAudioConverter(from: inFmt, to: outFmt),
              let inBuf = AVAudioPCMBuffer(pcmFormat: inFmt, frameCapacity: AVAudioFrameCount(f.length)) else { return nil }
        do { try f.read(into: inBuf) } catch { return nil }
        let cap = AVAudioFrameCount(Double(inBuf.frameLength) * 16000 / inFmt.sampleRate) + 1024
        guard let outBuf = AVAudioPCMBuffer(pcmFormat: outFmt, frameCapacity: cap) else { return nil }
        var fed = false
        var err: NSError?
        conv.convert(to: outBuf, error: &err) { _, status in
            if fed { status.pointee = .endOfStream; return nil }
            fed = true; status.pointee = .haveData; return inBuf
        }
        guard err == nil, let ch = outBuf.floatChannelData else { return nil }
        return Array(UnsafeBufferPointer(start: ch[0], count: Int(outBuf.frameLength)))
    }

    static func acoustics(_ raw: [Float], sr: Int) -> [String: Any] {
        let m = raw.reduce(0, +) / Float(raw.count)
        let a = raw.map { Double($0 - m) }
        let fl = sr * 40 / 1000, hop = sr / 100
        var starts: [Int] = []
        var i = 0
        while i + fl < a.count { starts.append(i); i += hop }
        let energy = starts.map { s -> Double in var e = 0.0; for k in s..<(s + fl) { e += a[k] * a[k] }; return (e / Double(fl)).squareRoot() }
        let thr = max(1e-4, percentile(energy, 0.3) * 2.5)
        let voiced = energy.map { $0 > thr }
        let win = (0..<fl).map { 0.5 - 0.5 * cos(2 * .pi * Double($0) / Double(fl - 1)) }
        let lo = sr / 400, hi = sr / 70
        var f0: [Double] = [], amp: [Double] = [], hnr: [Double] = []
        for (j, s) in starts.enumerated() where voiced[j] {
            var f = [Double](repeating: 0, count: fl)
            var peak = 0.0
            for k in 0..<fl { f[k] = a[s + k] * win[k]; peak = max(peak, abs(f[k])) }
            var ac0 = 0.0
            for k in 0..<fl { ac0 += f[k] * f[k] }
            guard ac0 > 0 else { continue }
            var best = -Double.infinity, lag = lo
            for L in lo..<min(hi, fl) {
                var s2 = 0.0
                for k in 0..<(fl - L) { s2 += f[k] * f[k + L] }
                if s2 > best { best = s2; lag = L }
            }
            let r = best / ac0
            guard r >= 0.3 else { continue }
            f0.append(Double(sr) / Double(lag))
            amp.append(peak)
            hnr.append(10 * log10(max(r, 1e-6) / max(1 - r, 1e-6)))
        }
        let hopSec = Double(hop) / Double(sr)
        let voicedS = (Double(voiced.filter { $0 }.count) * hopSec * 10).rounded() / 10
        guard f0.count >= 10 else { return ["voiced_s": voicedS] }
        let periods = f0.map { 1 / $0 }
        let pm = periods.reduce(0, +) / Double(periods.count)
        var jit = 0.0
        for k in 1..<periods.count { jit += abs(periods[k] - periods[k - 1]) }
        jit = jit / Double(periods.count - 1) / pm * 100
        var shim: Double? = nil
        if amp.count > 2 {
            let am = amp.reduce(0, +) / Double(amp.count)
            var d = 0.0
            for k in 1..<amp.count { d += abs(amp[k] - amp[k - 1]) }
            shim = d / Double(amp.count - 1) / am * 100
        }
        var onsets = 0
        for k in 1..<voiced.count where voiced[k] && !voiced[k - 1] { onsets += 1 }
        let dur = Double(a.count) / Double(sr)
        let fm = f0.reduce(0, +) / Double(f0.count)
        let fsd = (f0.map { ($0 - fm) * ($0 - fm) }.reduce(0, +) / Double(f0.count)).squareRoot()
        let ev = zip(energy, voiced).filter { $0.1 }.map { $0.0 }
        func r1(_ x: Double) -> Double { (x * 10).rounded() / 10 }
        func r2(_ x: Double) -> Double { (x * 100).rounded() / 100 }
        var out: [String: Any] = [
            "duration_s": r1(dur), "voiced_s": voicedS, "f0_mean": r1(median(f0)), "f0_sd": r1(fsd),
            "f0_cv": (fsd / fm * 1000).rounded() / 1000, "jitter_pct": r2(jit), "hnr_db": r1(median(hnr)),
            "rate_per_s": r2(Double(onsets) / dur), "pause_ratio": r2(1 - Double(ev.count) / Double(voiced.count)),
            "energy_db": r1(20 * log10(ev.reduce(0, +) / Double(max(1, ev.count)) + 1e-9)),
        ]
        if let s = shim { out["shimmer_pct"] = r2(s) }
        return out
    }

    static func percentile(_ v: [Double], _ q: Double) -> Double {
        let s = v.sorted(); guard !s.isEmpty else { return 0 }
        return s[min(s.count - 1, Int(q * Double(s.count)))]
    }
    static func median(_ v: [Double]) -> Double { let s = v.sorted(); return s.isEmpty ? 0 : s[s.count / 2] }
}
