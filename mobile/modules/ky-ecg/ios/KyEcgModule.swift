import ExpoModulesCore

/// Expo bridge for the KY-E-B1 ECG band (see KYBand.swift and docs/devices/KY_E_B1.md).
public class KyEcgModule: Module {
    public func definition() -> ModuleDefinition {
        Name("KyEcg")

        Events("onStatus", "onDevice", "onEcg", "onBeat", "onMetrics", "onRecording", "onRhythm")

        OnStartObserving {
            KYBand.shared.emit = { [weak self] name, body in self?.sendEvent(name, body) }
        }

        OnStopObserving {
            KYBand.shared.emit = nil
        }

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
        Function("startCapture") { (meta: [String: Any]) in KYBand.shared.startCapture(meta: meta) }
        Function("addUserEvent") { (e: [String: Any]) in KYBand.shared.addUserEvent(e) }
        Function("markPhase") { (phase: String, note: String?) in KYBand.shared.markPhase(phase, note: note) }
        Function("updateCapture") { (meta: [String: Any]) in KYBand.shared.updateCapture(meta) }
        Function("stopCapture") { (extra: [String: Any]) in KYBand.shared.stopCapture(extra: extra) }
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
