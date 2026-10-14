import CoreBluetooth
import Foundation

/// Connection manager for the KY-E-B1 ECG band.
///
/// "Seamless" behaviour:
/// - Remembers the last band (UserDefaults) and reconnects automatically: `connect` on iOS has no timeout, so a pending
///   connection completes as soon as the band is worn (it powers on when the electrodes touch skin).
/// - Re-connects after drops unless the user disconnected; restores state when iOS relaunches the app in the background
///   (bluetooth-central background mode + restore identifier).
/// - Streams ECG whenever `wantsStream` is true, re-arming the band's timed stream every 50 min and polling battery/contact.
/// Firmware update is intentionally not implemented.
final class KYBand: NSObject {
    static let shared = KYBand()

    static let serviceUUID = CBUUID(string: "DE5BF728-D711-4E47-AF26-65E3012A5DC7")
    static let notifyUUID = CBUUID(string: "DE5BF729-D711-4E47-AF26-65E3012A5DC7")
    static let writeUUID = CBUUID(string: "DE5BF72A-D711-4E47-AF26-65E3012A5DC7")
    private static let rememberKey = "ky.band.id"
    private static let rememberNameKey = "ky.band.name"
    private static let sampleRate = 100.0

    enum State: String { case unsupported, off, unauthorized, idle, scanning, connecting, connected, streaming }

    var emit: ((String, [String: Any]) -> Void)?

    private var central: CBCentralManager!
    private var peripheral: CBPeripheral?
    private var tx: CBCharacteristic?
    private var decoder = KYPacketDecoder()
    private var analyzer = KYAnalyzer(sampleRate: KYBand.sampleRate)
    private var insight = KYBand.makeInsight()
    private static let restingKey = "ky.restingHr"
    private static func makeInsight() -> KYInsight {
        let rest = UserDefaults.standard.double(forKey: restingKey)
        return KYInsight(sampleRate: sampleRate, restingHr: rest > 30 ? rest : 65)
    }
    private var probedAcc = false
    private var capture: KYCapture?
    private var restingSavedAt = 0.0
    private var state: State = .idle
    private var userDisconnected = false
    private(set) var wantsStream = false
    private var found: [UUID: CBPeripheral] = [:]
    private var info: KYDeviceInfo?
    private var leadOn: Bool?
    private var holterState: KYHolterState = .unknown
    private var holterStart: UInt32?
    private var sync: KYHolterSync?
    private var keepAlive: Timer?
    private var streamStartedAt: Date?
    private var firstSampleTime: Double?     // unix time of analyzer sample 0
    private var samplesIn = 0
    private var lastFrameIndex: Int?
    private var droppedFrames = 0
    private var lastError: String?
    private var lastFrameAt = 0.0
    private var liveBlockedByRecording = false
    private var awaitingHolterState = false
    private var lastPauseSent = 0.0
    /// Diagnostic log (Documents/ky-debug/*.log): raw frames, beats, metrics, status. Pulled over USB/Wi-Fi with devicectl.
    private var debug: FileHandle?
    private var debugDay = ""

    private override init() {
        super.init()
        central = CBCentralManager(delegate: self, queue: .main, options: [
            CBCentralManagerOptionRestoreIdentifierKey: "telomy.ky.band",
            CBCentralManagerOptionShowPowerAlertKey: true,
        ])
        if let id = KYCapture.activeId {  // an overnight/therapy session was running when iOS terminated the app
            capture = try? KYCapture(resume: id)
            if capture != nil { wantsStream = true; log("capture resumed \(id)") } else { UserDefaults.standard.removeObject(forKey: KYCapture.activeKey) }
        }
    }

    // MARK: public API (main queue)

    var rememberedId: String? { UserDefaults.standard.string(forKey: Self.rememberKey) }

    func status() -> [String: Any] {
        var s: [String: Any] = ["state": state.rawValue, "wantsStream": wantsStream, "droppedFrames": droppedFrames,
                                "holterState": "\(holterState)"]
        if let id = rememberedId { s["rememberedId"] = id; s["rememberedName"] = UserDefaults.standard.string(forKey: Self.rememberNameKey) ?? "ECG band" }
        if let p = peripheral { s["deviceId"] = p.identifier.uuidString; s["deviceName"] = p.name ?? "ECG band" }
        if let i = info { s["battery"] = i.battery; s["hardware"] = i.hardwareVersion; s["firmware"] = i.firmwareVersion }
        if let l = leadOn { s["leadOn"] = l }
        if let t = holterStart { s["holterStart"] = Double(t) }
        if let e = lastError { s["error"] = e }
        s["sampleRate"] = Self.sampleRate
        s["liveBlockedByRecording"] = liveBlockedByRecording
        return s
    }

