import Foundation

/// On-phone therapy session capture (works fully offline).
///
/// Documents/therapy-sessions/<id>/
///   ecg.bin        raw int16 µV @ 100 Hz, little-endian, exactly as received from the band
///   beats.csv      t_unix,rr_ms,amplitude_uv
///   metrics.jsonl  ~1 Hz: HR (adaptive + 10-s), HRV, quality, signal class, activity, motion, …
///   events.jsonl   rhythm / signal events
///   meta.json      therapy, machine settings, phases, ratings, notes, device, timing
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
    }

    func addSamples(_ s: [Int16], frameEndUnix: Double) {
        if firstSampleUnix == nil { firstSampleUnix = frameEndUnix - Double(s.count) / 100; meta["ecgStartUnix"] = firstSampleUnix }
        s.withUnsafeBufferPointer { ecg?.write(Data(buffer: $0)) }
        samples += s.count
    }

    func addBeat(tUnix: Double, rr: Double?, amplitude: Double) {
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
        meta["durationSec"] = Double(samples) / 100
        writeMeta()
        [ecg, beats, metrics, events].forEach { try? $0?.close() }
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
        guard !id.contains("/"), !id.isEmpty else { return }
        try? FileManager.default.removeItem(at: root.appendingPathComponent(id))
    }
}
