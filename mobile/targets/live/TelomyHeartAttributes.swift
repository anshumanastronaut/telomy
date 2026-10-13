import ActivityKit
import Foundation

// Keep identical to mobile/modules/ky-ecg/ios/KYLiveActivity.swift (ActivityKit matches the type by name and shape).
struct TelomyHeartAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var hr: Int?
        var hrv: Int?
        var signal: String      // clean, noisy, motion, no_contact …
        var subtitle: String    // e.g. "Overnight sleep · 2:14" or "Live heart"
        var updatedAt: Date
    }
    var title: String
    var startedAt: Date
}
