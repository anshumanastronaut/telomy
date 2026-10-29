import CoreBluetooth
import CoreMotion
import Foundation

/// Clean-room CoreBluetooth client for the TK3040B9 "smart ring" (Sichuan Haikehuicheng), which speaks the Yucheng
/// (YCBT) BLE protocol. Reverse-engineered from the HealthWear app with the manufacturer's permission and verified live
/// against the ring (telomy-lab/ring-tk3040/PROTOCOL.md). No vendor code is used.
///
/// Telomy reads the ring **locally only** — nothing is uploaded, unlike the stock app which sends readings (including a
/// non-real "blood sugar") to a third-party cloud. HR, HRV, temperature, SpO₂ and motion are treated as real; blood
/// pressure and glucose from this sensor class are NOT measurable and are never stored or shown as readings.
final class KYRing: NSObject {
    static let shared = KYRing()

    static let service = CBUUID(string: "be940000-7333-be46-b7ae-689e71722bd5")
    static let writeCh = CBUUID(string: "be940001-7333-be46-b7ae-689e71722bd5")
    static let notifyCh = CBUUID(string: "be940003-7333-be46-b7ae-689e71722bd5")
    static let rememberKey = "telomy.ring.id"

    private var central: CBCentralManager!
    private var ring: CBPeripheral?
    private var writeC: CBCharacteristic?
    private var writeType: CBCharacteristicWriteType = .withoutResponse
    private var rxBuf = [UInt8]()
    private var notifySubs = 0
    private var probes = 0
    private var debug: FileHandle?
    private var debugHour = ""

    var emit: ((String, [String: Any]) -> Void)?
    private(set) var state = "idle"           // idle, scanning, connecting, connected
    private(set) var battery = -1
    private(set) var lastHR: Int?
    private(set) var lastHRV: Int?
    private(set) var lastSpO2: Int?
    private(set) var lastTemp: Double?
    private(set) var deviceName = ""

    // Continuous longitudinal sync. The ring measures itself on a timer and logs to flash (SettingHeartMonitor etc.);
    // we enable that on connect, then pull history every `syncEveryMin` and keep the realtime values fresh in between.
    private let monitorEveryMin = 5          // ring auto-measures HR/SpO₂/temp/HRV this often (one short PPG burst)
    private let syncEveryMin = 5             // we read the flash log back this often while connected (foreground)
    private var syncTimer: Timer?
    private var histType: Int = 0            // subtype of the history dump currently streaming (6 heart, 26 spo2, 30 temp, 9 all)
    private var histOp: UInt16 = 0           // opcode of the request in flight; its echo is a summary, not records
    private var histBuf = [UInt8]()          // reassembled record body for the current dump
    private var lastHistHR: Int?, lastHistHRAt = 0.0
    /// Newest heart rate from the ring's own flash log, if logged within `maxAge` seconds.
    func recentHistoryHR(maxAge: Double) -> Double? {
        guard let h = lastHistHR, Date().timeIntervalSince1970 - lastHistHRAt <= maxAge else { return nil }
        return Double(h)
    }
    private var histQueue: [(UInt16, Int)] = []
    private var histWatchdog: DispatchWorkItem?
    private var setupDone = false            // didUpdateNotificationStateFor fires once per characteristic — set up once

    // History opcodes (dataType 0x05 = Health). item = subtype used by the parser.
    private static let histHeart: UInt16 = 0x0506   // Health_HistoryHeart   (1286) stride 6  [ts4][mode][hr]
    private static let histSpO2:  UInt16 = 0x051A   // Health_HistoryBloodOxygen (1306) stride 6 [ts4][type][spo2]
    private static let histTemp:  UInt16 = 0x051E   // Health_HistoryTemp    (1310) stride 7  [ts4][type][int][frac]
    private static let histAll:   UInt16 = 0x0509   // Health_HistoryAll     (1289) stride 20 HR+HRV+CVRR+temp together

    private override init() { super.init(); central = CBCentralManager(delegate: self, queue: .main,
        options: [CBCentralManagerOptionRestoreIdentifierKey: "telomy.ring", CBCentralManagerOptionShowPowerAlertKey: true]) }

    // MARK: public API
    func status() -> [String: Any] {
        var s: [String: Any] = ["state": state, "battery": battery, "name": deviceName]
        if let v = lastHR { s["hr"] = v }
        if let v = lastHRV { s["hrv"] = v }
        if let v = lastSpO2 { s["spo2"] = v }
        if let v = lastTemp { s["temp"] = v }
        s["capturing"] = capturing
        s["overnight"] = overnight
        if !rawCounts.isEmpty { s["rawCounts"] = rawCounts }
        if let id = UserDefaults.standard.string(forKey: Self.rememberKey) { s["rememberedId"] = id }
        return s
    }

    func scan() {
        guard central.state == .poweredOn else {
            set(central.state == .unauthorized ? "unauthorized" : central.state == .poweredOff ? "off" : "idle"); return
        }
        // a ring already connected in iOS Settings won't advertise — retrieve it directly
        let svcs = [Self.service, CBUUID(string: "180A"), CBUUID(string: "180F"), CBUUID(string: "1812"),
                    CBUUID(string: "6e400001-b5a3-f393-e0a9-e50e24dcca9e")]
        for p in central.retrieveConnectedPeripherals(withServices: svcs) {
            let n = (p.name ?? "").uppercased()
            if n.isEmpty || n.contains("TK") || n.contains("RING") || n.contains("R0") || n.contains("SMART") || n.contains("YC") || n.contains("BR") {
                log("found system-connected \(safeName(p.name))"); attach(p); return
            }
        }
        set("scanning")
        central.scanForPeripherals(withServices: nil, options: [CBCentralManagerScanOptionAllowDuplicatesKey: false])
        DispatchQueue.main.asyncAfter(deadline: .now() + 20) { [weak self] in
            guard let self, self.state == "scanning" else { return }
            self.central.stopScan(); self.set(self.ring == nil ? "idle" : self.state)
        }
    }

    func connect(id: String) {
        guard let uuid = UUID(uuidString: id), let p = central.retrievePeripherals(withIdentifiers: [uuid]).first else { scan(); return }
        attach(p)
    }

    func autoConnect() {
        guard central.state == .poweredOn, ring == nil, let id = UserDefaults.standard.string(forKey: Self.rememberKey),
              let uuid = UUID(uuidString: id), let p = central.retrievePeripherals(withIdentifiers: [uuid]).first else { return }
        attach(p)
    }

    func disconnect() { if let p = ring { central.cancelPeripheralConnection(p) }; ring = nil; set("idle") }
    func forget() { disconnect(); UserDefaults.standard.removeObject(forKey: Self.rememberKey) }

