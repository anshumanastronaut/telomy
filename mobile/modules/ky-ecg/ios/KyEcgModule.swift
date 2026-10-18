import ExpoModulesCore

/// Expo bridge for the KY-E-B1 ECG band (see KYBand.swift and docs/devices/KY_E_B1.md).
public class KyEcgModule: Module {
    public func definition() -> ModuleDefinition {
        Name("KyEcg")
        // On-device speech (Cactus): no usage telemetry, no cloud hand-off — nothing about the user's voice leaves the phone.
        OnCreate { setenv("CACTUS_NO_CLOUD_TELE", "1", 1); unsetenv("CACTUS_CLOUD_API_KEY"); unsetenv("CACTUS_CLOUD_KEY") }

        Events("onStatus", "onDevice", "onEcg", "onBeat", "onMetrics", "onRecording", "onRhythm", "onRingStatus", "onRingData", "onRingDevice", "onRingHistory", "onRingSleep")

        OnStartObserving {
            KYBand.shared.emit = { [weak self] name, body in self?.sendEvent(name, body) }
            KYRing.shared.emit = { [weak self] name, body in self?.sendEvent(name, body) }
        }

        OnStopObserving {
            KYBand.shared.emit = nil
            KYRing.shared.emit = nil
        }

        Function("ringStatus") { KYRing.shared.status() }
        Function("ringScan") { KYRing.shared.scan() }
        Function("ringAutoConnect") { KYRing.shared.autoConnect() }
        Function("ringSyncHistory") { KYRing.shared.syncHistory() }
        Function("ringStartRaw") { (ecg: Bool, imu: Bool, ppg: Bool) in KYRing.shared.startRawCapture(ecg: ecg, imu: imu, ppg: ppg) }
        Function("ringStopRaw") { KYRing.shared.stopRawCapture() }
        Function("ringConnect") { (id: String) in KYRing.shared.connect(id: id) }
        Function("ringDisconnect") { KYRing.shared.disconnect() }
        Function("ringForget") { KYRing.shared.forget() }
        Function("ringStartMeasure") { (type: Int) in KYRing.shared.startMeasure(type) }
        Function("ringStopMeasure") { (type: Int) in KYRing.shared.stopMeasure(type) }
        Function("ringReadBattery") { KYRing.shared.readBattery() }
        Function("getStatus") { KYBand.shared.status() }
        Function("startScan") { KYBand.shared.startScan() }
        Function("stopScan") { KYBand.shared.stopScan() }
        Function("connect") { (id: String) in KYBand.shared.connect(id: id) }
        Function("autoConnect") { KYBand.shared.autoConnect() }
        Function("disconnect") { KYBand.shared.disconnect() }
        Function("forget") { KYBand.shared.forget() }
        Function("startStream") { KYBand.shared.startStream() }
        Function("stopStream") { KYBand.shared.stopStream() }
        Function("startRecording") { KYBand.shared.startRecording() }
        Function("stopRecording") { KYBand.shared.stopRecording() }
        Function("syncRecording") { KYBand.shared.syncRecording() }
        Function("log") { (line: String) in KYBand.shared.log("js " + line) }
        Function("startCapture") { (meta: [String: Any]) -> [String: Any] in
            // one tap captures both devices: an overnight patch session also puts the ring in overnight mode
            if isOvernightTherapy(meta["therapyId"]) { KYRing.shared.startOvernight() }
            return KYBand.shared.startCapture(meta: meta)
        }
        Function("ringStartOvernight") { KYRing.shared.startOvernight() }
        Function("autoSleep") { KYSleepAuto.shared.enabled }
        AsyncFunction("phoneActivity") { (hours: Double, promise: Promise) in
            KYSleepAuto.phoneActivity(hours: hours) { promise.resolve($0) }
        }
        Function("setAutoSleep") { (on: Bool) in UserDefaults.standard.set(on, forKey: KYSleepAuto.enabledKey) }
        Function("ringStopOvernight") { KYRing.shared.stopOvernight() }
        AsyncFunction("healthAuthorize") { (promise: Promise) in
            KYHealth.shared.authorize { ok, err in promise.resolve(["ok": ok, "error": err as Any]) }
        }
        AsyncFunction("healthDaily") { (days: Int, promise: Promise) in
            KYHealth.shared.daily(days: days) { promise.resolve($0) }
        }
        AsyncFunction("voiceFeatures") { (path: String, delete: Bool, promise: Promise) in
            DispatchQueue.global(qos: .userInitiated).async { promise.resolve(KYVoice.features(path: path, delete: delete)) }
        }
        AsyncFunction("healthSleep") { (days: Int, promise: Promise) in
            KYHealth.shared.sleepSegments(days: days) { promise.resolve($0) }
        }
        Function("addUserEvent") { (e: [String: Any]) in KYBand.shared.addUserEvent(e) }
        Function("markPhase") { (phase: String, note: String?) in KYBand.shared.markPhase(phase, note: note) }
        Function("updateCapture") { (meta: [String: Any]) in KYBand.shared.updateCapture(meta) }
        Function("stopCapture") { (extra: [String: Any]) -> [String: Any] in
            if isOvernightTherapy(KYBand.shared.captureMeta?["therapyId"]) { KYRing.shared.stopOvernight() }
            return KYBand.shared.stopCapture(extra: extra)
        }
        Function("captureId") { KYBand.shared.captureId }
        Function("captureMeta") { KYBand.shared.captureMeta }
        Function("listCaptures") { KYCapture.list() }
        Function("deleteCapture") { (id: String) in KYCapture.delete(id: id) }
        Function("wellnessAppend") { (kind: String, record: [String: Any]) in KYWellnessStore.append(kind: kind, record: record) }
        AsyncFunction("wellnessRead") { (kind: String, days: Int, promise: Promise) in
            DispatchQueue.global(qos: .userInitiated).async { promise.resolve(KYWellnessStore.read(kind: kind, days: days)) }
        }
        AsyncFunction("reanalyseCapture") { (id: String, promise: Promise) in
            let resting = UserDefaults.standard.double(forKey: "ky.restingHr")
            DispatchQueue.global(qos: .userInitiated).async {
                promise.resolve(KYCapture.reanalyse(id: id, restingHr: resting > 30 ? resting : 65))
            }
        }
    }
}