    func startScan() {
        guard central.state == .poweredOn else { publish(); return }
        found = [:]
        central.scanForPeripherals(withServices: nil, options: [CBCentralManagerScanOptionAllowDuplicatesKey: false])
        set(.scanning)
        DispatchQueue.main.asyncAfter(deadline: .now() + 20) { [weak self] in
            guard let self, self.state == .scanning else { return }
            self.central.stopScan(); self.set(self.peripheral == nil ? .idle : self.state)
        }
    }

    func stopScan() { central.stopScan(); if state == .scanning { set(.idle) } }

    func connect(id: String) {
        guard let uuid = UUID(uuidString: id) else { return }
        central.stopScan()
        let p = found[uuid] ?? central.retrievePeripherals(withIdentifiers: [uuid]).first
        guard let p else { lastError = "Band not found. Put it on and scan again."; publish(); return }
        UserDefaults.standard.set(id, forKey: Self.rememberKey)
        UserDefaults.standard.set(p.name ?? "ECG band", forKey: Self.rememberNameKey)
        attach(p)
    }

    /// Reconnect to the remembered band (pending until it is in range and worn).
    func autoConnect() {
        guard central.state == .poweredOn, peripheral == nil || peripheral?.state == .disconnected,
              let id = rememberedId, let uuid = UUID(uuidString: id),
              let p = central.retrievePeripherals(withIdentifiers: [uuid]).first else { return }
        attach(p)
    }

    func disconnect() {
        userDisconnected = true
        wantsStream = false
        KYLiveActivity.shared.end()
        if let p = peripheral { central.cancelPeripheralConnection(p) }
    }

    func forget() {
        disconnect()
        UserDefaults.standard.removeObject(forKey: Self.rememberKey)
        UserDefaults.standard.removeObject(forKey: Self.rememberNameKey)
        peripheral = nil
        set(.idle)
    }

    func startStream() {
        wantsStream = true
        if liveBlockedByRecording || awaitingHolterState { publish(); return }  // band is recording to memory: stay paused
        if tx != nil { beginStream() } else { autoConnect() }
        publish()
    }

    func stopStream() {
        guard capture == nil else { return }  // a therapy capture keeps the stream alive until it is stopped
        wantsStream = false
        KYLiveActivity.shared.end()
        send(KYRequest.ecg(start: false, durationSec: 0))
        streamStartedAt = nil
        if state == .streaming { set(.connected) }
    }

    // MARK: therapy capture (offline, on the phone)

    func startCapture(meta: [String: Any]) -> [String: Any] {
        if let c = capture { return ["id": c.id, "error": "A session is already being captured"] }
        do {
            var m = meta
            m["device"] = ["name": peripheral?.name ?? "ECG band", "hardware": info?.hardwareVersion ?? "", "firmware": info?.firmwareVersion ?? ""]
            m["app"] = ["analysis": "KYAnalyzer/KYInsight", "fs": Self.sampleRate]
            capture = try KYCapture(meta: m)
            startStream()
            log("capture start \(capture!.id)")
            return ["id": capture!.id]
        } catch {
            return ["error": error.localizedDescription]
        }
    }

    /// Log a user event: into the running capture (if any) and always into the on-phone wellness store.
    func addUserEvent(_ e: [String: Any]) -> [String: Any] {
        var ev = e
        if ev["t"] == nil { ev["t"] = Date().timeIntervalSince1970 }
        if let c = capture { ev["captureId"] = c.id; c.addUserEvent(ev) }
        KYWellnessStore.append(kind: "events", record: ev)
        log("user event \(ev["kind"] ?? "") \(ev["label"] ?? "")")
        return ["captureId": capture?.id as Any, "t": ev["t"] as Any]
    }

    func markPhase(_ phase: String, note: String?) { capture?.mark(phase: phase, note: note); log("capture phase \(phase)") }

    func updateCapture(_ meta: [String: Any]) { capture?.update(meta: meta) }

