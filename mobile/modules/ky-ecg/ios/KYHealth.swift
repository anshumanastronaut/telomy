import Foundation
import HealthKit

/// Read-only Apple Health bridge: daily activity and vitals the iPhone (and a Watch, if paired) already records.
/// Telomy never writes to Health. Types mirror the team app's list (Flutter `health` package) so data lines up.
final class KYHealth {
    static let shared = KYHealth()
    private let store = HKHealthStore()

    private var readTypes: Set<HKObjectType> {
        var s = Set<HKObjectType>()
        let q: [HKQuantityTypeIdentifier] = [.stepCount, .distanceWalkingRunning, .activeEnergyBurned, .appleExerciseTime, .flightsClimbed,
                                             .heartRate, .restingHeartRate, .heartRateVariabilitySDNN, .respiratoryRate, .oxygenSaturation,
                                             .vo2Max, .bodyMass, .bodyFatPercentage, .walkingHeartRateAverage]
        for id in q { if let t = HKObjectType.quantityType(forIdentifier: id) { s.insert(t) } }
        if let sl = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) { s.insert(sl) }
        s.insert(HKObjectType.workoutType())
        return s
    }

    var available: Bool { HKHealthStore.isHealthDataAvailable() }

    func authorize(_ done: @escaping (Bool, String?) -> Void) {
        guard available else { return done(false, "Health data is not available on this device") }
        store.requestAuthorization(toShare: nil, read: readTypes) { ok, err in done(ok, err?.localizedDescription) }
    }

    /// One record per calendar day (oldest first) for the last `days` days.
    func daily(days: Int, _ done: @escaping ([[String: Any]]) -> Void) {
        let cal = Calendar.current
        let end = cal.startOfDay(for: Date()).addingTimeInterval(86400)
        let start = cal.date(byAdding: .day, value: -days, to: end)!
        var out: [String: [String: Any]] = [:]
        let df = DateFormatter(); df.dateFormat = "yyyy-MM-dd"
        let group = DispatchGroup()
        let lock = NSLock()
        func put(_ day: Date, _ k: String, _ v: Any) { lock.lock(); out[df.string(from: day), default: ["date": df.string(from: day)]][k] = v; lock.unlock() }

        func collect(_ id: HKQuantityTypeIdentifier, _ key: String, _ unit: HKUnit, _ opt: HKStatisticsOptions, scale: Double = 1) {
            guard let t = HKQuantityType.quantityType(forIdentifier: id) else { return }
            group.enter()
            let q = HKStatisticsCollectionQuery(quantityType: t, quantitySamplePredicate: HKQuery.predicateForSamples(withStart: start, end: end),
                                                options: opt, anchorDate: start, intervalComponents: DateComponents(day: 1))
            q.initialResultsHandler = { _, res, _ in
                res?.enumerateStatistics(from: start, to: end) { st, _ in
                    let qty = opt.contains(.cumulativeSum) ? st.sumQuantity() : st.averageQuantity()
                    if let v = qty?.doubleValue(for: unit) { put(st.startDate, key, (v * scale * 10).rounded() / 10) }
                }
                group.leave()
            }
            store.execute(q)
        }
        collect(.stepCount, "steps", .count(), .cumulativeSum)
        collect(.distanceWalkingRunning, "distanceKm", .meterUnit(with: .kilo), .cumulativeSum)
        collect(.activeEnergyBurned, "activeKcal", .kilocalorie(), .cumulativeSum)
        collect(.appleExerciseTime, "exerciseMin", .minute(), .cumulativeSum)
        collect(.flightsClimbed, "flights", .count(), .cumulativeSum)
        collect(.restingHeartRate, "restingHr", .count().unitDivided(by: .minute()), .discreteAverage)
        collect(.walkingHeartRateAverage, "walkingHr", .count().unitDivided(by: .minute()), .discreteAverage)
        collect(.heartRateVariabilitySDNN, "hrvSdnn", .secondUnit(with: .milli), .discreteAverage)
        collect(.respiratoryRate, "respRate", .count().unitDivided(by: .minute()), .discreteAverage)
        collect(.oxygenSaturation, "spo2", .percent(), .discreteAverage, scale: 100)
        collect(.vo2Max, "vo2max", HKUnit(from: "ml/kg*min"), .discreteAverage)
        collect(.bodyMass, "weightKg", .gramUnit(with: .kilo), .discreteAverage)
        collect(.bodyFatPercentage, "bodyFatPct", .percent(), .discreteAverage, scale: 100)

        // sleep (asleep minutes per wake-up day) from any source (Watch, iPhone sleep schedule, other apps)
        if let sl = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) {
            group.enter()
            let q = HKSampleQuery(sampleType: sl, predicate: HKQuery.predicateForSamples(withStart: start.addingTimeInterval(-43200), end: end),
                                  limit: HKObjectQueryNoLimit, sortDescriptors: nil) { _, samples, _ in
                var mins: [Date: Double] = [:]
                for s in (samples as? [HKCategorySample]) ?? [] {
                    let v = HKCategoryValueSleepAnalysis(rawValue: s.value)
                    let asleep: Bool
                    if #available(iOS 16.0, *) { asleep = v != .inBed && v != .awake } else { asleep = v == .asleep }
                    guard asleep else { continue }
                    mins[cal.startOfDay(for: s.endDate), default: 0] += s.endDate.timeIntervalSince(s.startDate) / 60
                }
                for (d, m) in mins { put(d, "sleepMin", m.rounded()) }
                group.leave()
            }
            store.execute(q)
        }
        // workouts
        group.enter()
        let wq = HKSampleQuery(sampleType: .workoutType(), predicate: HKQuery.predicateForSamples(withStart: start, end: end), limit: 200,
                               sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)]) { _, samples, _ in
            var byDay: [Date: [[String: Any]]] = [:]
            for w in (samples as? [HKWorkout]) ?? [] {
                var rec: [String: Any] = ["type": w.workoutActivityType.rawValue, "min": (w.duration / 60).rounded(),
                                          "start": w.startDate.timeIntervalSince1970, "end": w.endDate.timeIntervalSince1970,
                                          "source": w.sourceRevision.source.name]
                if let e = w.totalEnergyBurned?.doubleValue(for: .kilocalorie()) { rec["kcal"] = e.rounded() }
                if let d = w.totalDistance?.doubleValue(for: .meterUnit(with: .kilo)) { rec["km"] = (d * 100).rounded() / 100 }
                byDay[cal.startOfDay(for: w.startDate), default: []].append(rec)
            }
            for (d, ws) in byDay { put(d, "workouts", ws) }
            group.leave()
        }
        store.execute(wq)
        group.notify(queue: .global()) { done(out.values.sorted { ($0["date"] as! String) < ($1["date"] as! String) }) }
    }

    /// Raw sleep segments (oldest first) for the last `days` nights from every source. Stage codes:
    /// 0 awake, 1 core/light, 2 deep, 3 REM, 4 asleep (unstaged), 5 in bed. Apple Watch writes staged segments
    /// (iOS 16+); iPhone/other apps usually write in-bed or unstaged asleep.
    func sleepSegments(days: Int, _ done: @escaping ([[String: Any]]) -> Void) {
        guard let sl = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) else { return done([]) }
        let start = Date().addingTimeInterval(-Double(days) * 86400 - 43200)
        let q = HKSampleQuery(sampleType: sl, predicate: HKQuery.predicateForSamples(withStart: start, end: Date()), limit: HKObjectQueryNoLimit,
                              sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)]) { _, samples, _ in
            var out: [[String: Any]] = []
            for s in (samples as? [HKCategorySample]) ?? [] {
                var st = 4
                if #available(iOS 16.0, *) {
                    switch HKCategoryValueSleepAnalysis(rawValue: s.value) {
                    case .awake: st = 0
                    case .asleepCore: st = 1
                    case .asleepDeep: st = 2
                    case .asleepREM: st = 3
                    case .inBed: st = 5
                    default: st = 4
                    }
                } else { st = s.value == HKCategoryValueSleepAnalysis.inBed.rawValue ? 5 : s.value == 2 ? 0 : 4 }
                let src = s.sourceRevision.source
                out.append(["start": s.startDate.timeIntervalSince1970, "end": s.endDate.timeIntervalSince1970, "stage": st,
                            "source": src.name, "watch": (s.device?.model ?? "").lowercased().contains("watch")
                                || src.bundleIdentifier.lowercased().contains("watch")])
            }
            done(out)
        }
        store.execute(q)
    }
}
