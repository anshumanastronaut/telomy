import ActivityKit
import SwiftUI
import WidgetKit

private let ink = Color(red: 0.043, green: 0.071, blue: 0.063)
private let teal = Color(red: 0.36, green: 0.79, blue: 0.65)
private let heartRed = Color(red: 1.0, green: 0.42, blue: 0.34)

private func signalColor(_ s: String) -> Color {
    switch s {
    case "clean": return teal
    case "noisy", "motion": return Color(red: 0.95, green: 0.73, blue: 0.29)
    default: return .gray
    }
}

struct TelomyHeartLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: TelomyHeartAttributes.self) { context in
            // Lock Screen / banner
            HStack(alignment: .center, spacing: 14) {
                Image(systemName: "heart.fill").font(.system(size: 26)).foregroundStyle(heartRed)
                VStack(alignment: .leading, spacing: 2) {
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text(context.state.hr.map(String.init) ?? "–").font(.system(size: 40, weight: .semibold, design: .rounded)).monospacedDigit()
                        Text("bpm").font(.system(size: 14)).foregroundStyle(.secondary)
                    }
                    Text(context.state.subtitle).font(.system(size: 12)).foregroundStyle(.secondary).lineLimit(1)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    Text("HRV").font(.system(size: 10, weight: .semibold)).foregroundStyle(.secondary)
                    Text(context.state.hrv.map { "\($0) ms" } ?? "–").font(.system(size: 18, weight: .semibold, design: .rounded)).monospacedDigit()
                    HStack(spacing: 4) {
                        Circle().fill(signalColor(context.state.signal)).frame(width: 6, height: 6)
                        Text(context.state.signal == "clean" ? "Clean signal" : context.state.signal.replacingOccurrences(of: "_", with: " ").capitalized)
                            .font(.system(size: 10)).foregroundStyle(.secondary)
                    }
                }
            }
            .padding(16)
            .foregroundStyle(.white)
            .activityBackgroundTint(ink)
            .activitySystemActionForegroundColor(teal)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Label { Text(context.state.hr.map(String.init) ?? "–").font(.title2.weight(.semibold)).monospacedDigit() }
                        icon: { Image(systemName: "heart.fill").foregroundStyle(heartRed) }
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(context.state.hrv.map { "HRV \($0) ms" } ?? "HRV –").font(.callout).monospacedDigit()
                }
                DynamicIslandExpandedRegion(.bottom) {
                    Text(context.state.subtitle).font(.caption).foregroundStyle(.secondary)
                }
            } compactLeading: {
                Image(systemName: "heart.fill").foregroundStyle(heartRed)
            } compactTrailing: {
                Text(context.state.hr.map(String.init) ?? "–").monospacedDigit().foregroundStyle(heartRed)
            } minimal: {
                Image(systemName: "heart.fill").foregroundStyle(heartRed)
            }
            .keylineTint(heartRed)
        }
    }
}