    func stopCapture(extra: [String: Any]) -> [String: Any] {
        guard let c = capture else { return ["error": "No session is being captured"] }
        capture = nil
        var e = extra
        let m = analyzer.metrics, st = insight.state
        var summary: [String: Any] = ["beats": m.beatCount, "droppedFrames": droppedFrames, "restingHr": st.restingHr,
                                      "events": insight.events.map { ["type": $0.type, "start": ($0.start) + (firstSampleTime ?? 0), "end": $0.end + (firstSampleTime ?? 0)] }
                                          .filter { ($0["end"] as? Double ?? 0) >= (c.meta["startedAt"] as? Double ?? 0) }]  // only this session
        if let v = m.rmssd300 { summary["rmssd300End"] = v }
        let t0 = c.meta["startedAt"] as? Double ?? Date().timeIntervalSince1970
        let wall = Date().timeIntervalSince1970 - t0
        let overnight = (c.meta["therapyId"] as? String) == "overnight_sleep" || nightOverlapSec(from: t0, to: t0 + wall) >= 2 * 3600
        if wall > 2 * 3600, overnight, let n = KYSleepNight.analyze(beats: c.beatTimes.map { $0 - t0 }, durationSec: wall) {
            var sl: [String: Any] = ["totalSleepMin": n.totalSleepMin, "efficiency": n.efficiency, "wasoMin": n.wakeAfterOnsetMin,
                                     "awakenings": n.awakenings, "hypnogram": n.asleep.map { $0 ? 1 : 0 }, "epochSec": 30]
            if let v = n.sleepOnsetMin { sl["onsetMin"] = v }
            if let v = n.sleepHr { sl["sleepHr"] = v }
            if let v = n.sleepRmssd { sl["sleepRmssd"] = v }
            summary["sleep"] = sl
        }
        e["summary"] = summary
        let url = c.finish(extra: e)
        log("capture stop \(c.id) → \(url.lastPathComponent)")
        return ["id": c.id, "bundlePath": url.path]
    }

    var captureId: String? { capture?.id }
    var captureMeta: [String: Any]? { capture?.meta }

    func startRecording() {
        let now = UInt32(Date().timeIntervalSince1970)
        send(KYRequest.holterTime(set: now))
        send(KYRequest.holter(start: true, durationSec: 24 * 3600))
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { [weak self] in self?.pollRecording() }
        // Firmware B1_1.00.39 does not write to memory while it streams (dry run 2026-10-12: only non-streaming time was
        // stored). So recording to memory pauses the live stream; it resumes when the recording stops.
        if wantsStream { pauseStreamForRecording() }
    }

    private func pauseStreamForRecording() {
        send(KYRequest.ecg(start: false, durationSec: 0))
        streamStartedAt = nil
        liveBlockedByRecording = true
        log("live stream paused: band is recording to memory")
        if state == .streaming { set(.connected) } else { publish() }
    }

    func stopRecording() {
        send(KYRequest.holter(start: false))
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { [weak self] in self?.pollRecording() }
        if liveBlockedByRecording {
            liveBlockedByRecording = false
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { [weak self] in
                guard let self, self.wantsStream, self.sync == nil else { return }
                self.send(KYRequest.ecg(start: true, durationSec: 3600)); self.streamStartedAt = Date()
            }
            publish()
        }
    }

    /// Downloads the on-device recording to Documents/ky-recordings/<start>.holter and analyses it.
    func syncRecording() {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("ky-recordings")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let start = holterStart ?? UInt32(Date().timeIntervalSince1970)
        let url = dir.appendingPathComponent("\(start).holter")
        sync = KYHolterSync(fileURL: url, send: { [weak self] in self?.send($0) }) { [weak self] e in self?.syncEvent(e, start: start) }
        sync?.start()
    }

    // MARK: internals

    private func attach(_ p: CBPeripheral) {
        userDisconnected = false
        peripheral = p
        p.delegate = self
        lastError = nil
        set(.connecting)
        central.connect(p, options: nil)
    }

    private func set(_ s: State) {
        state = s
        publish()
    }

    private func publish() {
        emit?("onStatus", status())
        log("status \(state.rawValue) holter=\(holterState) blocked=\(liveBlockedByRecording) lead=\(leadOn.map { "\($0)" } ?? "?") batt=\(info?.battery ?? -1)")
    }

