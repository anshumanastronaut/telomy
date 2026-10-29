# NOOP/Strand → Telomy: device-layer adopt-list

*Prepared 29 Oct 2026. What Telomy's device layer (`mobile/modules/ky-ecg`) should learn from the NOOP/Strand multi-device BLE app (`telomy-lab/whoop/noop`). Analysis only — see "Applied" at the bottom for what's been done.*

## The core difference
**NOOP** treats devices as a first-class, extensible registry: a `DeviceRegistry` of `PairedDevice` rows, one minimal `LiveHRSource` protocol any brand driver conforms to, a `SourceCoordinator` running one live source, a pure `DeviceBrandCatalog` for recognition, and **every decode/reliability rule as a pure, unit-tested function** (`FTMSDecode`, `Framing`, `StandardHeartRate`, `reconnectStep`, `OuraAuthWatchdog`, `DeviceConfigWriteGate`, `BackfillPolicy`) consulted by thin CoreBluetooth glue.

**Telomy** has two hard-coded singletons (`KYRing.shared`, `KYBand.shared`), each its own `CBCentralManager`, decode logic inline in the frame handlers, and a static JS source-ranking list. Fine for two fixed devices; won't scale to the CGM / Polar H10 / Galaxy Watch / EMG band on the roadmap.

## Where Telomy is already AHEAD (do not regress)
- Correct **no-timeout standing-connect reconnect**, with the `CBConnectPeripheralOptionEnableAutoReconnect` bug already documented (KYRing `connectOpts`) — matches NOOP's hard-won conclusion.
- **Simultaneous ring+patch fusion** with honest agreement flags (`devices.tsx agree()`) — better than NOOP's single-active-source model; keep it.
- **Honest-data discipline**: ring SpO₂ <90 awake rejected as artifact, out-of-range history dropped, BP/glucose never surfaced.
- **Cross-device auto-sleep** (`KYSleepAuto`) fusing patch + ring + phone motion — more sophisticated than NOOP's per-source sleep.

## Ranked adopt-list
| # | Item | Take from NOOP | Effort | Priority | Status |
|---|------|----------------|--------|----------|--------|
| 1 | **Pure, tested reconnect policy** | Extract `reconnectStep`-style pure fn + regression tests from KYRing/KYBand's imperative reconnect. Logic is already right — make it testable so the overnight bug can't regress. | M (2-3d) | **Highest** | TODO |
| 2 | **Size-bounded eviction + off-main raw/debug writes** | `RawOutbox` size cap + `PuffinFrameRecorder` background-actor writer. Cap `ring-raw`, `ring-debug`, `ky-recordings`. | S–M | **Highest** | **Caps applied; off-main TODO** |
| 3 | **Shared device-driver protocol + brand catalog** | `LiveHRSource` protocol + `DeviceBrandCatalog`. Unify KYRing/KYBand behind one interface; move scattered name-token matching into one tested struct. Prereq for CGM/EMG/Polar. | M (3-5d) | High | TODO |
| 4 | **Standard 0x180D HR driver** | Port `StandardHeartRate.parse` + `StandardHRSource` (+ battery 0x2A19). Unlocks Polar H10 / Galaxy Watch / any standard strap — the test rig can't exist without it. | S–M | High (if rig active) | TODO |
| 5 | **`PairedDevice` registry + per-device controls** | id/nickname/capabilities/status + rename + **per-device delete-all-data** (DPDP). Make `METRIC_SOURCES` a user-overridable persisted ranking. | M | Med–High | TODO |
| 6 | **Ring write-gate** | `DeviceConfigWriteGate` pattern — allowlist around `KYRing.send()` so dangerous opcodes (BP-mode `0x032F type 1`) can't be issued by accident. | S | Medium | **Applied** |
| 7 | **Log / device-name redaction** | `logSafeDeviceName` allowlist + hex/MAC masking before anything hits `ring-debug`/`ky-debug`. | S | Medium | **Applied (ring)** |
| 8 | **Power-saving screen** | Expose the ring's hard-coded `monitorEveryMin` / night cadences + a battery-% trigger. | S–M | Medium | TODO |

## What is NOT worth porting
- **`HrBroadcaster` / `GarminBroadcast`** (re-advertising HR out): wrong direction for a clinical app.
- **WHOOP/Oura proprietary stacks** (`OuraLiveSource`, `FrameRouter`, `BLEManager`, `PuffinExperiment`, `Whoop4BondAck`): device-specific RE we don't own hardware for — take the *patterns* (pure policy + read-back verification), not the code.
- **FTMS gym-equipment decode**: no roadmap fit.
- **The exclusive single-live-source `SourceCoordinator`**: NOOP runs one source because WHOOP owns the radio; Telomy wants ring+patch simultaneously — adopt the registry/catalog but **not** the single-active constraint.

## Applied in this pass (KYRing.swift)
- **#6 Write-gate** — `KYRing.send()` now refuses `0x032F` with `[on=1, type=1]` (blood-pressure estimation mode), logged not sent.
- **#7 Redaction** — a `safeName()` helper strips personal names from the debug log (keeps only model tokens).
- **#2 Size caps** — `ring-raw` capped to the newest 40 files and `ring-debug` to 48 hourly logs (pruned on capture start / log rotation), so neither grows unbounded on the device.

Key refs: NOOP — `Strand/BLE/{SourceCoordinator,LiveHRSource,StandardHRSource,BLEManager}.swift`, `Packages/WhoopStore/.../{PairedDevice,DeviceBrandCatalog,RawOutbox}.swift`, `Packages/WhoopProtocol/.../{FTMSDecode,Framing,DeviceConfigWriteGate}.swift`, `Packages/PolarProtocol/.../PmdDecoder.swift`. Telomy — `modules/ky-ecg/ios/{KYRing,KYBand,KyEcgModule}.swift`, `Core/KYProtocol.swift`, `src/lib/devices.ts`, `src/app/{ring,devices,monitor}.tsx`.
