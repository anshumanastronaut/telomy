import Foundation

/// Small on-phone store for wellness data (works offline): Documents/wellness/<kind>/<yyyy-MM-dd>.jsonl, one JSON
/// object per line. Kinds used: "minutes" (per-minute band summaries), "profile" (last known age, etc.).
enum KYWellnessStore {
    static var root: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("wellness")
    }
    private static let day: DateFormatter = { let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd"; return f }()

    static func append(kind: String, record: [String: Any]) {
        guard kind.range(of: "^[a-z]+$", options: .regularExpression) != nil,
              let data = try? JSONSerialization.data(withJSONObject: record) else { return }
        let dir = root.appendingPathComponent(kind)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent(day.string(from: Date()) + ".jsonl")
        if !FileManager.default.fileExists(atPath: url.path) { FileManager.default.createFile(atPath: url.path, contents: nil) }
        guard let h = try? FileHandle(forWritingTo: url) else { return }
        _ = try? h.seekToEnd()
        h.write(data); h.write("\n".data(using: .utf8)!)
        try? h.close()
    }

    /// Records from the last `days` day-files (today included), oldest first.
    static func read(kind: String, days: Int) -> [[String: Any]] {
        guard kind.range(of: "^[a-z]+$", options: .regularExpression) != nil else { return [] }
        let dir = root.appendingPathComponent(kind)
        let cal = Calendar.current
        var out: [[String: Any]] = []
        for back in stride(from: max(0, days - 1), through: 0, by: -1) {
            guard let d = cal.date(byAdding: .day, value: -back, to: Date()) else { continue }
            let url = dir.appendingPathComponent(day.string(from: d) + ".jsonl")
            guard let text = try? String(contentsOf: url, encoding: .utf8) else { continue }
            for line in text.split(separator: "\n") {
                if let o = try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any] { out.append(o) }
            }
        }
        return out
    }
}
