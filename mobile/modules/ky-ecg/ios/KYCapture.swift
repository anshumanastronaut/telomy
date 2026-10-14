import Foundation

/// On-phone therapy session capture (works fully offline).
///
/// Documents/therapy-sessions/<id>/
///   ecg.bin        raw int16 µV @ 100 Hz, little-endian, exactly as received from the band
///   beats.csv      t_unix,rr_ms,amplitude_uv
///   metrics.jsonl  ~1 Hz: HR (adaptive + 10-s), HRV, quality, signal class, activity, motion, …
///   events.jsonl   rhythm / signal events
///   meta.json      therapy, machine settings, phases, ratings, notes, device, timing, segments
/// ECG sample i belongs to the last segment with sample <= i, at unix + (i - sample) / 100. A new segment starts after any
/// gap (band out of range, app relaunched). The active session survives app termination and resumes on relaunch.
/// On stop, everything is bundled into <id>.telomy.json (format "telomy.capture/1") for sharing.
final class KYCapture {
    let id: String
    let dir: URL
    private(set) var meta: [String: Any]
    private var ecg: FileHandle?, beats: FileHandle?, metrics: FileHandle?, events: FileHandle?
    private var phases: [[String: Any]] = []
    private var firstSampleUnix: Double?
    private var samples = 0
    private var lastMetricAt = 0.0
    private var segments: [[String: Any]] = []
    private var lastMetaWrite = 0.0
    private(set) var beatTimes: [Double] = []   // unix seconds, for whole-night sleep analysis
    static let activeKey = "telomy.capture.active"
    static var activeId: String? { UserDefaults.standard.string(forKey: activeKey) }

