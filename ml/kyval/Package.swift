// swift-tools-version:5.9
// KYECG: Telomy's own iOS client for the Kangyuan KY-E-B1 single-lead ECG band (clean-room, from the documented protocol).
import PackageDescription
let package = Package(
  name: "KYECG",
  platforms: [.iOS(.v15), .macOS(.v12)],
  products: [.library(name: "KYECG", targets: ["KYECG"])],
  targets: [
    .target(name: "KYECG"),
    .executableTarget(name: "kyval", dependencies: ["KYECG"]),
    .testTarget(name: "KYECGTests", dependencies: ["KYECG"]),
  ]
)