    func log(_ line: String) {
        let day = String(ISO8601DateFormatter().string(from: Date()).prefix(13))  // one file per hour
        if day != debugDay || debug == nil {
            try? debug?.close()
            let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("ky-debug")
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            if let old = try? FileManager.default.contentsOfDirectory(atPath: dir.path).sorted(), old.count > 12 {
                for f in old.prefix(old.count - 12) { try? FileManager.default.removeItem(at: dir.appendingPathComponent(f)) }
            }
            let url = dir.appendingPathComponent("\(day.replacingOccurrences(of: ":", with: "-")).log")
            if !FileManager.default.fileExists(atPath: url.path) { FileManager.default.createFile(atPath: url.path, contents: nil) }
            debug = try? FileHandle(forWritingTo: url)
            _ = try? debug?.seekToEnd()
            debugDay = day
        }
        debug?.write("\(String(format: "%.3f", Date().timeIntervalSince1970)) \(line)\n".data(using: .utf8)!)
    }

    private func send(_ packet: KYPacket) {
        guard let p = peripheral, let c = tx else { return }
        let bytes = packet.encoded
        let chunk = max(20, p.maximumWriteValueLength(for: .withoutResponse))
        var i = 0
        while i < bytes.count {
            let end = min(i + chunk, bytes.count)
            p.writeValue(Data(bytes[i..<end]), for: c, type: .withoutResponse)
            i = end
        }
    }