    /// type 0 = live heart-rate stream; otherwise AppStartMeasurement (0x032F [on, type]) with the SDK's Common types:
    /// 2 = SpO₂, 4 = temperature, 10 = HRV, 3 = respiratory rate. NOTE type 1 is BLOOD PRESSURE in this SDK — the old
    /// "heart rate" button sent 1 and put the ring in BP-estimate mode. Live HR is AppControlReal 0x0309 [on, 1, 2 s],
    /// exactly what the vendor app sends (appRealDataReport(1, 1, 2)).
    func startMeasure(_ type: Int) {
        if type == 0 { send(0x0309, [0x01, 0x01, 0x02]); return }
        send(0x032F, [0x01, UInt8(type & 0xFF)])
    }
    func stopMeasure(_ type: Int) {
        if type == 0 { send(0x0309, [0x00, 0x01, 0x02]); return }
        send(0x032F, [0x00, UInt8(type & 0xFF)])
    }

    // Live HR view: hold the ~2 s real-time HR stream (AppControlReal 0x0309 on, every 2 s) ON while a screen is
    // showing it (the ring screen calls setLive(true) on focus, false on blur). Without this, a connected ring only
    // refreshes HR when the 5-min flash log is pulled, which is the "large gap between HR sendings". A 25 s keep-alive
    // re-arms the stream because the ring stops it on its own after a while or after a spot measurement. No-op during
    // overnight (which drives its own stream) and the flag is honoured on the next (re)connect if not yet connected.
    private(set) var live = false
    private var liveTimer: Timer?
    func setLive(_ on: Bool) {
        live = on
        liveTimer?.invalidate(); liveTimer = nil
        guard state == "connected" else { return }
        if on {
            if !overnight { send(0x0309, [0x01, 0x01, 0x02]) }
            liveTimer = Timer.scheduledTimer(withTimeInterval: 25, repeats: true) { [weak self] _ in
                guard let self, self.live, self.state == "connected", !self.overnight, !self.capturing else { return }
                self.send(0x0309, [0x01, 0x01, 0x02])
            }
        } else if !overnight {
            send(0x0309, [0x00, 0x01, 0x02])
        }
    }

    // MARK: overnight mode — continuous HR + movement all night, saved on the phone even with the screen off
    private(set) var overnight = false
    /// Live HR every ~2 s (Real_UploadHeart) + live sport counters every ~2 s (step increments = movement, an actigraphy
    /// proxy) + an attempt at the raw sensor switch (AppSensorSwitchControl 0x0322; logged either way). Frames arrive as
    /// CoreBluetooth notifications, which wake the app in the background, so capture continues with the screen locked.
    /// The ring's own 5-min monitoring keeps logging to its flash regardless; we pull that plus its sleep score at stop.
    func startOvernight() {
        guard state == "connected", !overnight else { return }
        if capturing { stopRawCapture() }
        startRawCapture(ecg: false, imu: false, ppg: false, tag: "night")
        overnight = true
        send(0x0309, [0x01, 0x01, 0x02])                 // live heart rate
        send(0x0309, [0x01, 0x00, 0x02])                 // live sport counters (movement)
        send(0x0322, [0x01, 0x01])                       // raw sensor stream, if this firmware supports it
        readBattery()
        log("overnight started")
        publish()
    }
    static let nightStreams: [UInt16: String] = [0x0601: "hr", 0x0602: "spo2", 0x060A: "temp", 0x0600: "sport",
        0x0603: "bpEst(ignored)", 0x0322: "sensorAck", 0x0309: "realAck", 0x032F: "measureAck"]
    private var lastSport: [UInt8] = []
    private var lastMoveAt = Date().timeIntervalSince1970
    private var lastSpO2At = 0.0, lastTempAt = 0.0, lastBattAt = 0.0
    private var moving = false
    private var moveBoutStart = 0.0, watching = false, lastHistAt = 0.0

    /// Any change in the live step/motion counters = you moved. Returns true on a movement.
    @discardableResult private func noteSport(_ p: [UInt8]) -> Bool {
        let now = Date().timeIntervalSince1970
        defer { lastSport = p }
        guard !lastSport.isEmpty, p != lastSport else { return false }
        if now - lastMoveAt > 60 { moveBoutStart = now }
        lastMoveAt = now
        return true
    }
    /// Seconds since the last movement (0 if we aren't receiving motion counters).
    var stillSeconds: Double { watching || overnight ? Date().timeIntervalSince1970 - lastMoveAt : 0 }
    /// Length of the current movement bout (0 if still for > 1 min).
    var movingSeconds: Double { let n = Date().timeIntervalSince1970; return n - lastMoveAt < 60 ? n - moveBoutStart : 0 }

    /// Every ring heartbeat (~10 s, also in the background): evening motion watch for auto-sleep, a 5-min history
    /// sync that doesn't depend on a foreground timer, and the auto-sleep evaluator.
    private func heartbeatTick() {
        let now = Date().timeIntervalSince1970, hour = Calendar.current.component(.hour, from: Date())
        if state == "connected", !watching, !overnight, hour >= 20 || hour < 10 {
            watching = true; lastMoveAt = now; lastSport = []
            send(0x0309, [0x01, 0x00, 0x02])            // live motion counters only — no optical sensor, minimal battery
            log("evening motion watch on")
        } else if watching, !overnight, hour >= 10, hour < 20 {
            watching = false; send(0x0309, [0x00, 0x00, 0x02])
        }
        if !capturing, now - lastHistAt >= Double(syncEveryMin) * 60 { lastHistAt = now; syncHistory() }
        KYSleepAuto.shared.evaluate()
    }

    /// Live frames during the night: keep the app's values fresh, detect movement, and resume the HR stream after a
    /// motion-gated spot measurement finishes (a spot reading can pre-empt the live stream).
    private func nightFrame(_ code: UInt16, _ p: [UInt8]) {
        let now = Date().timeIntervalSince1970
        switch code {
        case 0x0601: if let v = p.first, v > 0 { lastHR = Int(v) }
        // Overnight SpO₂: keep a bounded range so genuine sleep desaturation (apnea dips into the low 80s) is preserved,
        // but drop the SDK's out-of-range garbage (54–146 seen). A sub-80 reflectance reading is indistinguishable from a
        // failed measurement on this hardware, so it is not trusted.
        case 0x0602: if let v = p.first, v >= 80, v <= 100 { lastSpO2 = Int(v); send(0x0309, [0x01, 0x01, 0x02]) }
        case 0x060A: if p.count > 13, p[12] >= 20, p[12] <= 45 { lastTemp = Double(p[12]) + Double(p[13]) / 10; send(0x0309, [0x01, 0x01, 0x02]) }
        case 0x0600:
            if noteSport(p), !moving { rawFile?.write(String(format: "%.3f event move-start\n", now).data(using: .utf8)!) }
            if now - lastMoveAt < 1 { moving = true }
        default: break
        }
    }

