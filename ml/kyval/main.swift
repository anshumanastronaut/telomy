import Foundation
import KYECG

// kyval <in.bin int16 µV @100 Hz> <out.json> — runs the phone pipeline (KYAnalyzer + KYInsight) exactly as the app does,
// in 87-sample chunks, and dumps beats, HR, window classes, AF windows, sleep epochs and events for scoring.
let t00 = Date()
let args = CommandLine.arguments
let data = try Data(contentsOf: URL(fileURLWithPath: args[1]))
let samples: [Int16] = data.withUnsafeBytes { Array($0.bindMemory(to: Int16.self)) }
let restingHr = args.count > 3 ? Double(args[3]) ?? 65 : 65
let env = ProcessInfo.processInfo.environment
if let v = env["KY_TH"].flatMap(Double.init) { KYAnalyzer.tuning.thresholdCoef = v }
if let v = env["KY_DELAY"].flatMap(Double.init) { KYAnalyzer.tuning.confirmDelay = v }
if let v = env["KY_TSLOPE"].flatMap(Double.init) { KYAnalyzer.tuning.tWaveSlope = v }
let a = KYAnalyzer(sampleRate: 100)
let ins = KYInsight(sampleRate: 100, restingHr: restingHr)
ins.keepLogs = true
var beats: [Double] = []
var nmBeats: [KYNightMetrics.Beat] = []
var hr: [[Double]] = []
var sleep: [[Double]] = []
var i = 0
var lastSec = -1
while i < samples.count {
    let chunk = Array(samples[i..<min(i + 87, samples.count)])
    let out = a.process(chunk)
    beats += out.beats.map(\.sample)
    nmBeats += out.beats.map { KYNightMetrics.Beat(t: $0.sample / 100, rr: $0.rrMs, amp: $0.amplitude) }
    ins.process(samples: chunk, beats: out.beats, leadOn: true, quality: a.currentQuality)
    i += chunk.count
    let sec = i / 100
    if sec != lastSec {
        lastSec = sec
        let st = ins.state
        hr.append([Double(sec), st.hr ?? -1, st.hrSd ?? -1, st.rmssd ?? -1, Double(["rest", "light", "active", "moving", "unknown"].firstIndex(of: st.activity.rawValue) ?? 4), st.motionIndex])
        sleep.append([Double(sec), ins.currentSleep == .asleep ? 1 : ins.currentSleep == .awake ? 0 : -1])
    }
}
let tA = Date()
let night = KYSleepNight.analyze(beats: beats.map { $0 / 100 }, durationSec: Double(samples.count) / 100)
var staging: [String: Any] = [:]
if let mp = env["KY_STAGE"], let md = try? Data(contentsOf: URL(fileURLWithPath: mp)), let st = KYSleepStager(json: md) {
    let n = Int(Double(samples.count) / 100 / 30)
    let r = st.stage(beatTimes: nmBeats.map(\.t), amplitudes: nmBeats.map(\.amp), t0: Double(env["KY_T0"] ?? "0") ?? 0, epochs: n)
    staging = ["stages": r.stages, "probs": r.probabilities, "minutes": r.minutes,
               "features": KYSleepStager.epochFeatures(beats: nmBeats.map(\.t), amps: nmBeats.map(\.amp), n: n, t0: Double(env["KY_T0"] ?? "0") ?? 0).map { $0.map { $0.isNaN ? -999 : $0 } }]
}
var rhythm: [[Double]] = []
if let rp = env["KY_RHYTHM"], let rd = try? Data(contentsOf: URL(fileURLWithPath: rp)), let rm = KYRhythmModel(json: rd) {
    let xs = samples.map(Double.init)
    var s0 = 0
    while s0 + 6000 <= xs.count {
        let wb = nmBeats.filter { $0.t * 100 >= Double(s0) && $0.t * 100 < Double(s0 + 6000) }
        if wb.count >= 20 {
            let f = KYRhythmModel.features(x: Array(xs[s0..<(s0 + 6000)]), beats: wb.map { $0.t * 100 - Double(s0) }, amps: wb.map(\.amp))
            rhythm.append([Double(s0 / 100), rm.predict(f)[1]] + f)
        }
        s0 += 3000
    }
}
var afOut: [String: Any] = [:]
if let mp = env["KY_AF_MODEL"], let md = try? Data(contentsOf: URL(fileURLWithPath: mp)), let am = KYRhythmModel(json: md) {
    let fv = KYRhythmModel.features(x: samples.map(Double.init), beats: nmBeats.map { $0.t * 100 }, amps: nmBeats.map(\.amp))
    afOut = ["features": fv, "probs": am.predict(fv)]
}
let tB = Date()
let nightMetrics: [String: Any] = night.map { KYNightMetrics.compute(beats: nmBeats, asleep: $0.asleep, t0: 0) } ?? [:]
FileHandle.standardError.write("pipeline \(tA.timeIntervalSince(t00)) sleepNight \(tB.timeIntervalSince(tA)) nightMetrics \(Date().timeIntervalSince(tB))\n".data(using: .utf8)!)
let out: [String: Any] = [
    "night": night.map { ["p": $0.probability, "tst": $0.totalSleepMin, "eff": $0.efficiency, "onset": $0.sleepOnsetMin ?? -1] } ?? [:],
    "beats": beats,
    "amps": nmBeats.map { ($0.amp * 10).rounded() / 10 },
    "nightMetrics": nightMetrics,
    "staging": staging,
    "afModel": afOut,
    "rhythm": rhythm,
    "hr": hr,
    "sleepState": sleep.enumerated().filter { $0.offset % 30 == 0 }.map(\.element),
    "epochs": ins.epochLog.map { ["t": $0.t, "f": $0.f, "p": $0.p] },
    "af": ins.afLog.map { ["t": $0.t, "f": $0.f, "af": $0.af] },
    "events": ins.events.map { ["type": $0.type, "start": $0.start, "end": $0.end, "detail": $0.detail] },
]
try JSONSerialization.data(withJSONObject: out).write(to: URL(fileURLWithPath: args[2]))