    private func onReady() {
        send(KYRequest.connectionHandshake)
        send(KYRequest.deviceInfo)
        send(KYRequest.leadState)
        pollRecording()
        if !probedAcc {  // one-time, read-only probe: does this band answer the accelerometer query? (logged only)
            probedAcc = true
            send(KYPacket(command: 0x2E))
        }
        set(.connected)
        keepAlive?.invalidate()
        keepAlive = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in self?.tick() }
        // don't start the live stream until we know the band isn't recording to memory (that would stop the recording)
        awaitingHolterState = wantsStream
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            guard let self, self.awaitingHolterState else { return }
            self.awaitingHolterState = false
            if self.wantsStream { self.beginStream() }
        }
    }

    private func beginStream() {
        analyzer.reset()
        insight = Self.makeInsight()
        insight.onEvent = { [weak self] e in self?.emitRhythm(e, offset: self?.firstSampleTime ?? Date().timeIntervalSince1970) }
        firstSampleTime = nil; samplesIn = 0; lastFrameIndex = nil; droppedFrames = 0
        streamStartedAt = Date()
        send(KYRequest.ecg(start: true, durationSec: 3600))
        set(.streaming)
    }

    private func tick() {
        send(KYRequest.deviceInfo)
        send(KYRequest.leadState)
        send(KYRequest.holterState)
        if wantsStream, !liveBlockedByRecording, let s = streamStartedAt, Date().timeIntervalSince(s) > 50 * 60 {
            streamStartedAt = Date()
            send(KYRequest.ecg(start: true, durationSec: 3600))  // re-arm the band's timed stream
        }
    }

    private func pollRecording() {
        send(KYRequest.holterState)
        send(KYRequest.holterTime())
    }

    private func handle(_ m: KYMessage) {
        if sync?.handle(m) == true { return }
        switch m {
        case .deviceInfo(let i): info = i; publish()
        case .leadState(let l):
            log("lead on=\(l.isLeadOn) drops=\(l.dropCount)")
            leadOn = l.isLeadOn; analyzer.leadOn = l.isLeadOn; publish()
        case .holterState(let s):
            holterState = s
            let recording = [.single, .sleep, .continuous].contains(s)
            if awaitingHolterState {
                awaitingHolterState = false
                if recording { pauseStreamForRecording() }
                else if wantsStream { beginStream() }
            } else if !recording && liveBlockedByRecording {  // recording ended on the band (e.g. full/low battery)
                liveBlockedByRecording = false
                if wantsStream && sync == nil { beginStream() }
            }
            // Auto-sync: a recording the band made on its own (phone away, app closed) is pulled the moment the band
            // reconnects — once per recording, so nothing waits on someone remembering to tap Sync.
            let have = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("ky-recordings/\(holterStart ?? 0).holter")
            let alreadyOnPhone = ((try? FileManager.default.attributesOfItem(atPath: have.path)[.size] as? Int) ?? 0) > 1024
            if !recording, s != .readingFlash, sync == nil, capture == nil, !alreadyOnPhone, let st = holterStart, st > 0,
               UserDefaults.standard.integer(forKey: "telomy.band.lastAutoSync") != Int(st) {
                UserDefaults.standard.set(Int(st), forKey: "telomy.band.lastAutoSync")
                log("auto-sync on-band recording started \(st)")
                syncRecording()
            }
            publish()
        case .holterTime(let t): holterStart = t; publish()
        case .ecgFrame(let f): handleFrame(f)
        case .other(let cmd, let payload):
            log(String(format: "other cmd=0x%02X len=%d %@", cmd, payload.count, payload.prefix(48).map { String(format: "%02X", $0) }.joined(separator: " ")))
        default: break
        }
    }

    private func handleFrame(_ f: KYEcgFrame) {
        if state != .streaming { state = .streaming; publish() }
        if let last = lastFrameIndex, f.frameIndex > last + 1 { droppedFrames += f.frameIndex - last - 1 }
        lastFrameIndex = f.frameIndex
        let now = Date().timeIntervalSince1970
        lastFrameAt = now
        if liveBlockedByRecording, now - lastPauseSent > 10 {  // band still streaming (e.g. a timed stream from before): stop it
            lastPauseSent = now
            send(KYRequest.ecg(start: false, durationSec: 0))
            log("stream frame while recording to memory → stop sent")
        }
        if firstSampleTime == nil { firstSampleTime = now - Double(f.samples.count) / Self.sampleRate }
        let out = analyzer.process(f.samples)
        capture?.addSamples(f.samples, frameEndUnix: now)
        log("ecg \(f.frameIndex) \(f.samples.map(String.init).joined(separator: ","))")
        samplesIn += f.samples.count
        let t0 = firstSampleTime ?? now
        // display samples are delayed by the baseline filter; their first sample index:
        let displayStart = samplesIn - f.samples.count - analyzer.displayDelay
        emit?("onEcg", [
            "frame": f.frameIndex,
            "t": t0 + Double(max(0, displayStart)) / Self.sampleRate,
            "fs": Self.sampleRate,
            "raw": f.samples.map(Int.init),
            "display": out.display.map { ($0 * 10).rounded() / 10 },
        ])
        for b in out.beats { log(String(format: "beat %.2f rr=%@ amp=%.0f", b.sample, b.rrMs.map { String(format: "%.1f", $0) } ?? "-", b.amplitude)) }
        for b in out.beats { capture?.addBeat(tUnix: t0 + b.sample / Self.sampleRate, rr: b.rrMs, amplitude: b.amplitude) }
        for b in out.beats {
            emit?("onBeat", ["t": t0 + b.sample / Self.sampleRate, "rr": b.rrMs as Any, "amplitude": b.amplitude])
        }
        insight.process(samples: f.samples, beats: out.beats, leadOn: leadOn ?? true, quality: analyzer.currentQuality)
        let m = analyzer.metrics
        let st = insight.state
        var mm: [String: Any] = ["quality": m.quality.rawValue, "hrvReliable": m.hrvReliable && st.hrvState == "ok", "beats": m.beatCount,
                                 "irregularBeats60": m.irregularBeats60, "sqi": m.sqi, "droppedFrames": droppedFrames, "t": now,
                                 "hrConfidence": st.hrConfidence, "hrvState": st.hrvState, "activity": st.activity.rawValue,
                                 "sleep": st.sleep.rawValue, "motionIndex": st.motionIndex, "signal": st.windowClass,
                                 "restingHr": st.restingHr, "earlyBeatsPerMin": st.earlyBeatsPerMin, "afBurden60": st.afBurden60,
                                 "openEvents": st.openEvents]
        if let v = st.hr { mm["hr"] = v }               // adaptive Kalman heart rate
        if let v = st.hrSd { mm["hrSd"] = v }
        if let v = m.heartRate { mm["hr10"] = v }       // plain 10-s mean, for comparison
        if let v = st.rmssd { mm["rmssdSmooth"] = v }
        if let v = st.rmssd5 { mm["rmssd5"] = v }
        if now - restingSavedAt > 60 { restingSavedAt = now; UserDefaults.standard.set(st.restingHr, forKey: Self.restingKey) }
        KYSleepAuto.shared.band(sleep: st.sleep.rawValue, activity: st.activity.rawValue)   // auto sleep onset / wake
        if let v = m.meanNN60 { mm["meanNN60"] = v }
        if let v = m.rmssd60, st.hrvState == "ok" || st.hrvState == "active" { mm["rmssd60"] = v }
        if let v = m.sdnn60 { mm["sdnn60"] = v }
        if let v = m.pnn50_60 { mm["pnn50"] = v }
        if let v = m.rmssd300 { mm["rmssd300"] = v }
        if let v = m.sdnn300 { mm["sdnn300"] = v }
        if let v = m.artefactPercent60 { mm["artefactPercent"] = v }
        if capture != nil { mm["capturing"] = capture!.id; capture?.addMetrics(mm) }
        emit?("onMetrics", mm)
        // Lock Screen live heart (ActivityKit), throttled to 5 s inside
        let live = KYLiveActivity.shared
        if !live.isRunning { live.start(title: capture.map { ($0.meta["therapy"] as? String) ?? "Session" } ?? "Live heart") }
        let sub = capture.map { "\(($0.meta["therapy"] as? String) ?? "Session") · \(live.elapsed)" } ?? "Live heart · \(live.elapsed)"
        live.update(hr: st.hr, hrv: (st.hrvState == "ok" || st.hrvState == "active") ? st.rmssd : nil, signal: st.windowClass, subtitle: sub)
        log("metrics q=\(m.quality.rawValue) hr=\(m.heartRate.map { String(format: "%.1f", $0) } ?? "-") rmssd60=\(m.rmssd60.map { String(format: "%.1f", $0) } ?? "-") rel=\(m.hrvReliable) art=\(m.artefactPercent60.map { String(format: "%.1f", $0) } ?? "-") sqi=\(m.sqi.map { "\($0.key)=\(String(format: "%.2f", $0.value))" }.sorted().joined(separator: ","))")
    }

    private func emitRhythm(_ e: KYInsight.Event, offset: Double) {
        log("rhythm \(e.type) \(String(format: "%.0f-%.0f", e.start, e.end)) \(e.detail)")
        let ev: [String: Any] = ["type": e.type, "start": offset + e.start, "end": offset + e.end, "detail": e.detail]
        capture?.addEvent(ev)
        emit?("onRhythm", ev)
    }

    private func syncEvent(_ e: KYHolterSync.Event, start: UInt32) {
        switch e {
        case .started(let total, let from): emit?("onRecording", ["phase": "started", "total": total, "from": from])
        case .progress(let r, let t): emit?("onRecording", ["phase": "progress", "received": r, "total": t])
        case .failed(let msg): emit?("onRecording", ["phase": "failed", "message": msg])
        case .completed(let url, let frames):
            emit?("onRecording", ["phase": "analysing", "frames": frames])
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                guard let self else { return }
                var payload = self.analyseRecording(url: url, frames: frames, start: start)
                let merged = KYCapture.attachRecording(payload: payload, holterURL: url)
                payload["beatTimes"] = nil
                if let merged { payload["captureId"] = merged }
                DispatchQueue.main.async {
                    self.log("recording analysed: \(frames) frames, merged into \(merged ?? "no capture")")
                    self.emit?("onRecording", payload)
                }
            }
        }
    }

    private func analyseRecording(url: URL, frames: Int, start: UInt32) -> [String: Any] {
            var payload: [String: Any] = ["phase": "completed", "path": url.path, "frames": frames, "start": Double(start)]
            if let all = try? KYHolterFile.frames(at: url) {
                payload["samples"] = all.reduce(0) { $0 + $1.samples.count }
                let a = KYAnalyzer(sampleRate: Self.sampleRate)
                let ins = Self.makeInsight()
                var rr: [Double] = []
                var beatTimes: [Double] = []
                var samples = 0
                for f in all {
                    let out = a.process(f.samples)
                    rr += out.beats.compactMap(\.rrMs)
                    beatTimes += out.beats.map { $0.sample / Self.sampleRate }
                    ins.process(samples: f.samples, beats: out.beats, leadOn: true, quality: a.currentQuality)
                    samples += f.samples.count
                }
                payload["events"] = ins.events.map { ["type": $0.type, "start": Double(start) + $0.start, "end": Double(start) + $0.end, "detail": $0.detail] }
                if let n = KYSleepNight.analyze(beats: beatTimes, durationSec: Double(samples) / Self.sampleRate) {
                    var sl: [String: Any] = ["totalSleepMin": n.totalSleepMin, "efficiency": n.efficiency, "wasoMin": n.wakeAfterOnsetMin,
                                             "awakenings": n.awakenings, "hypnogram": n.asleep.map { $0 ? 1 : 0 }]
                    if let v = n.sleepOnsetMin { sl["onsetMin"] = v }
                    if let v = n.sleepHr { sl["sleepHr"] = v }
                    if let v = n.sleepRmssd { sl["sleepRmssd"] = v }
                    payload["sleep"] = sl
                }
                let c = KYArtefacts.correct(rr)
                payload["durationSec"] = Double(samples) / Self.sampleRate
                payload["beats"] = rr.count + 1
                if !c.nn.isEmpty { payload["meanHr"] = 60000 / (c.nn.reduce(0, +) / Double(c.nn.count)) }
                if let v = KYHRV.rmssd(c.nn) { payload["rmssd"] = v }
                if let v = KYHRV.sdnn(c.nn) { payload["sdnn"] = v }
                payload["artefactPercent"] = c.artefactPercent
                payload["rr"] = c.nn.map { ($0 * 10).rounded() / 10 }
                payload["beatTimes"] = beatTimes.map { Double(start) + $0 }
            }
            return payload
    }
}