    /// Motion-gated measuring, like the best rings: measure when you've been still (clean optical signal), log
    /// movement bursts as possible arousals. Driven by the ring's 10-s heartbeat so it runs in the background.
    private func nightTick() {
        let now = Date().timeIntervalSince1970, still = now - lastMoveAt
        if moving, still > 30 { moving = false; rawFile?.write(String(format: "%.3f event move-end\n", now).data(using: .utf8)!) }
        if still >= 120, now - lastSpO2At >= 15 * 60 { lastSpO2At = now; log("still \(Int(still))s → SpO₂"); startMeasure(2) }
        else if still >= 60, now - lastTempAt >= 30 * 60 { lastTempAt = now; log("still \(Int(still))s → temp"); startMeasure(4) }
        if now - lastBattAt >= 30 * 60 { lastBattAt = now; readBattery() }
        if Calendar.current.component(.hour, from: Date()) == 9 { stopOvernight() }   // forgot to stop → stop at 09:00
    }

    func stopOvernight() {
        guard overnight else { return }
        send(0x0309, [0x00, 0x01, 0x02]); send(0x0309, [0x00, 0x00, 0x02]); send(0x0322, [0x01, 0x00])
        overnight = false
        stopRawCapture()                                 // restarts auto-sync → pulls the night's history + sleep score
        log("overnight stopped")
        publish()
    }
    func readBattery() { send(0x0200, [0x47, 0x43]) }     // device info (battery at payload[5])

    // MARK: raw research capture (ECG / PPG / IMU / PPI) — frames written verbatim to Documents/ring-raw for decoding
    // Stream opcodes from the SDK's Constants.DATATYPE (Real_Upload* = 0x06xx, Device* = 0x04xx, App* = 0x03xx).
    static let rawStreams: [UInt16: String] = [0x0605: "ecg", 0x06F0: "ecgHrv", 0x06F1: "ecgRR", 0x06F2: "ecgHR", 0x040B: "ecgEnd",
        0x0604: "ppg", 0x060F: "ppgMulti", 0x0616: "ppi", 0x0608: "imu", 0x0607: "resp", 0x0314: "ecgPpgStatus",
        0x03FA: "imuConfig", 0x03FB: "imuAck", 0x0302: "ecgAck", 0x03F9: "ppgAck"]
    private(set) var capturing = false
    private(set) var rawCounts: [String: Int] = [:]
    private var rawFile: FileHandle?
    private var ppi: [Double] = []

