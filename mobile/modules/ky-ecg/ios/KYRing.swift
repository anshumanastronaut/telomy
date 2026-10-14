import CoreBluetooth
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
    private(set) var lastSpO2: Int?
    private(set) var lastTemp: Double?
    private(set) var deviceName = ""

    private override init() { super.init(); central = CBCentralManager(delegate: self, queue: .main,
        options: [CBCentralManagerOptionRestoreIdentifierKey: "telomy.ring", CBCentralManagerOptionShowPowerAlertKey: true]) }

    // MARK: public API
    func status() -> [String: Any] {
        var s: [String: Any] = ["state": state, "battery": battery, "name": deviceName]
        if let v = lastHR { s["hr"] = v }
        if let v = lastSpO2 { s["spo2"] = v }
        if let v = lastTemp { s["temp"] = v }
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
                log("found system-connected \(p.name ?? "?")"); attach(p); return
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

    /// Start a live measurement. type: 1 = heart rate, 2 = SpO₂, 4 = temperature (verified for 2 and 4).
    func startMeasure(_ type: Int) {
        send(0x032F, [0x01, UInt8(type & 0xFF)])          // configure real-time acquisition of <type>
        send(0x0309, [0x00, 0x00, UInt8(type & 0xFF)])    // start measurement <type>
    }
    func stopMeasure(_ type: Int) {
        send(0x040E, [0x00])
        send(0x032F, [0x00, UInt8(type & 0xFF)])
    }
    func readBattery() { send(0x0200, [0x47, 0x43]) }     // device info (battery at payload[5])

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

    private func send(_ code: UInt16, _ payload: [UInt8]) {
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
        if code != 0xFFFF { log("rx " + f.map { String(format: "%02X", $0) }.joined()) }
        switch code {
        case 0x0200:                                           // device info
            if payload.count > 5 { battery = Int(payload[5]); deviceName = "Ring" }
        case 0x0602:                                           // SpO₂ real-time
            if let v = payload.first, v > 0 { lastSpO2 = Int(v) }
        case 0x0601:                                           // heart rate real-time
            if let v = payload.first, v > 0 { lastHR = Int(v) }
        case 0x060A:                                           // temperature real packet (value at [12],[13])
            if payload.count > 13, payload[12] >= 20, payload[12] <= 45 { lastTemp = Double(payload[12]) + Double(payload[13]) / 10 }
        case 0x0600: break                                     // sport (steps/cal/distance)
        case 0xFFFF: return                                    // heartbeat
        default: break
        }
        emit?("onRingData", status())
        publish()
    }

    // MARK: internals
    private func attach(_ p: CBPeripheral) {
        central.stopScan(); ring = p; p.delegate = self
        UserDefaults.standard.set(p.identifier.uuidString, forKey: Self.rememberKey)
        set("connecting"); central.connect(p, options: nil)
    }
    private func set(_ s: String) { state = s; publish() }
    private func publish() { emit?("onRingStatus", status()) }

    func log(_ line: String) {
        let hour = String(ISO8601DateFormatter().string(from: Date()).prefix(13))
        if hour != debugHour || debug == nil {
            try? debug?.close()
            let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("ring-debug")
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            let url = dir.appendingPathComponent(hour.replacingOccurrences(of: ":", with: "-") + ".log")
            if !FileManager.default.fileExists(atPath: url.path) { FileManager.default.createFile(atPath: url.path, contents: nil) }
            debug = try? FileHandle(forWritingTo: url); _ = try? debug?.seekToEnd(); debugHour = hour
        }
        debug?.write("\(String(format: "%.3f", Date().timeIntervalSince1970)) \(line)\n".data(using: .utf8)!)
    }
}

extension KYRing: CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ c: CBCentralManager) { if c.state == .poweredOn { autoConnect() } else { set("off") } }
    func centralManager(_ c: CBCentralManager, willRestoreState dict: [String: Any]) {
        if let p = (dict[CBCentralManagerRestoredStatePeripheralsKey] as? [CBPeripheral])?.first { ring = p; p.delegate = self }
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
    func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) { p.discoverServices([Self.service]) }
    func centralManager(_ c: CBCentralManager, didDisconnectPeripheral p: CBPeripheral, error: Error?) {
        writeC = nil; set("idle"); DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in self?.autoConnect() }
    }
}

extension KYRing: CBPeripheralDelegate {
    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
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
        set("connected")
        send(0x0100, makeTime())
        probe()
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
