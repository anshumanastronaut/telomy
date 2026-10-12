import Foundation

/// Wire protocol of the KY-E-B1 band (see PROTOCOL.md).
///
/// Frame: `0xBC | cmd | len (UInt16 LE) | checksum (UInt16 LE) | payload[len]`
/// checksum = sum of payload bytes, truncated to 16 bits. An empty payload has len = 0 and checksum = 0.
public enum KYCommand: UInt8, CaseIterable {
    case deviceInfo = 0x10
    case deviceUnixTime = 0x11
    case measTag = 0x22
    case measFlash = 0x23
    case measStatus = 0x24
    case measData = 0x25
    case measSN = 0x26
    case measCont = 0x27
    case measIndex = 0x28
    case connParamSet = 0x2A
    case connParamSetAndroid = 0x2B
    case measFlashDescription = 0x2C
    case measTime = 0x2D
    case ecgControl = 0x30
    case ecgData = 0x31
    case ecgStatus = 0x32
    case ecgAccel = 0x33
    case factorySN = 0x55
}

public struct KYPacket: Equatable {
    public static let magic: UInt8 = 0xBC
    public static let headerSize = 6

    public let command: UInt8
    public let payload: [UInt8]

    public init(command: UInt8, payload: [UInt8] = []) {
        self.command = command
        self.payload = payload
    }

    public init(_ command: KYCommand, payload: [UInt8] = []) {
        self.init(command: command.rawValue, payload: payload)
    }

    public static func checksum(_ payload: [UInt8]) -> UInt16 {
        UInt16(truncatingIfNeeded: payload.reduce(0) { $0 + Int($1) })
    }

    public var encoded: [UInt8] {
        let len = UInt16(payload.count)
        let sum = KYPacket.checksum(payload)
        return [KYPacket.magic, command,
                UInt8(len & 0xFF), UInt8(len >> 8),
                UInt8(sum & 0xFF), UInt8(sum >> 8)] + payload
    }
}

/// Reassembles notification chunks into packets. Tolerates a packet split across several notifications and several
/// packets in one notification; drops bytes until the next magic byte if the stream is corrupt.
public struct KYPacketDecoder {
    private var buffer: [UInt8] = []
    public private(set) var droppedBytes = 0
    public private(set) var badChecksums = 0

    public init() {}

    public mutating func feed(_ chunk: [UInt8]) -> [KYPacket] {
        buffer += chunk
        var out: [KYPacket] = []
        while true {
            if let start = buffer.firstIndex(of: KYPacket.magic), start > 0 {
                droppedBytes += start
                buffer.removeFirst(start)
            } else if buffer.first != KYPacket.magic {
                droppedBytes += buffer.count
                buffer.removeAll()
                return out
            }
            guard buffer.count >= KYPacket.headerSize else { return out }
            let len = Int(buffer[2]) | Int(buffer[3]) << 8
            let sum = UInt16(buffer[4]) | UInt16(buffer[5]) << 8
            let total = KYPacket.headerSize + len
            guard buffer.count >= total else { return out }
            let payload = Array(buffer[KYPacket.headerSize..<total])
            if KYPacket.checksum(payload) == sum {
                out.append(KYPacket(command: buffer[1], payload: payload))
                buffer.removeFirst(total)
            } else {
                badChecksums += 1
                buffer.removeFirst(1)  // resync on the next magic byte
            }
        }
    }
}

// MARK: - Requests

public enum KYRequest {
    /// Connection-parameter handshake sent right after notifications are enabled (the vendor's Android SDK sends this with an empty payload).
    public static let connectionHandshake = KYPacket(.connParamSet)
    public static let deviceInfo = KYPacket(.deviceInfo)
    public static let leadState = KYPacket(.ecgStatus)
    public static let holterState = KYPacket(.measStatus)
    public static let serialNumber = KYPacket(.measSN)

    /// Start/stop on-device ("Holter") recording for up to `durationSec` seconds (UInt24 LE), no motion channel.
    public static func holter(start: Bool, durationSec: Int = 24 * 3600) -> KYPacket {
        let d = max(0, min(durationSec, 0xFF_FFFF))
        return KYPacket(.measTag, payload: [start ? 1 : 0, UInt8(d & 0xFF), UInt8((d >> 8) & 0xFF), UInt8((d >> 16) & 0xFF), 0])
    }

    /// Get (`unixTime == nil`) or set the recording start time; setting 0 clears it (the vendor app clears it after a sync).
    public static func holterTime(set unixTime: UInt32? = nil) -> KYPacket {
        let t = unixTime ?? 0
        return KYPacket(.measTime, payload: [unixTime == nil ? 0 : 1, UInt8(t & 0xFF), UInt8((t >> 8) & 0xFF), UInt8((t >> 16) & 0xFF), UInt8(t >> 24)])
    }

    /// Number of 238-byte frames stored in flash (reply: UInt32 LE on the same command).
    public static let holterFrameCount = KYPacket(.measCont)

    /// Ask the band to stream stored frames starting at `index` (UInt24 LE). Frames arrive on 0x23.
    public static func holterRead(from index: Int) -> KYPacket {
        KYPacket(.measFlash, payload: [UInt8(index & 0xFF), UInt8((index >> 8) & 0xFF), UInt8((index >> 16) & 0xFF)])
    }

    /// End a flash read session.
    public static let holterReadEnd = KYPacket(.measFlashDescription)

    /// Start/stop live ECG on a B1 band. Duration is a 24-bit little-endian number of seconds.
    public static func ecg(start: Bool, durationSec: Int) -> KYPacket {
        let d = max(0, min(durationSec, 0xFF_FFFF))
        return KYPacket(.ecgControl, payload: [start ? 1 : 2, UInt8(d & 0xFF), UInt8((d >> 8) & 0xFF), UInt8((d >> 16) & 0xFF)])
    }
}