    /// Start the ring's raw streams. ECG: AppControl 0x0302 [2] (appEcgTestStart). IMU: query 0x03FA then switch on
    /// 0x03FB [on, xyz-mask]. PPG: raw acquisition 0x03F9 (green channel) plus an HR measurement so the ring also
    /// emits PPI (beat intervals) on 0x0616. Every reply is logged, so an unsupported stream shows up as "no frames".
    func startRawCapture(ecg: Bool, imu: Bool, ppg: Bool, tag: String = "raw") {
        guard state == "connected", !capturing else { return }
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("ring-raw")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        pruneDir("ring-raw", keep: 40)               // bound raw-capture storage on the device
        let url = dir.appendingPathComponent(tag + "-" + ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-") + ".log")
        FileManager.default.createFile(atPath: url.path, contents: "# telomy ring \(tag) capture ecg=\(ecg) imu=\(imu) ppg=\(ppg)\n".data(using: .utf8))
        rawFile = try? FileHandle(forWritingTo: url); _ = try? rawFile?.seekToEnd()
        capturing = true; rawCounts = [:]; ppi = []
        stopAutoSync(); setupDone = true                       // pause history sync so its frames don't interleave
        if ecg { send(0x0302, [0x02]) }
        if imu { send(0x03FA, []); send(0x03FB, [0x01, 0x07]) }
        if ppg { send(0x03F9, [0x01, 0x19] + [UInt8](repeating: 0, count: 14)); startMeasure(0) }
        log("raw capture started ecg=\(ecg) imu=\(imu) ppg=\(ppg) → \(url.lastPathComponent)")
        publish()
    }

    func stopRawCapture() {
        guard capturing else { return }
        send(0x0302, [0x00]); send(0x03FB, [0x00, 0x07]); stopMeasure(0)
        capturing = false; try? rawFile?.close(); rawFile = nil
        log("raw capture stopped \(rawCounts)")
        publish()
        startAutoSync()
    }

    private func recordRaw(_ name: String, _ frame: [UInt8], _ payload: [UInt8]) {
        rawCounts[name, default: 0] += 1
        let line = String(format: "%.3f ", Date().timeIntervalSince1970) + name + " " + frame.map { String(format: "%02X", $0) }.joined() + "\n"
        rawFile?.write(line.data(using: .utf8)!)
        if name == "ppi" {                                     // u16 LE pulse-to-pulse intervals, ms
            var i = 0
            while i + 1 < payload.count {
                let v = Double(Int(payload[i]) | (Int(payload[i + 1]) << 8)); i += 2
                if v >= 300, v <= 2000 { ppi.append(v) }
            }
            if ppi.count > 120 { ppi.removeFirst(ppi.count - 120) }
            if ppi.count >= 20 {                               // RMSSD over the last ≤120 beats, successive diffs < 20 % (artefact gate)
                var sq = 0.0, n = 0
                for k in 1..<ppi.count where abs(ppi[k] - ppi[k - 1]) < 0.2 * ppi[k - 1] { sq += pow(ppi[k] - ppi[k - 1], 2); n += 1 }
                if n >= 10 { lastHRV = Int((sq / Double(n)).squareRoot().rounded()) }
            }
        }
    }

    // MARK: continuous longitudinal data
    /// Tell the ring to measure itself on a timer and log to flash, so we get 24/7 data without the phone
    /// driving slow spot-measurements. One short PPG burst every `monitorEveryMin`; very low battery cost.
    func enableMonitoring() {
        let m = UInt8(monitorEveryMin & 0xFF)
        send(0x010C, [0x01, m])               // SettingHeartMonitor      on, every m min  → logs HR + HRV (RRI)
        send(0x0126, [0x01, m])               // SettingBloodOxygenModeMonitor on, every m min
        send(0x0120, [0x01, m])               // SettingTemperatureMonitor on, every m min
        send(0x0145, [0x01, 0x00, 0x18, m, 0x00]) // SettingHRVMonitor on, window 00–24h, every m min
        send(0x0140, [0x00, 0x18, m])         // SettingAutomaticMeasurementTime: window 00–24h, interval m min
        log("enabled on-device monitoring every \(monitorEveryMin) min")
    }

    /// Pull everything the ring has logged since we last synced. Records stream back on the notify channel and are
    /// reassembled per type, then emitted as `onRingHistory` for the longitudinal store. Safe to call repeatedly.
    func syncHistory() {
        guard state == "connected", histQueue.isEmpty, histOp == 0 else { return }   // one sync at a time
        histQueue = [(Self.histAll, 9), (Self.histHeart, 6), (Self.histSpO2, 26), (Self.histTemp, 30), (0x0504, 4)]  // 4 = the ring's own sleep
        nextHistory()
    }

    /// Request one history type at a time. Verified on the ring: the request is answered by a short summary frame
    /// echoing the opcode, then the records stream in 0x0515 frames, then 0x0580 marks the end. Asking for all types
    /// at once interleaves the streams, so we wait for 0x0580 (or a timeout) before asking for the next.
    private func nextHistory() {
        histWatchdog?.cancel()
        if !histBuf.isEmpty { histBuf.removeAll() }
        guard !histQueue.isEmpty else { histOp = 0; return }
        let (op, sub) = histQueue.removeFirst()
        histOp = op; histType = sub
        send(op, [])                           // empty payload = "give me the whole log for this type"
        let w = DispatchWorkItem { [weak self] in self?.log("history \(sub) timed out"); self?.nextHistory() }
        histWatchdog = w
        DispatchQueue.main.asyncAfter(deadline: .now() + 15, execute: w)
    }

    private func startAutoSync() {
        syncTimer?.invalidate()
        enableMonitoring()
        DispatchQueue.main.asyncAfter(deadline: .now() + 4) { [weak self] in self?.syncHistory() }  // backfill on connect
        syncTimer = Timer.scheduledTimer(withTimeInterval: Double(syncEveryMin) * 60, repeats: true) { [weak self] _ in
            self?.syncHistory()
        }
    }
    private func stopAutoSync() {
        syncTimer?.invalidate(); syncTimer = nil
        histWatchdog?.cancel(); histQueue.removeAll(); histOp = 0; histBuf.removeAll(); setupDone = false; watching = false
    }

    // MARK: frame codec (PROTOCOL.md; verified live)
    static func crc16(_ b: ArraySlice<UInt8>) -> UInt16 {
        var s: UInt16 = 0xFFFF
        for x in b {
            s = (s << 8) | (s >> 8)
            s ^= UInt16(x)
            s ^= (s & 0xFF) >> 4
            s ^= (s << 12) & 0xFFFF
            s ^= (s & 0xFF) << 5
        }
        return s & 0xFFFF
    }

    /// Write-gate (adopted from NOOP's DeviceConfigWriteGate): refuse opcodes/params that would put the ring into a mode
    /// Telomy never wants — notably AppStartMeasurement type 1 = BLOOD PRESSURE estimation (the old "HR" button bug,
    /// see startMeasure's docstring). A refused write is logged, never sent, so a stray call can't mis-configure the ring.
    private func gateAllows(_ code: UInt16, _ payload: [UInt8]) -> Bool {
        if code == 0x032F, payload.count >= 2, payload[0] == 0x01, payload[1] == 0x01 { return false }  // turn ON BP-estimate
        return true
    }

    private func send(_ code: UInt16, _ payload: [UInt8]) {
        guard gateAllows(code, payload) else { log("gate blocked tx code=\(String(format: "%04X", code))"); return }
        guard let p = ring, let c = writeC else { return }
        let total = payload.count + 6
        var b = [UInt8](repeating: 0, count: total)
        b[0] = UInt8(code >> 8); b[1] = UInt8(code & 0xFF)
        b[2] = UInt8(total & 0xFF); b[3] = UInt8((total >> 8) & 0xFF)
        for (i, x) in payload.enumerated() { b[4 + i] = x }
        let crc = Self.crc16(b[0..<(payload.count + 4)])
        b[payload.count + 4] = UInt8(crc & 0xFF); b[payload.count + 5] = UInt8((crc >> 8) & 0xFF)
        log("tx " + b.map { String(format: "%02X", $0) }.joined())
        p.writeValue(Data(b), for: c, type: writeType)
    }

    private func onBytes(_ data: [UInt8]) {
        rxBuf += data
        while rxBuf.count >= 4 {
            let len = Int(rxBuf[2]) | (Int(rxBuf[3]) << 8)
            if len < 6 || len > 2048 { rxBuf.removeFirst(); continue }   // resync
            if rxBuf.count < len { break }
            let frame = Array(rxBuf[0..<len]); rxBuf.removeFirst(len)
            let crc = UInt16(frame[len - 2]) | (UInt16(frame[len - 1]) << 8)
            if Self.crc16(frame[0..<(len - 2)]) == crc { handle(frame) }
        }
    }

    private func handle(_ f: [UInt8]) {
        let code = (UInt16(f[0]) << 8) | UInt16(f[1])
        let payload = Array(f[4..<(f.count - 2)])
        if capturing, let name = Self.rawStreams[code] ?? (overnight ? Self.nightStreams[code] : nil) {
            recordRaw(name, f, payload)                         // verbatim to the night/raw file, no debug-log spam
            if overnight { nightFrame(code, payload) }
            emit?("onRingData", status()); return
        }
        if code == 0xFFFF { if overnight { nightTick() }; heartbeatTick() }   // 10-s heartbeat drives the schedulers
        if code != 0xFFFF { log("rx " + f.map { String(format: "%02X", $0) }.joined()) }
        switch code {
        case 0x0200:                                           // device info
            if payload.count > 5 { battery = Int(payload[5]); deviceName = "Ring" }
        case 0x0602:                                           // SpO₂ real-time (awake spot measurement)
            // Awake, a single reflectance-ring reading below 90 % is overwhelmingly a poor-contact / motion artifact, not
            // real hypoxemia — do not surface it as a number (it would be a false alarm). Keep the last good value; the
            // user can re-measure holding still. Overnight readings take the bounded path in nightFrame instead.
            if let v = payload.first, v >= 90, v <= 100 { lastSpO2 = Int(v) }
            else if let v = payload.first, v > 0 { log("spo2 \(v) rejected (awake, <90 = low-confidence)") }
        case 0x0601:                                           // heart rate real-time
            if let v = payload.first, v > 0 { lastHR = Int(v) }
        case 0x060A:                                           // temperature real packet (value at [12],[13])
            if payload.count > 13, payload[12] >= 20, payload[12] <= 45 { lastTemp = Double(payload[12]) + Double(payload[13]) / 10 }
        case 0x0600: noteSport(payload)                        // sport counters → movement (evening watch)
        case 0x0580:                                           // end of a history stream → next type
            if histType == 4 { parseSleepRecords() }
            log("history \(histType) done"); nextHistory(); return
        case _ where code >> 8 == 0x05:
            if code != histOp, histOp != 0 { parseHistory(payload) }   // 0x0515 record stream (echo = summary, skipped)
            return                                             // longitudinal dump — never a live reading
        case 0xFFFF: return                                    // heartbeat
        default: break
        }
        emit?("onRingData", status())
        publish()
    }

    /// Parse a streamed history dump into longitudinal samples. Record body starts at offset 0, fixed stride per type,
    /// timestamps are LOCAL wall-clock seconds since 2000-01-01 (we set the ring's clock in local time), converted to UTC ms. Verified record layout from the
    /// decompiled unpacker; emitted as `onRingHistory` for Telomy's longitudinal store. Parses what's complete and
    /// keeps any partial tail for the next frame.
    private func parseHistory(_ chunk: [UInt8]) {
        if histType == 4 {                     // ring's own sleep record: variable-length (night header + stage segments)
            saveSleepHistory(chunk)             // raw kept for re-decoding / audits
            histBuf += chunk; return            // decoded at end-of-stream (parseSleepRecords)
        }
        histBuf += chunk
        let stride = histType == 30 ? 7 : histType == 9 ? 20 : 6
        func ts(_ i: Int) -> Double {
            let le = Double(Int(histBuf[i]) | (Int(histBuf[i+1]) << 8) | (Int(histBuf[i+2]) << 16) | (Int(histBuf[i+3]) << 24))
            // The ring's clock is set to LOCAL wall time (makeTime), so its seconds-since-2000 are wall-clock, not UTC.
            // Convert back to real time (2026-10-19: every ring sample was 5 h 30 min late in IST until this fix).
            let wall = le + 946684800
            return (wall - Double(TimeZone.current.secondsFromGMT(for: Date(timeIntervalSince1970: wall)))) * 1000
        }
        var samples: [[String: Any]] = []
        var i = 0
        let latest = (Date().timeIntervalSince1970 + 86400) * 1000
        while i + stride <= histBuf.count {
            let t = ts(i)
            if t < 1_577_836_800_000 || t > latest { i += stride; continue }   // corrupt record (a year-2135 stamp was seen)
            switch histType {
            case 6:  if histBuf[i+5] >= 30, histBuf[i+5] <= 220 { samples.append(["t": t, "hr": Int(histBuf[i+5])]) }
            case 26: if histBuf[i+5] >= 80, histBuf[i+5] <= 100 { samples.append(["t": t, "spo2": Int(histBuf[i+5])]) }   // 54–146 seen: out-of-range = failed reading; <80 on this ring = artifact, not real desat
            case 30: let v = Double(histBuf[i+5]) + Double(histBuf[i+6]) / 10
                     if v >= 20, v <= 45 { samples.append(["t": t, "temp": v]) }
            case 9:  // paired HR + HRV at one timestamp — the record Telomy uses to cross-check against the patch
                var s: [String: Any] = ["t": t]
                if histBuf[i+6] >= 30, histBuf[i+6] <= 220 { s["hr"] = Int(histBuf[i+6]) }
                if histBuf[i+11] > 0 { s["hrv"] = Int(histBuf[i+11]) }
                if histBuf[i+12] > 0 { s["cvrr"] = Int(histBuf[i+12]) }
                let temp = Double(histBuf[i+13]) + Double(histBuf[i+14]) / 10
                if temp >= 20, temp <= 45 { s["temp"] = temp }
                if s.count > 1 { samples.append(s) }
            default: break
            }
            i += stride
        }
        histBuf.removeFirst(i)
        if let newest = samples.compactMap({ s -> (Double, Int)? in guard let t = s["t"] as? Double, let h = s["hr"] as? Int else { return nil }; return (t / 1000, h) }).max(by: { $0.0 < $1.0 }),
           newest.0 > lastHistHRAt { lastHistHRAt = newest.0; lastHistHR = newest.1 }
        if !samples.isEmpty { emit?("onRingHistory", ["type": histType, "samples": samples]) }
    }

    /// The ring's own sleep records (Health_HistorySleep 0x0504), decoded per the vendor SDK layout (DataUnpack case 4,
    /// manufacturer's permission): AF FA | len u16 | start u32 | end u32 | deepCount u16 (0xFFFF = v2) | totals |
    /// 8-byte segments [type u8 | start u32 | len u24 s]. Types (verified on 2026-10-18 against WHOOP): 241 deep,
    /// 242 light, 243 REM, 244 awake. Times are local wall-clock (converted to UTC like every ring record).
    /// The ring detects sleep from its own accelerometer — onset matched WHOOP to 1 min on 2026-10-18 — which gives
    /// ring-only nights the motion signal the 5-min HR log lacks.
    /// Completeness: a record whose bytes were cut by a BLE drop (seen: 1 of ~20 segments arrived) is emitted with its
    /// coverage, and the sleep log is re-requested once a minute later.
    private var sleepResyncAt = 0.0
    private func parseSleepRecords() {
        let b = histBuf
        func le(_ i: Int, _ n: Int) -> Int { var v = 0; for k in 0..<n { v |= Int(b[i + k]) << (8 * k) }; return v }
        func utc(_ wall: Int) -> Double {
            let w = Double(wall) + 946684800
            return w - Double(TimeZone.current.secondsFromGMT(for: Date(timeIntervalSince1970: w)))
        }
        var nights: [[String: Any]] = [], truncated = false
        var i = 0
        while i + 20 <= b.count {
            guard b[i] == 0xAF, b[i + 1] == 0xFA else { i += 1; continue }
            let L = le(i + 2, 2)
            if L < 20 { i += 2; continue }
            if i + L > b.count { truncated = true; break }
            let start = utc(le(i + 4, 4)), end = utc(le(i + 8, 4))
            var segs: [[String: Any]] = [], covered = 0
            var k = i + 20
            while k + 8 <= i + L {
                let ty = Int(b[k]), st = utc(le(k + 1, 4)), len = le(k + 5, 2) | (Int(b[k + 7]) << 16)
                if (241...244).contains(ty), len > 0, len < 86400 { segs.append(["type": ty, "start": st, "len": len]); covered += len }
                k += 8
            }
            if end > start, end - start < 20 * 3600, start > 1_577_836_800, start < Date().timeIntervalSince1970 + 86400 {
                nights.append(["start": start, "end": end, "segments": segs, "coverage": Double(covered) / (end - start)])
                if Double(covered) / (end - start) < 0.8 { truncated = true }
            }
            i += L
        }
        log("ring sleep: \(nights.count) record(s)\(truncated ? ", some incomplete" : "")")
        if !nights.isEmpty { emit?("onRingSleep", ["nights": nights]) }
        let now = Date().timeIntervalSince1970
        if truncated, now - sleepResyncAt > 600 {               // one retry per 10 min
            sleepResyncAt = now
            DispatchQueue.main.asyncAfter(deadline: .now() + 60) { [weak self] in
                guard let self, self.state == "connected", self.histQueue.isEmpty, self.histOp == 0 else { return }
                self.log("ring sleep: re-requesting incomplete records"); self.histQueue = [(0x0504, 4)]; self.nextHistory()
            }
        }
    }

    private func saveSleepHistory(_ chunk: [UInt8]) {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("ring-raw")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent("ring-sleep-" + String(ISO8601DateFormatter().string(from: Date()).prefix(10)) + ".log")
        if !FileManager.default.fileExists(atPath: url.path) { FileManager.default.createFile(atPath: url.path, contents: nil) }
        guard let h = try? FileHandle(forWritingTo: url) else { return }
        _ = try? h.seekToEnd()
        h.write((String(format: "%.3f ", Date().timeIntervalSince1970) + chunk.map { String(format: "%02X", $0) }.joined() + "\n").data(using: .utf8)!)
        try? h.close()
    }

    // MARK: internals
    // Connect options used everywhere: ask iOS to notify us on disconnect, and (iOS 17+) to auto-re-establish the link
    // when the ring comes back into range — the OS handles the reconnect even while the app is suspended, so we never
    // run an app-side timeout/rescan loop (the #1 cause of overnight connect/disconnect flapping). See the device
    // reliability research (Apple CoreBluetooth docs).
    private var connectOpts: [String: Any] {
        // Plain notify-on-disconnect — the exact options that streamed cleanly before. CBConnectPeripheralOption-
        // EnableAutoReconnect was tried (iOS 17+) to harden the overnight link, but on this ring iOS rejects it with
        // "One or more parameters were invalid.", so EVERY connect() failed. Overnight resilience does not need it:
        // the didDisconnect handler issues a no-timeout pending connect() that iOS honours even while suspended, so
        // the link re-establishes on its own when the ring is back in range.
        return [CBConnectPeripheralOptionNotifyOnDisconnectionKey: true]
    }
    private func attach(_ p: CBPeripheral) {
        central.stopScan(); ring = p; p.delegate = self
        setupDone = false; writeC = nil                        // clean setup for every (re)attach
        UserDefaults.standard.set(p.identifier.uuidString, forKey: Self.rememberKey)
        set("connecting")
        // A ring from retrieveConnectedPeripherals is ALREADY connected at the system level. Calling connect() on an
        // already-.connected peripheral does not reliably re-fire didConnect, so discoverServices never runs and no
        // frames arrive (the "found system-connected, 0 frames" stuck state). Discover directly on a live link —
        // same pattern the state-restoration path uses — and only issue a real connect() for a disconnected ring.
        if p.state == .connected {
            log("attach: already system-connected — discovering services directly")
            p.discoverServices([Self.service])
        } else {
            log("attach: state=\(p.state.rawValue) — issuing connect()")
            central.connect(p, options: connectOpts)
            // Watchdog: if iOS still hasn't given us a live link in 6 s, the ring's single GATT slot is held elsewhere
            // (a stale iOS bond). Cancel the pending request and retry a clean connect so it can't wedge forever.
            let target = p
            DispatchQueue.main.asyncAfter(deadline: .now() + 6) { [weak self] in
                guard let self, self.ring === target, self.state == "connecting", target.state != .connected else { return }
                self.log("connect pending >6s (state=\(target.state.rawValue)) — cancelling + retrying")
                self.central.cancelPeripheralConnection(target)
                self.central.connect(target, options: self.connectOpts)
            }
        }
    }
    private func set(_ s: String) { state = s; publish() }
    private func publish() { emit?("onRingStatus", status()) }

    /// Strip a personal name before it reaches the debug log (adopted from NOOP's logSafeDeviceName): keep only a known
    /// model token, so "Aarav's Ring" is logged as "RING" and no PII lands on disk.
    func safeName(_ s: String?) -> String {
        let n = (s ?? "").uppercased()
        for t in ["TK3040", "RING", "SMART", "YC", "BR", "R0", "TK"] where n.contains(t) { return t }
        return n.isEmpty ? "?" : "device"
    }

    /// Keep a Documents subfolder bounded: delete the oldest files beyond `keep` (NOOP's size-bounded eviction). Stops
    /// ring-raw captures and hourly ring-debug logs from growing unbounded on the device.
    func pruneDir(_ name: String, keep: Int) {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent(name)
        guard let files = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.contentModificationDateKey]), files.count > keep else { return }
        let sorted = files.sorted { a, b in
            let da = (try? a.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            let db = (try? b.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            return da < db
        }
        for f in sorted.prefix(sorted.count - keep) { try? FileManager.default.removeItem(at: f) }
    }

    func log(_ line: String) {
        let hour = String(ISO8601DateFormatter().string(from: Date()).prefix(13))
        if hour != debugHour || debug == nil {
            try? debug?.close()
            let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("ring-debug")
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            pruneDir("ring-debug", keep: 48)          // ~2 days of hourly logs
            let url = dir.appendingPathComponent(hour.replacingOccurrences(of: ":", with: "-") + ".log")
            if !FileManager.default.fileExists(atPath: url.path) { FileManager.default.createFile(atPath: url.path, contents: nil) }
            debug = try? FileHandle(forWritingTo: url); _ = try? debug?.seekToEnd(); debugHour = hour
        }
        debug?.write("\(String(format: "%.3f", Date().timeIntervalSince1970)) \(line)\n".data(using: .utf8)!)
    }
}

/// Automatic sleep detection — starts and stops the night without a tap, from whichever devices are present.
/// • Patch alone: its own estimate (HR vs resting, HRV, motion) says "asleep" for 15 min.
/// • Ring alone: still for 20 min (live motion counters, streamed from 20:00 — no PPG, so cheap) with HR near resting.
/// • Both: either one starts the night; stopping needs positive evidence you are up (phone walking, ring moving ≥ 10 min, or patch awake 15 min with the phone in hand) after 05:00, or a 13:00 hard stop. A dropped link never ends the night.
/// Runs natively, driven by the ring's 10-s heartbeat and the patch's metric frames, so it works with the phone locked.
final class KYSleepAuto {
    static let shared = KYSleepAuto()
    static let enabledKey = "telomy.autoSleep"
    var enabled: Bool { UserDefaults.standard.object(forKey: Self.enabledKey) as? Bool ?? true }
    private(set) var active = false            // we started tonight's session
    private var bandAsleepSince: Double?, bandAwakeSince: Double?, startedAt = 0.0, cooldownUntil = 0.0
    private var ours = false                   // true only for a night auto-detection started (false-start cancel applies)

