import ActivityKit
import Foundation

// Keep identical to mobile/targets/live/TelomyHeartAttributes.swift (ActivityKit matches the type by name and shape).
struct TelomyHeartAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var hr: Int?
        var hrv: Int?
        var signal: String
        var subtitle: String
        var updatedAt: Date
    }
    var title: String
    var startedAt: Date
}

/// Live heart rate on the Lock Screen / Dynamic Island while the band streams. Updated locally (no push) at most every
/// 5 s; the band's Bluetooth background mode keeps the app running so updates continue with the screen locked.
final class KYLiveActivity {
    static let shared = KYLiveActivity()
    private var activity: Any?
    private var lastUpdate = Date.distantPast
    private var startedAt = Date()

    var isRunning: Bool { activity != nil }

    func start(title: String = "Live heart") {
        guard #available(iOS 16.2, *), activity == nil, ActivityAuthorizationInfo().areActivitiesEnabled else { return }
        startedAt = Date()
        let state = TelomyHeartAttributes.ContentState(hr: nil, hrv: nil, signal: "warming_up", subtitle: "Connecting…", updatedAt: Date())
        activity = try? Activity.request(attributes: TelomyHeartAttributes(title: title, startedAt: startedAt),
                                         content: ActivityContent(state: state, staleDate: Date().addingTimeInterval(120)))
    }

    func update(hr: Double?, hrv: Double?, signal: String, subtitle: String) {
        guard #available(iOS 16.2, *), let a = activity as? Activity<TelomyHeartAttributes>, Date().timeIntervalSince(lastUpdate) >= 5 else { return }
        lastUpdate = Date()
        let state = TelomyHeartAttributes.ContentState(hr: hr.map { Int($0.rounded()) }, hrv: hrv.map { Int($0.rounded()) },
                                                      signal: signal, subtitle: subtitle, updatedAt: Date())
        Task { await a.update(ActivityContent(state: state, staleDate: Date().addingTimeInterval(120))) }
    }

    func end() {
        guard #available(iOS 16.2, *), let a = activity as? Activity<TelomyHeartAttributes> else { return }
        activity = nil
        Task { await a.end(nil, dismissalPolicy: .immediate) }
    }

    var elapsed: String {
        let s = Int(Date().timeIntervalSince(startedAt)); return s >= 3600 ? String(format: "%d:%02d h", s / 3600, (s % 3600) / 60) : "\(s / 60) min"
    }
}