    static var root: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("therapy-sessions")
    }

    init(meta: [String: Any]) throws {
        let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"
        id = "\(f.string(from: Date()))-\((meta["therapy"] as? String ?? "session").lowercased().replacingOccurrences(of: " ", with: "_"))"
        dir = Self.root.appendingPathComponent(id)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        self.meta = meta
        self.meta["id"] = id
        self.meta["format"] = "telomy.capture/1"
        self.meta["startedAt"] = Date().timeIntervalSince1970
        func open(_ name: String, header: String? = nil) -> FileHandle? {
            let url = dir.appendingPathComponent(name)
            FileManager.default.createFile(atPath: url.path, contents: header?.data(using: .utf8))
            return try? FileHandle(forWritingTo: url)
        }
        ecg = open("ecg.bin"); beats = open("beats.csv", header: "t_unix,rr_ms,amplitude_uv\n")
        metrics = open("metrics.jsonl"); events = open("events.jsonl")
        _ = try? beats?.seekToEnd()
        mark(phase: (meta["firstPhase"] as? String) ?? "baseline")
        writeMeta()
        UserDefaults.standard.set(id, forKey: Self.activeKey)
    }

    /// Re-open an unfinished session after the app was terminated (e.g. overnight).
    init(resume id: String) throws {
        guard !id.contains("/") else { throw CocoaError(.fileNoSuchFile) }
        self.id = id
        dir = Self.root.appendingPathComponent(id)
        let d = try Data(contentsOf: dir.appendingPathComponent("meta.json"))
        guard let m = try JSONSerialization.jsonObject(with: d) as? [String: Any] else { throw CocoaError(.fileReadCorruptFile) }
        meta = m
        phases = m["phases"] as? [[String: Any]] ?? []
        segments = m["segments"] as? [[String: Any]] ?? []
        firstSampleUnix = m["ecgStartUnix"] as? Double
        func open(_ name: String) -> FileHandle? {
            let h = try? FileHandle(forWritingTo: dir.appendingPathComponent(name)); _ = try? h?.seekToEnd(); return h
        }
        ecg = open("ecg.bin"); beats = open("beats.csv"); metrics = open("metrics.jsonl"); events = open("events.jsonl")
        let size = (try? FileManager.default.attributesOfItem(atPath: dir.appendingPathComponent("ecg.bin").path)[.size] as? Int) ?? 0
        samples = size / 2
        let csv = (try? String(contentsOf: dir.appendingPathComponent("beats.csv"), encoding: .utf8)) ?? ""
        beatTimes = csv.split(separator: "\n").dropFirst().compactMap { Double($0.split(separator: ",").first ?? "") }
        meta["resumes"] = ((meta["resumes"] as? Int) ?? 0) + 1
        mark(phase: "marker", note: "app relaunched, recording resumed")
    }

    func addSamples(_ s: [Int16], frameEndUnix: Double) {
        let start = frameEndUnix - Double(s.count) / 100
        if firstSampleUnix == nil { firstSampleUnix = start; meta["ecgStartUnix"] = start }
        // new segment at the start and after any gap > 2 s between the sample clock and the wall clock
        let expected = (segments.last?["unix"] as? Double).map { $0 + Double(samples - (segments.last?["sample"] as? Int ?? 0)) / 100 }
        if expected == nil || abs(start - expected!) > 2 {
            segments.append(["sample": samples, "unix": start]); meta["segments"] = segments; writeMeta()
        }
        if frameEndUnix - lastMetaWrite > 60 { lastMetaWrite = frameEndUnix; writeMeta() }  // keep sample count current
        s.withUnsafeBufferPointer { ecg?.write(Data(buffer: $0)) }
        samples += s.count
    }

    func addBeat(tUnix: Double, rr: Double?, amplitude: Double) {
        beatTimes.append(tUnix)
        beats?.write(String(format: "%.3f,%@,%.0f\n", tUnix, rr.map { String(format: "%.1f", $0) } ?? "", amplitude).data(using: .utf8)!)
    }

    func addMetrics(_ m: [String: Any]) {
        guard let t = m["t"] as? Double, t - lastMetricAt >= 0.9 else { return }
        lastMetricAt = t
        if let d = try? JSONSerialization.data(withJSONObject: m) { metrics?.write(d); metrics?.write("\n".data(using: .utf8)!) }
    }

    func addEvent(_ e: [String: Any]) {
        if let d = try? JSONSerialization.data(withJSONObject: e) { events?.write(d); events?.write("\n".data(using: .utf8)!) }
    }

    func mark(phase: String, note: String? = nil) {
        var p: [String: Any] = ["phase": phase, "t": Date().timeIntervalSince1970]
        if let note { p["note"] = note }
        phases.append(p)
        meta["phases"] = phases
        writeMeta()
    }

    /// Free-form user event (meal, supplement, caffeine, alcohol, smoking, custom…) with its own time, kept in
    /// meta.userEvents so the team can line it up with the ECG.
    func addUserEvent(_ e: [String: Any]) {
        var list = meta["userEvents"] as? [[String: Any]] ?? []
        list.append(e)
        meta["userEvents"] = list.sorted { ($0["t"] as? Double ?? 0) < ($1["t"] as? Double ?? 0) }
        writeMeta()
    }

    func update(meta extra: [String: Any]) { for (k, v) in extra { meta[k] = v }; writeMeta() }

    private func writeMeta() {
        meta["samples"] = samples
        if let d = try? JSONSerialization.data(withJSONObject: meta, options: [.prettyPrinted, .sortedKeys]) {
            try? d.write(to: dir.appendingPathComponent("meta.json"))
        }
    }

    /// Close files and write the shareable bundle. Returns its path.
    func finish(extra: [String: Any]) -> URL {
        update(meta: extra)
        meta["endedAt"] = Date().timeIntervalSince1970
        meta["durationSec"] = Double(samples) / 100          // recorded ECG
        meta["wallSec"] = (meta["endedAt"] as! Double) - ((meta["startedAt"] as? Double) ?? 0)  // including gaps
        writeMeta()
        [ecg, beats, metrics, events].forEach { try? $0?.close() }
        if Self.activeId == id { UserDefaults.standard.removeObject(forKey: Self.activeKey) }
        return Self.bundle(dir: dir)
    }

    static func bundle(dir: URL) -> URL {
        let fm = FileManager.default
        func text(_ n: String) -> String { (try? String(contentsOf: dir.appendingPathComponent(n), encoding: .utf8)) ?? "" }
        let meta = (try? JSONSerialization.jsonObject(with: Data(contentsOf: dir.appendingPathComponent("meta.json")))) ?? [:]
        let raw = (try? Data(contentsOf: dir.appendingPathComponent("ecg.bin"))) ?? Data()
        let jsonl = { (n: String) -> [Any] in text(n).split(separator: "\n").compactMap { try? JSONSerialization.jsonObject(with: Data($0.utf8)) } }
        let bundle: [String: Any] = [
            "format": "telomy.capture/1",
            "meta": meta,
            "ecg": ["fs": 100, "unit": "uV", "dtype": "int16le", "encoding": "base64", "data": raw.base64EncodedString()],
            "beats_csv": text("beats.csv"),
            "metrics": jsonl("metrics.jsonl"),
            "events": jsonl("events.jsonl"),
        ]
        let url = dir.appendingPathComponent("\(dir.lastPathComponent).telomy.json")
        if let d = try? JSONSerialization.data(withJSONObject: bundle) { try? d.write(to: url) }
        _ = fm
        return url
    }

    /// After a band-memory recording is synced, put its ECG, beats and night analysis into the overnight capture that
    /// started it, so the team gets one file. Returns the capture id, or nil if no matching session.
    static func attachRecording(payload: [String: Any], holterURL: URL) -> String? {
        guard let start = payload["start"] as? Double, let frames = try? KYHolterFile.frames(at: holterURL), !frames.isEmpty else { return nil }
        let fm = FileManager.default
        guard let ids = try? fm.contentsOfDirectory(atPath: root.path) else { return nil }
        for id in ids.sorted(by: >) where id != activeId {
            let dir = root.appendingPathComponent(id)
            guard let d = try? Data(contentsOf: dir.appendingPathComponent("meta.json")),
                  var meta = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
                  meta["therapyId"] as? String == "sleep", let t0 = meta["startedAt"] as? Double, abs(t0 - start) < 600 else { continue }
            // only when the band memory holds clearly more ECG than the live stream did (never overwrite with less)
            let liveBytes = (try? fm.attributesOfItem(atPath: dir.appendingPathComponent("ecg.bin").path)[.size] as? Int) ?? 0
            let memSamples = frames.reduce(0) { $0 + $1.samples.count }
            guard memSamples > liveBytes / 2 + 6000 else { continue }
            if fm.fileExists(atPath: dir.appendingPathComponent("ecg.bin").path) {
                try? fm.moveItem(at: dir.appendingPathComponent("ecg.bin"), to: dir.appendingPathComponent("ecg-live.bin"))
            }
            var raw = Data()
            for f in frames { f.samples.withUnsafeBufferPointer { raw.append(Data(buffer: $0)) } }
            try? raw.write(to: dir.appendingPathComponent("ecg.bin"))
            let n = raw.count / 2
            let times = payload["beatTimes"] as? [Double] ?? []
            var csv = "t_unix,rr_ms,amplitude_uv\n"
            for (i, t) in times.enumerated() {
                csv += String(format: "%.3f,%@,\n", t, i > 0 ? String(format: "%.1f", (t - times[i - 1]) * 1000) : "")
            }
            try? csv.data(using: .utf8)?.write(to: dir.appendingPathComponent("beats-memory.csv"))
            if fm.fileExists(atPath: dir.appendingPathComponent("beats.csv").path) {
                try? fm.removeItem(at: dir.appendingPathComponent("beats-live.csv"))
                try? fm.moveItem(at: dir.appendingPathComponent("beats.csv"), to: dir.appendingPathComponent("beats-live.csv"))
            }
            try? fm.moveItem(at: dir.appendingPathComponent("beats-memory.csv"), to: dir.appendingPathComponent("beats.csv"))
            meta["ecgSource"] = "band memory (synced)"
            meta["ecgStartUnix"] = start
            meta["segments"] = [["sample": 0, "unix": start]]
            meta["samples"] = n
            meta["durationSec"] = Double(n) / 100
            var summary = meta["summary"] as? [String: Any] ?? [:]
            for k in ["sleep", "events", "meanHr", "rmssd", "sdnn", "artefactPercent", "beats"] { if let v = payload[k] { summary[k] = v } }
            meta["summary"] = summary
            if let d = try? JSONSerialization.data(withJSONObject: meta, options: [.prettyPrinted, .sortedKeys]) {
                try? d.write(to: dir.appendingPathComponent("meta.json"))
            }
            _ = bundle(dir: dir)
            return id
        }
        return nil
    }

    static let analysisVersion = "2026-10-14c (4-stage sleep, gaps = no data)"

    /// Re-run the current analysis over a saved session's raw ECG (each gap-free segment separately, as live) and rewrite
    /// beats.csv, the summary (beats, HR/HRV, rhythm events, whole-night sleep) and the export bundle. The original live
    /// beats are kept as beats-live.csv. Slow for a whole night (~10–20 s on a phone): call off the main thread.
    static func reanalyse(id: String, restingHr: Double) -> [String: Any] {
        guard !id.contains("/"), id != activeId else { return ["error": "This session is still recording"] }
        let fm = FileManager.default
        let dir = root.appendingPathComponent(id)
        guard let d = try? Data(contentsOf: dir.appendingPathComponent("meta.json")),
              var meta = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
              let raw = try? Data(contentsOf: dir.appendingPathComponent("ecg.bin")), raw.count > 2000 else {
            return ["error": "No ECG in this session"]
        }
        let samples: [Int16] = raw.withUnsafeBytes { Array($0.bindMemory(to: Int16.self)) }
        let t0 = meta["startedAt"] as? Double ?? 0
        var segs = (meta["segments"] as? [[String: Any]] ?? []).compactMap { s -> (Int, Double)? in
            guard let i = s["sample"] as? Int, let u = s["unix"] as? Double else { return nil }; return (i, u)
        }
        if segs.isEmpty { segs = [(0, meta["ecgStartUnix"] as? Double ?? t0)] }
        var beatRows: [(t: Double, rr: Double?, amp: Double)] = []
        var events: [[String: Any]] = []
        var rrAll: [Double] = []
        for (k, seg) in segs.enumerated() {
            let end = k + 1 < segs.count ? segs[k + 1].0 : samples.count
            guard end - seg.0 > 300 else { continue }
            let a = KYAnalyzer(sampleRate: 100)
            let ins = KYInsight(sampleRate: 100, restingHr: restingHr)
            var i = seg.0
            while i < end {
                let chunk = Array(samples[i..<min(i + 87, end)])
                let out = a.process(chunk)
                for b in out.beats {
                    beatRows.append((seg.1 + b.sample / 100, b.rrMs, b.amplitude))
                    if let r = b.rrMs { rrAll.append(r) }
                }
                ins.process(samples: chunk, beats: out.beats, leadOn: true, quality: a.currentQuality)
                i += chunk.count
            }
            events += ins.events.map { ["type": $0.type, "start": seg.1 + $0.start, "end": seg.1 + $0.end, "detail": $0.detail] }
        }
        var csv = "t_unix,rr_ms,amplitude_uv\n"
        for b in beatRows { csv += String(format: "%.3f,%@,%.0f\n", b.t, b.rr.map { String(format: "%.1f", $0) } ?? "", b.amp) }
        let beatsURL = dir.appendingPathComponent("beats.csv"), liveURL = dir.appendingPathComponent("beats-live.csv")
        if !fm.fileExists(atPath: liveURL.path) { try? fm.moveItem(at: beatsURL, to: liveURL) }
        try? csv.data(using: .utf8)?.write(to: beatsURL)

        var summary = meta["summary"] as? [String: Any] ?? [:]
        summary["beats"] = beatRows.count
        summary["events"] = events
        let c = KYArtefacts.correct(rrAll)
        if !c.nn.isEmpty { summary["meanHr"] = 60000 / (c.nn.reduce(0, +) / Double(c.nn.count)) }
        if let v = KYHRV.rmssd(c.nn) { summary["rmssd"] = v }
        if let v = KYHRV.sdnn(c.nn) { summary["sdnn"] = v }
        summary["artefactPercent"] = c.artefactPercent
        // sleep epochs start where the ECG starts (minutes before the first sample have no data)
        let tS = segs.first?.1 ?? t0
        let wall = (meta["endedAt"] as? Double ?? (beatRows.last?.t ?? tS)) - tS
        summary["sleep"] = nil
        if wall > 2 * 3600, let n = KYSleepNight.analyze(beats: beatRows.map { $0.t - tS }, durationSec: wall) {
            var sl: [String: Any] = ["totalSleepMin": n.totalSleepMin, "efficiency": n.efficiency, "wasoMin": n.wakeAfterOnsetMin,
                                     "awakenings": n.awakenings, "hypnogram": n.asleep.map { $0 ? 1 : 0 }, "epochSec": 30, "t0": tS]
            if let v = n.sleepOnsetMin { sl["onsetMin"] = v }
            if let v = n.sleepHr { sl["sleepHr"] = v }
            if let v = n.sleepRmssd { sl["sleepRmssd"] = v }
            var asleep = n.asleep
            // 4-stage model (Wake/Light/Deep/REM) when the weights are bundled: it replaces the sleep/wake estimate
            if let st = KYSleepStager.shared {
                let r = st.stage(beatTimes: beatRows.map(\.t), amplitudes: beatRows.map(\.amp), t0: tS, epochs: Int(wall / 30))
                let ss = KYSleepStager.summarize(r.stages)
                if (ss["totalSleepMin"] as? Double ?? 0) > 60 {
                    for (k, v) in ss { sl[k] = v }
                    sl["stages"] = r.stages
                    sl["hypnogram"] = r.stages.map { $0 > 0 ? 1 : 0 }
                    sl["model"] = "stager-v2 (HMC 151 nights, ECG-only)"
                    asleep = r.stages.map { $0 > 0 }
                }
            }
            summary["sleep"] = sl
            summary["night"] = KYNightMetrics.compute(beats: beatRows.map { KYNightMetrics.Beat(t: $0.t, rr: $0.rr, amp: $0.amp) },
                                                      asleep: asleep, t0: tS)
        }
        meta["summary"] = summary
        meta["analysis"] = ["version": analysisVersion, "at": Date().timeIntervalSince1970, "source": "reanalysed on phone"]
        if let d = try? JSONSerialization.data(withJSONObject: meta, options: [.prettyPrinted, .sortedKeys]) {
            try? d.write(to: dir.appendingPathComponent("meta.json"))
        }
        _ = bundle(dir: dir)
        return ["id": id, "summary": summary]
    }

    static func list() -> [[String: Any]] {
        let fm = FileManager.default
        guard let ids = try? fm.contentsOfDirectory(atPath: root.path) else { return [] }
        return ids.sorted(by: >).compactMap { id in
            let dir = root.appendingPathComponent(id)
            guard let d = try? Data(contentsOf: dir.appendingPathComponent("meta.json")),
                  var m = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any] else { return nil }
            let b = dir.appendingPathComponent("\(id).telomy.json")
            m["bundlePath"] = fm.fileExists(atPath: b.path) ? b.path : nil
            m["bundleBytes"] = (try? fm.attributesOfItem(atPath: b.path)[.size] as? Int) ?? 0
            return m
        }
    }

    static func delete(id: String) {
        guard !id.contains("/"), !id.isEmpty, id != activeId else { return }
        try? FileManager.default.removeItem(at: root.appendingPathComponent(id))
    }
}