    // Phone motion coprocessor: Apple's on-device activity classifier, with ~7 days of history readable even for
    // periods the app wasn't running. Third signal for sleep (phone still = in bed/away) and the wake signal (walking).
    private let motion = CMMotionActivityManager()
    private var phoneStillSince: Double?, phoneWalking = false, lastPhoneQuery = 0.0, phoneOnlyStart: Double?

    private func refreshPhone() {
        guard CMMotionActivityManager.isActivityAvailable() else { return }
        let now = Date()
        guard now.timeIntervalSince1970 - lastPhoneQuery > 120 else { return }
        lastPhoneQuery = now.timeIntervalSince1970
        motion.queryActivityStarting(from: now.addingTimeInterval(-3 * 3600), to: now, to: .main) { [weak self] acts, _ in
            guard let self, let acts, !acts.isEmpty else { return }
            var since: Date?
            for a in acts.reversed() {                   // walk back to the start of the current still stretch
                if (a.walking || a.running || a.cycling || a.automotive) && a.confidence != .low { break }
                if a.stationary { since = a.startDate }
            }
            self.phoneStillSince = since?.timeIntervalSince1970
            let last = acts.last!
            self.phoneWalking = (last.walking || last.running) && last.confidence != .low
        }
    }

    /// Phone activity segments for the last `hours` (merged runs of the same type) — for the day's activity timeline.
    static func phoneActivity(hours: Double, done: @escaping ([[String: Any]]) -> Void) {
        guard CMMotionActivityManager.isActivityAvailable() else { done([]); return }
        let now = Date()
        shared.motion.queryActivityStarting(from: now.addingTimeInterval(-hours * 3600), to: now, to: .main) { acts, _ in
            var out: [[String: Any]] = []
            let list = acts ?? []
            for (i, a) in list.enumerated() {
                let type = a.running ? "running" : a.cycling ? "cycling" : a.automotive ? "driving" : a.walking ? "walking" : a.stationary ? "still" : "unknown"
                let end = i + 1 < list.count ? list[i + 1].startDate : now
                if var lastSeg = out.last, lastSeg["type"] as? String == type { lastSeg["end"] = end.timeIntervalSince1970; out[out.count - 1] = lastSeg }
                else { out.append(["type": type, "start": a.startDate.timeIntervalSince1970, "end": end.timeIntervalSince1970, "confidence": a.confidence.rawValue]) }
            }
            done(out.filter { (($0["end"] as? Double ?? 0) - ($0["start"] as? Double ?? 0)) >= 60 })
        }
    }

