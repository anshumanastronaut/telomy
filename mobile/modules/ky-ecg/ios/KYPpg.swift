import AVFoundation
import Foundation

/// Camera photoplethysmography: back camera + torch, fingertip over the lens. For each frame we emit the average
/// R/G/B of a central patch and a timestamp (ms). JS (lib/ppg.ts) turns the stream into HR + HRV. Low preset and a
/// strided sample keep it light; the red channel carries the pulse in transmissive finger PPG.
final class KYPpg: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    static let shared = KYPpg()
    var emit: ((String, [String: Any]) -> Void)?

    // Finger-PPG doesn't need a bright torch — the LED sits right against the skin. A low level keeps a strong red
    // signal while staying cool enough to hold a fingertip on for the full minute (1.0 gets uncomfortably hot).
    private let torchLevel: Float = 0.6
    private let session = AVCaptureSession()
    private let queue = DispatchQueue(label: "telomy.ppg")
    private var device: AVCaptureDevice?
    private var t0: Double = -1
    private var running = false

    func start() {
        // Ask for camera access first; a notDetermined status otherwise yields a silent, frameless session.
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            queue.async { [weak self] in self?.configureAndStart() }
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                guard let self = self else { return }
                if granted { self.queue.async { self.configureAndStart() } }
                else { self.emit?("onPpgFrame", ["error": "denied"]) }
            }
        default:
            emit?("onPpgFrame", ["error": "denied"])
        }
    }

    private func configureAndStart() {
        if running { return }
        guard let dev = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            emit?("onPpgFrame", ["error": "no_camera"]); return
        }
        device = dev
        session.beginConfiguration()
        session.sessionPreset = .low
        do {
            let input = try AVCaptureDeviceInput(device: dev)
            if session.canAddInput(input) { session.addInput(input) }
        } catch { emit?("onPpgFrame", ["error": "camera_input"]); session.commitConfiguration(); return }
        let output = AVCaptureVideoDataOutput()
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
        output.alwaysDiscardsLateVideoFrames = true
        output.setSampleBufferDelegate(self, queue: queue)
        if session.canAddOutput(output) { session.addOutput(output) }
        session.commitConfiguration()
        do {
            try dev.lockForConfiguration()
            if dev.isExposureModeSupported(.continuousAutoExposure) { dev.exposureMode = .continuousAutoExposure }
            dev.activeVideoMinFrameDuration = CMTime(value: 1, timescale: 30)
            dev.activeVideoMaxFrameDuration = CMTime(value: 1, timescale: 30)
            dev.unlockForConfiguration()
        } catch {}
        t0 = -1
        running = true
        session.startRunning()
        // Torch must be asserted AFTER the session is running — setting it before startRunning() only blinks once,
        // because starting the session resets the torch. captureOutput re-asserts it if anything turns it back off.
        enableTorch()
    }

    private func enableTorch() {
        guard let dev = device, dev.hasTorch, dev.isTorchAvailable else { return }
        do { try dev.lockForConfiguration(); try dev.setTorchModeOn(level: torchLevel); dev.unlockForConfiguration() } catch {}
    }

    func stop() {
        queue.async { [weak self] in
            guard let self = self else { return }
            if self.session.isRunning { self.session.stopRunning() }
            if let dev = self.device, dev.hasTorch { try? dev.lockForConfiguration(); dev.torchMode = .off; dev.unlockForConfiguration() }
            self.session.inputs.forEach { self.session.removeInput($0) }
            self.session.outputs.forEach { self.session.removeOutput($0) }
            self.running = false
        }
    }

    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pb = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        CVPixelBufferLockBaseAddress(pb, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pb, .readOnly) }
        let w = CVPixelBufferGetWidth(pb), h = CVPixelBufferGetHeight(pb), bpr = CVPixelBufferGetBytesPerRow(pb)
        guard let base = CVPixelBufferGetBaseAddress(pb) else { return }
        let ptr = base.assumingMemoryBound(to: UInt8.self)
        var rs = 0.0, gs = 0.0, bs = 0.0, cnt = 0.0
        let x0 = w / 4, x1 = 3 * w / 4, y0 = h / 4, y1 = 3 * h / 4
        var y = y0
        while y < y1 {
            let row = ptr + y * bpr
            var x = x0
            while x < x1 { let px = row + x * 4; bs += Double(px[0]); gs += Double(px[1]); rs += Double(px[2]); cnt += 1; x += 4 }  // BGRA
            y += 4
        }
        if cnt == 0 { return }
        // Keep the torch lit for the whole read: if anything (auto-config, thermal) turned it off, turn it back on.
        if running, let dev = device, dev.hasTorch, dev.torchMode != .on, dev.isTorchAvailable { enableTorch() }
        let tms = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sampleBuffer)) * 1000
        if t0 < 0 { t0 = tms }
        emit?("onPpgFrame", ["t": tms - t0, "r": rs / cnt, "g": gs / cnt, "b": bs / cnt])
    }
}
