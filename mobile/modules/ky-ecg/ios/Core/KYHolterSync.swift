import Foundation

/// Downloads the on-device recording: ask for the frame count, request frames from the next missing index, append frames in order
/// to a `.holter` file (238 bytes per frame), re-request on any gap, resume from a partial file, and end the read session.
public final class KYHolterSync {
    public enum Event: Equatable {
        case started(totalFrames: Int, resumingFrom: Int)
        case progress(received: Int, total: Int)
        case completed(URL, frames: Int)
        case failed(String)
    }

    public let fileURL: URL
    public private(set) var total = -1
    public private(set) var received = 0
    public private(set) var rerequests = 0
    private var handle: FileHandle?
    private let send: (KYPacket) -> Void
    private let onEvent: (Event) -> Void
    private var active = false
    private var lastProgress = Date.distantPast
    private var watchdog: Timer?
    /// Frame size in bytes, learned from the first frame (or from an existing partial file).
    public private(set) var frameSize: Int?

    public init(fileURL: URL, send: @escaping (KYPacket) -> Void, onEvent: @escaping (Event) -> Void) {
        self.fileURL = fileURL
        self.send = send
        self.onEvent = onEvent
    }

    public func start() {
        active = true
        if !FileManager.default.fileExists(atPath: fileURL.path) { FileManager.default.createFile(atPath: fileURL.path, contents: nil) }
        let size = ((try? FileManager.default.attributesOfItem(atPath: fileURL.path)[.size] as? Int) ?? 0) ?? 0
        frameSize = size > 0 ? KYHolterFile.detectFrameSize(at: fileURL) : nil
        received = frameSize.map { size / $0 } ?? 0
        handle = try? FileHandle(forWritingTo: fileURL)
        _ = try? handle?.seek(toOffset: UInt64(received * (frameSize ?? 0)))
        send(KYRequest.holterFrameCount)
    }

    public func cancel() { finish(nil, failure: "Cancelled") }

    /// Feed every message from the client; returns true if the message belonged to the sync.
    @discardableResult
    public func handle(_ m: KYMessage) -> Bool {
        guard active else { return false }
        switch m {
        case .holterFrameCount(let n):
            guard total < 0 else { return true }
            guard n >= 0 else { finish(nil, failure: "The band did not report how much it recorded."); return true }
            total = n
            received = min(received, n)
            onEvent(.started(totalFrames: n, resumingFrom: received))
            if received >= n { finish(fileURL, failure: nil); return true }
            requestNext()
            startWatchdog()
            return true
        case .holterFrame(let f):
            lastProgress = Date()
            if frameSize == nil { frameSize = f.raw.count }
            if f.index == received {
                guard f.raw.count == frameSize else { finish(nil, failure: "Frame size changed mid-sync (\(f.raw.count) vs \(frameSize ?? 0) bytes)"); return true }
                handle?.write(Data(f.raw))
                received += 1
                if received % 20 == 0 || received == total { onEvent(.progress(received: received, total: total)) }
                if received >= total { finish(fileURL, failure: nil) }
            } else if f.index > received {
                rerequests += 1
                requestNext()  // a frame was skipped: ask again from the first missing one
            }
            return true
        default:
            return false
        }
    }

    private func requestNext() { send(KYRequest.holterRead(from: received)) }

    private func startWatchdog() {
        lastProgress = Date()
        watchdog?.invalidate()
        watchdog = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            guard let self, self.active else { return }
            if Date().timeIntervalSince(self.lastProgress) > 4 { self.rerequests += 1; self.lastProgress = Date(); self.requestNext() }
        }
    }

    private func finish(_ url: URL?, failure: String?) {
        guard active else { return }
        active = false
        watchdog?.invalidate()
        try? handle?.close()
        send(KYRequest.holterReadEnd)
        if let url { onEvent(.completed(url, frames: received)) } else { onEvent(.failed(failure ?? "Sync failed")) }
    }
}

/// Reads a `.holter` file (fixed-size frames, size detected from the sequential frame indices) back into samples.
public enum KYHolterFile {
    public static func detectFrameSize(at url: URL) -> Int? {
        guard let data = try? [UInt8](Data(contentsOf: url)) else { return nil }
        return detectFrameSize(data)
    }

    static func detectFrameSize(_ d: [UInt8]) -> Int? {
        func index(_ o: Int) -> Int { Int(d[o]) | Int(d[o + 1]) << 8 | Int(d[o + 2]) << 16 }
        return KYHolterFrame.knownSizes.first { size in
            guard d.count >= size, d.count % size == 0 else { return false }
            let n = min(d.count / size, 5)
            let first = index(0)
            return (0..<n).allSatisfy { index($0 * size) == first + $0 }
        }
    }

    public static func frames(at url: URL) throws -> [KYHolterFrame] {
        let data = [UInt8](try Data(contentsOf: url))
        guard let size = detectFrameSize(data) else { return [] }
        return stride(from: 0, to: data.count - size + 1, by: size).compactMap { KYHolterFrame(payload: Array(data[$0..<$0 + size])) }
    }
}