    func band(sleep: String, activity: String) {
        let now = Date().timeIntervalSince1970
        if sleep == "asleep" { bandAsleepSince = bandAsleepSince ?? now; bandAwakeSince = nil }
        else if sleep == "awake" || activity == "active" || activity == "moving" { bandAwakeSince = bandAwakeSince ?? now; bandAsleepSince = nil }
        evaluate()
    }

    func evaluate() {
        guard enabled else { return }
        refreshPhone()
        let now = Date().timeIntervalSince1970, hour = Calendar.current.component(.hour, from: Date())
        let ring = KYRing.shared
        let resting = UserDefaults.standard.double(forKey: "ky.restingHr")
        let phoneStill = phoneStillSince.map { now - $0 } ?? 0
        let wearable = ring.state == "connected" || KYBand.shared.status()["state"] as? String != "idle"
        // Phone only (no wearable on): we can't record physiology, but a long still stretch at night is a usable
        // in-bed window — logged to the wellness store as a low-confidence sleep estimate when it ends.
        if !wearable {
            if phoneOnlyStart == nil, hour >= 21 || hour < 4, phoneStill >= 45 * 60 { phoneOnlyStart = phoneStillSince }
            if let st = phoneOnlyStart, phoneWalking, now - st > 3 * 3600 {
                KYWellnessStore.append(kind: "events", record: ["kind": "sleep_estimate", "label": "Sleep window (phone motion)",
                    "t": st, "end": now, "source": "phone-motion", "confidence": "low"])
                phoneOnlyStart = nil
            }
            return
        }
        // A manually started overnight session is adopted: it gets the same morning stop as an automatic one.
        if !active, isOvernightTherapy(KYBand.shared.captureMeta?["therapyId"]) {
            active = true; ours = false; startedAt = KYBand.shared.captureMeta?["startedAt"] as? Double ?? now
            ring.log("auto-sleep: adopted a running overnight session")
        }
        if !active {
            // Stricter onset (2026-10-15: a still ring at a desk late at night was mistaken for sleep).
            // 21:00–06:00 (2026-10-19: asleep at 03:02 and nothing recorded — the old 22–04 window and rules missed it)
            guard hour >= 21 || hour < 6, now >= cooldownUntil else { return }
            let bandSays = bandAsleepSince.map { now - $0 >= 20 * 60 } ?? false          // ECG-based: the strongest signal
            // The patch only streams during a recording, so its own "asleep" estimate can't start the first one
            // (2026-10-19: patch on skin all night, never streamed). Patch on skin + phone lying still 20 min at night
            // starts the recording; the false-start rule below cancels it if you're actually up.
            let b = KYBand.shared.status()
            let patchOn = (b["leadOn"] as? Bool) == true && ["connected", "streaming"].contains(b["state"] as? String ?? "")
            let patchSays = patchOn && phoneStill >= 20 * 60
            // Ring: live HR is rarely available at night — fall back to the newest flash-log HR (≤ 15 min old)
            let hrNow = ring.lastHR.map(Double.init) ?? ring.recentHistoryHR(maxAge: 15 * 60)
            let hrLow = hrNow.map { resting >= 30 && $0 <= resting + 3 } ?? false
            let ringSays = ring.state == "connected" && (ring.stillSeconds >= 30 * 60 || phoneStill >= 40 * 60) && hrLow && phoneStill >= 30 * 60
            guard bandSays || patchSays || ringSays else { return }
            active = true; ours = true; startedAt = now
            ring.log("auto-sleep: onset detected (band=\(bandSays) patch=\(patchSays) ring=\(ringSays)) — starting the night")
            KYRing.shared.startOvernight()
            KYBand.shared.stopContinuousIfRunning()      // all-day record hands over to the overnight capture
            if KYBand.shared.captureId == nil, KYBand.shared.status()["state"] as? String != "idle" {
                _ = KYBand.shared.startCapture(meta: ["therapy": "Overnight sleep", "therapyId": "sleep", "settings": [:],
                    "pre": [:], "firstPhase": "baseline", "tz": TimeZone.current.identifier, "autoStarted": true])
            }
            return
        }
        // False start: clearly up and about within the first 2 h → cancel, and don't re-arm for 45 min.
        if ours, now - startedAt < 2 * 3600, (bandAwakeSince.map { now - $0 >= 10 * 60 } ?? false) || phoneWalking || ring.movingSeconds >= 3 * 60 {
            active = false; cooldownUntil = now + 45 * 60
            ring.log("auto-sleep: false start — you're up; cancelled")
            ring.stopOvernight()
            if (KYBand.shared.captureMeta?["autoStarted"] as? Bool) == true { _ = KYBand.shared.stopCapture(extra: ["autoStopped": true, "falseStart": true]) }
            return
        }
        do {
            // Morning stop needs POSITIVE evidence of being up. 2026-10-18: the ring dropped its link in the early morning and the
            // patch's own estimate flickered to "awake" — the old rule read "ring not connected" as "up" and ended the
            // night while the WHOOP showed ~4 more hours of sleep. A lost link, or a heart-rate-only "awake", is not waking.
            let ringMoving = ring.state == "connected" && ring.movingSeconds >= 10 * 60
            let bandUpMoving = bandAwakeSince.map { now - $0 >= 15 * 60 } ?? false
            let up = phoneWalking || ringMoving || (bandUpMoving && phoneStill < 10 * 60)   // patch awake AND phone handled
            let morning = hour >= 5 && hour < 12 && now - startedAt > 3 * 3600
            guard (morning && up) || (hour >= 13 && hour < 20) else { return }
            active = false
            ring.log("auto-sleep: wake detected — ending the night")
            // the ring finalises its own sleep record some time after waking (2026-10-19: record stopped at 05:08,
            // asleep to 07:01) — pull the sleep log again later so the complete record is captured
            for delay in [30.0 * 60, 90.0 * 60] {
                DispatchQueue.main.asyncAfter(deadline: .now() + delay) { KYRing.shared.syncHistory() }
            }
            ring.stopOvernight()
            if isOvernightTherapy(KYBand.shared.captureMeta?["therapyId"]) { _ = KYBand.shared.stopCapture(extra: ["autoStopped": true]) }
        }
    }
}

extension KYRing: CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ c: CBCentralManager) {
        guard c.state == .poweredOn else { set("off"); return }
        // After iOS relaunches us in the background (state restoration) the peripheral may still be connected, but we
        // have lost our characteristics and setup. Previously we left it half-alive — "connected" in iOS, dead in the
        // app — which looked like a disconnect. Re-discover on a live link; re-arm a pending connect otherwise.
        if let p = ring {
            p.delegate = self; setupDone = false; writeC = nil
            if p.state == .connected { log("restored live link — rediscovering"); set("connecting"); p.discoverServices([Self.service]) }
            else { log("restored peripheral — pending reconnect"); set("connecting"); central.connect(p, options: connectOpts) }
        } else { autoConnect() }
    }
    func centralManager(_ c: CBCentralManager, willRestoreState dict: [String: Any]) {
        if let p = (dict[CBCentralManagerRestoredStatePeripheralsKey] as? [CBPeripheral])?.first { ring = p; p.delegate = self; log("willRestoreState") }
    }
    func centralManager(_ c: CBCentralManager, didDiscover p: CBPeripheral, advertisementData ad: [String: Any], rssi: NSNumber) {
        let name = (ad[CBAdvertisementDataLocalNameKey] as? String) ?? p.name ?? ""
        let uuids = (ad[CBAdvertisementDataServiceUUIDsKey] as? [CBUUID]) ?? []
        let n = name.uppercased()
        let isRing = uuids.contains(Self.service) || n.contains("TK") || n.contains("RING") || n.contains("R0")
            || n.contains("SMART") || n.contains("YC") || n.contains("BR")
        guard isRing else { return }
        deviceName = name.isEmpty ? "Ring" : name
        emit?("onRingDevice", ["id": p.identifier.uuidString, "name": deviceName, "rssi": rssi.intValue])
        attach(p)                                              // connect the first ring we recognise
    }
    func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) { log("didConnect — discovering services"); p.discoverServices([Self.service]) }
    func centralManager(_ c: CBCentralManager, didFailToConnect p: CBPeripheral, error: Error?) {
        log("didFailToConnect err=\(error?.localizedDescription ?? "none") — retrying in 2s")
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in                 // back off: never spin
            guard let self, self.ring === p, p.state != .connected else { return }
            self.central.connect(p, options: self.connectOpts)
        }
    }
    func centralManager(_ c: CBCentralManager, didDisconnectPeripheral p: CBPeripheral, error: Error?) {
        writeC = nil; stopAutoSync()
        log("disconnected err=\(error?.localizedDescription ?? "none") — issuing pending reconnect")
        // A pending connect() (no timeout) is honoured by iOS even while the app is suspended: when the ring comes
        // back into range — including with the screen off — the system reconnects and wakes us via CoreBluetooth.
        // This is why the link no longer drops on screen-off; a delayed re-scan can't run while suspended.
        if ring === p || ring == nil {
            ring = p; p.delegate = self
            central.connect(p, options: connectOpts)
            set("connecting")
        } else {
            set("idle"); DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in self?.autoConnect() }
        }
    }
}