extension KYBand: CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ c: CBCentralManager) {
        switch c.state {
        case .poweredOn:
            set(peripheral?.state == .connected ? state : .idle)
            if let p = peripheral, p.state == .connected, tx == nil {  // restored by iOS while connected: rediscover the channel
                p.delegate = self; set(.connecting); p.discoverServices([Self.serviceUUID])
            } else { autoConnect() }
        case .unauthorized: set(.unauthorized)
        case .unsupported: set(.unsupported)
        default: set(.off)
        }
    }

    func centralManager(_ c: CBCentralManager, willRestoreState dict: [String: Any]) {
        if let p = (dict[CBCentralManagerRestoredStatePeripheralsKey] as? [CBPeripheral])?.first {
            peripheral = p
            p.delegate = self
        }
    }

    func centralManager(_ c: CBCentralManager, didDiscover p: CBPeripheral, advertisementData ad: [String: Any], rssi: NSNumber) {
        let name = (ad[CBAdvertisementDataLocalNameKey] as? String) ?? p.name ?? ""
        let services = (ad[CBAdvertisementDataServiceUUIDsKey] as? [CBUUID]) ?? []
        guard services.contains(Self.serviceUUID) || name.localizedCaseInsensitiveContains("B1") || name.localizedCaseInsensitiveContains("A1") else { return }
        found[p.identifier] = p
        emit?("onDevice", ["id": p.identifier.uuidString, "name": name.isEmpty ? "ECG band" : name, "rssi": rssi.intValue])
    }

    func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) {
        decoder = KYPacketDecoder()
        p.discoverServices([Self.serviceUUID])
    }

    func centralManager(_ c: CBCentralManager, didFailToConnect p: CBPeripheral, error: Error?) {
        lastError = error?.localizedDescription
        set(.idle)
        if !userDisconnected { DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in self?.autoConnect() } }
    }

    func centralManager(_ c: CBCentralManager, didDisconnectPeripheral p: CBPeripheral, error: Error?) {
        tx = nil
        keepAlive?.invalidate()
        leadOn = nil
        if userDisconnected {
            set(.idle)
        } else {
            set(.connecting)
            central.connect(p, options: nil)  // pending reconnect: completes when the band is back in range
        }
    }
}

extension KYBand: CBPeripheralDelegate {
    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        guard let s = p.services?.first(where: { $0.uuid == Self.serviceUUID }) else {
            lastError = "This device is not a supported ECG band."
            disconnect(); return
        }
        p.discoverCharacteristics([Self.notifyUUID, Self.writeUUID], for: s)
    }

    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        for c in s.characteristics ?? [] {
            if c.uuid == Self.writeUUID { tx = c }
            if c.uuid == Self.notifyUUID { p.setNotifyValue(true, for: c) }
        }
    }

    func peripheral(_ p: CBPeripheral, didUpdateNotificationStateFor c: CBCharacteristic, error: Error?) {
        if c.uuid == Self.notifyUUID, c.isNotifying { onReady() }
    }

    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        guard let v = c.value else { return }
        for packet in decoder.feed([UInt8](v)) { handle(KYMessage(packet)) }
    }
}