// MARK: - Responses

public struct KYDeviceInfo: Equatable {
    public let battery: Int
    public let hardwareVersion: String
    public let firmwareVersion: String
    public let adcReference: Int?

    public init?(payload p: [UInt8]) {
        guard p.count >= 2 else { return nil }
        battery = Int(p[0])
        let hwLen = Int(p[1])
        hardwareVersion = hwLen > 0 && 2 + hwLen <= p.count ? String(decoding: p[2..<2 + hwLen], as: UTF8.self) : ""
        var o = 2 + hwLen
        let fwLen = o < p.count ? Int(p[o]) : 0
        o += 1
        firmwareVersion = fwLen > 0 && o + fwLen <= p.count ? String(decoding: p[o..<o + fwLen], as: UTF8.self) : ""
        o += fwLen
        adcReference = o + 1 < p.count ? Int(p[o]) << 8 | Int(p[o + 1]) : nil
    }
}

public struct KYLeadState: Equatable {
    public let isLeadOn: Bool
    public let dropCount: Int
    public init?(payload p: [UInt8]) {
        guard let first = p.first else { return nil }
        isLeadOn = first == 1
        dropCount = p.count > 1 ? Int(p[1]) : 0
    }
}

/// Reply to an ECG start/stop request. `intervalMs` is the sample interval, so sample rate = 1000 / intervalMs.
public struct KYEcgConfig: Equatable {
    public let status: Int
    public let intervalMs: Int
    public let gain: Int
    public var sampleRateHz: Double? { intervalMs > 0 ? 1000.0 / Double(intervalMs) : nil }
    public init(payload p: [UInt8]) {
        status = p.count > 0 ? Int(p[0]) : 0
        intervalMs = p.count > 1 ? Int(p[1]) : 0
        gain = p.count > 2 ? Int(p[2]) : 0
    }
}

/// One frame of live ECG. Samples are signed 16-bit raw values; the vendor documents the unit as 0.001 mV (µV).
public struct KYEcgFrame: Equatable {
    public let frameIndex: Int
    public let samples: [Int16]
    public init?(payload p: [UInt8]) {
        guard p.count >= 4 else { return nil }
        frameIndex = Int(p[0]) | Int(p[1]) << 8 | Int(p[2]) << 16
        var s: [Int16] = []
        s.reserveCapacity((p.count - 4) / 2)
        var i = 4
        while i + 1 < p.count {
            s.append(Int16(bitPattern: UInt16(p[i]) | UInt16(p[i + 1]) << 8))
            i += 2
        }
        samples = s
    }
}

public enum KYHolterState: Int, Equatable {
    case off = 0, single, sleep, continuous, readingFlash, charging, lowBattery
    case unknown = 255
}

/// One stored frame: UInt24 index, event marker, then int16 samples (µV). Firmware B1_1.00.39 stores 87 samples (178 bytes),
/// the same as the live stream; the vendor SDK documents 117 samples (238 bytes) for other firmware.
public struct KYHolterFrame: Equatable {
    public static let knownSizes = [178, 238]
    public let index: Int
    public let event: Int
    public let samples: [Int16]
    public let raw: [UInt8]
    public init?(payload p: [UInt8]) {
        guard p.count >= 4 else { return nil }
        index = Int(p[0]) | Int(p[1]) << 8 | Int(p[2]) << 16
        event = Int(p[3])
        var s: [Int16] = []
        var i = 4
        while i + 1 < p.count { s.append(Int16(bitPattern: UInt16(p[i]) | UInt16(p[i + 1]) << 8)); i += 2 }
        samples = s
        raw = p
    }
}

public enum KYMessage: Equatable {
    case deviceInfo(KYDeviceInfo)
    case leadState(KYLeadState)
    case ecgConfig(KYEcgConfig)
    case ecgFrame(KYEcgFrame)
    case holterState(KYHolterState)
    case holterTime(UInt32?)
    case holterFrameCount(Int)
    case holterFrame(KYHolterFrame)
    case other(command: UInt8, payload: [UInt8])

    public init(_ packet: KYPacket) {
        switch KYCommand(rawValue: packet.command) {
        case .deviceInfo: self = KYDeviceInfo(payload: packet.payload).map(KYMessage.deviceInfo) ?? .other(command: packet.command, payload: packet.payload)
        case .ecgStatus: self = KYLeadState(payload: packet.payload).map(KYMessage.leadState) ?? .other(command: packet.command, payload: packet.payload)
        case .ecgControl: self = .ecgConfig(KYEcgConfig(payload: packet.payload))
        case .measStatus: self = .holterState(KYHolterState(rawValue: Int(packet.payload.first ?? 255)) ?? .unknown)
        case .measTime:
            let p = packet.payload
            if p.count >= 4 {
                let t = UInt32(p[0]) | UInt32(p[1]) << 8 | UInt32(p[2]) << 16 | UInt32(p[3]) << 24
                self = .holterTime(t == 0 || t == .max ? nil : t)
            } else { self = .holterTime(nil) }
        case .measCont:
            let p = packet.payload
            self = p.count >= 4 ? .holterFrameCount(Int(UInt32(p[0]) | UInt32(p[1]) << 8 | UInt32(p[2]) << 16 | UInt32(p[3]) << 24)) : .holterFrameCount(-1)
        case .measFlash: self = KYHolterFrame(payload: packet.payload).map(KYMessage.holterFrame) ?? .other(command: packet.command, payload: packet.payload)
        case .ecgData: self = KYEcgFrame(payload: packet.payload).map(KYMessage.ecgFrame) ?? .other(command: packet.command, payload: packet.payload)
        default: self = .other(command: packet.command, payload: packet.payload)
        }
    }
}