extension KYRing: CBPeripheralDelegate {
    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        log("didDiscoverServices err=\(error?.localizedDescription ?? "none") svcs=\((p.services ?? []).map { $0.uuid.uuidString.prefix(8) }.joined(separator: ","))")
        for s in p.services ?? [] where s.uuid == Self.service { p.discoverCharacteristics(nil, for: s) }
    }
    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        for c in s.characteristics ?? [] {
            let pr = c.properties
            log("char \(c.uuid.uuidString.prefix(8)) props=\(pr.rawValue)")
            if c.uuid == Self.writeCh || (writeC == nil && (pr.contains(.write) || pr.contains(.writeWithoutResponse))) {
                writeC = c
                writeType = pr.contains(.writeWithoutResponse) ? .withoutResponse : .withResponse
            }
            if pr.contains(.notify) || pr.contains(.indicate) { p.setNotifyValue(true, for: c); notifySubs += 1 }
        }
    }

    func peripheral(_ p: CBPeripheral, didUpdateNotificationStateFor c: CBCharacteristic, error: Error?) {
        log("notify enabled=\(c.isNotifying) on \(c.uuid.uuidString.prefix(8)) err=\(error?.localizedDescription ?? "none")")
        guard !setupDone, writeC != nil else { return }        // fires once per characteristic; set up only once
        setupDone = true
        set("connected")
        send(0x0100, makeTime())
        probe()
        startAutoSync()                        // enable on-device monitoring + begin periodic history backfill
        if overnight { send(0x0309, [0x01, 0x01, 0x02]); send(0x0309, [0x01, 0x00, 0x02]); log("overnight re-armed after reconnect") }
        else if live { setLive(true); log("live HR re-armed after reconnect") }   // restore the foreground live stream
    }
    private func probe() {
        guard battery < 0, probes < 6 else { return }
        probes += 1
        readBattery()
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in self?.probe() }
    }
    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        if let d = c.value, !d.isEmpty { log("note \(c.uuid.uuidString.prefix(8))"); onBytes([UInt8](d)) }
    }
    func peripheral(_ p: CBPeripheral, didWriteValueFor c: CBCharacteristic, error: Error?) {
        if let e = error { log("write err \(e.localizedDescription)") }
    }

    private func makeTime() -> [UInt8] {
        let d = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute, .second], from: Date())
        let y = d.year ?? 2026
        return [UInt8(y & 0xFF), UInt8((y >> 8) & 0xFF), UInt8(d.month ?? 1), UInt8(d.day ?? 1),
                UInt8(d.hour ?? 0), UInt8(d.minute ?? 0), UInt8(d.second ?? 0)]
    }
}
