# AP1 Model S port note

**Not road-tested on this SunnyTesla branch.** BogPilot `ap1-driving-milestone-1`
(`013f1ffa`) was driven on 2026-10-04 and `ap1-driving-milestone-2` (`92e84996`) on
2026-10-05, both on BogPilot (FrogPilot base). This port carries that behavior into
sunnypilot's opendbc layout. Nothing here has been driven on sunnypilot, and nothing has been
tested on MCU2. Green unit tests do not mean it is safe to drive.

AP1 is treated as a **fresh car port**. Nothing in it is shared with, or derived from,
the Model 3/Y/X port (camera-based, different buses). The reference for AP1 is
**BogGyver/Tinkla** (one project, two names):

- `BogGyver/openpilot` `tesla_unity_dev` (`501c7de`): `selfdrive/car/tesla/interface.py`,
  `values.py` (CAN fingerprints, `CarControllerParams`), `carstate.py` (`TinklaHandsOnLevel`)
- `BogGyver/panda` `f7751e4`: `board/safety/safety_tesla.h` (`FLAG_TESLA_*`, angle-rate
  table, `has_ap_hardware` path)
- `BogGyver/opendbc` `9c0b6fe`: `tesla_can.dbc`

BogPilot's AP1 port (FrogPilot base) is the bridge that was actually driven, and is the
source for the FW query and the interceptor forward hook.

## Base

- SunnyTesla `sunny-tesla` on sunnypilot `master` `a5f44653`
- opendbc submodule: BogPilot fork (see `.gitmodules`), carrying the AP1 car + safety
- panda submodule: unchanged pin `74a0adce` (safety is compiled from opendbc)

## Detection (automatic)

opendbc runs three Tesla FW requests on bus 0, each with its own ECU whitelist:

| Request | ECUs | Addresses | Source |
| --- | --- | --- | --- |
| TesterPresent + `22 F1A0` | Model 3/Y/X EPS only | 0x730 -> 0x738 | upstream (now whitelisted to EPS) |
| TesterPresent + `22 F181`, rx_offset 0x10 | AP1 brake booster, radar | 0x64d -> 0x65d, 0x671 -> 0x681 | BogPilot `values.py` |
| TesterPresent + `22 F188`, rx_offset 0x08 | AP1 EPAS | 0x730 -> 0x738 | user's AP1 rlogs |

`FW_VERSIONS[TESLA_AP1_MODELS]` holds the user's versions: brake booster `1037123-00-A`,
Bosch radar `\x01\x00W...\t\xff\xfe`, EPAS `1016704-00-HAA` + 10 NULs. Matching is exact:
radar and EPS are essential ECUs and both must match. Neither is used for fuzzy matching, so
the shared brake booster (AP2 and Raven use the same part, see BogPilot `fingerprints.py`)
can never select AP1 on its own. Model 3/Y/X EPS strings cannot match AP1, and the AP1 EPAS
string cannot match Model 3/Y/X (tests in `opendbc/car/tesla/tests/test_tesla_ap1.py`).

**Other AP1 cars need their radar and EPAS versions added** before they auto-detect.
Until then, pick **Tesla AP1 Model S** in Vehicle settings (CarPlatformBundle); manual
selection works the same as before.

No CAN fingerprint fallback was added. BogGyver/Tinkla's AP1 CAN fingerprint does not
cover the user's car (bus 0 `0x21a` is missing and `0x294` has a different length), and the
user's own 168-address set has 18 intermittent IDs from a handful of drives. opendbc
eliminates a candidate on one unknown address within ~0.1 s, so the list would either miss
the car or need to be loose enough to risk selecting AP1 safety on another car.

## Longitudinal

AP1 always uses openpilot longitudinal (`openpilotLongitudinalControl = True`). It is not
gated on `AlphaLongitudinalEnabled`, and the Alpha toggle is hidden for AP1
(`alphaLongitudinalAvailable = False`). This follows BogPilot. BogGyver/Tinkla itself
defaults AP1 to stock ACC and opts in with `TinklaEnableOPLong`; there is no BogGyver
opt-out, so none is added here.

## Panda safety param

AP1 uses BogGyver/Tinkla's numbering (`TeslaAp1SafetyFlags`, `tesla_ap1.h`), not the
Model 3/Y layout:

| Bit | BogGyver/Tinkla name | AP1 here |
| --- | --- | --- |
| 2 | `FLAG_TESLA_LONG_CONTROL` | chassis 0x2b9 + 0x349 Hold clear |
| 16 | `FLAG_TESLA_HAS_AP` | selects `tesla_ap1.h` inside the Tesla mode |
| 1, 4, 8, 32, 64, 128 | POWERTRAIN, RADAR_BEHIND_NOSECONE, IC, RADAR_EMU, HAO, IBOOSTER | not implemented, ignored |

AP1 sends `HAS_AP | LONG_CONTROL` = **18**. Bit 16 is clear of every Model 3/Y/X bit
(`LONG_CONTROL` 1, `FSD_14` 2), so a Model 3/Y param can never select AP1 safety (tested).
The old SunnyTesla value `0x101` no longer selects AP1.

**ALLOW_DEBUG gate kept.** BogGyver/Tinkla's panda honors the long flag in every build. That
panda predates comma's ALLOW_DEBUG gate on Tesla longitudinal, and nothing in it argues the
gate is unneeded for AP1, so it stays. You need a **DEBUG panda build** (the default when
building from source without `RELEASE=1`; `panda/SConscript` adds `-DALLOW_DEBUG`). On a
release-signed panda, openpilot still plans longitudinal but the panda drops 0x2b9 / 0x349
and keeps forwarding stock 0x2b9, so the car stays on stock ACC.

Checks kept from before: Tinkla/BogGyver angle-rate table, ±20° clip in the controller,
controls-allowed gating, interceptor forward hook (0x488 within 100 ms, 0x2b9 within 50 ms
with long and no stock AEB), 0x45 cancel-only, 0x349 all-zero only, no AEB TX, accel
limits 2.0 / -3.52 m/s² (BogGyver allowed -4.51).

Added for milestone 2 (cluster): bus 0 TX of `0x399` / `0x389` / `0x239`
(`autopilotStatus` 3-5 in `0x399` needs controls allowed). The stock bus-2 copy is dropped
only within 750 ms (`0x399`, `0x389`) / 150 ms (`0x239`) of openpilot's last send of that
address, so stock frames come back as soon as openpilot stops. MISRA (cppcheck) is clean.

### Panda firmware on the device

The safety code is in `opendbc/safety` and is compiled into the panda firmware by
`panda/SConscript` when the device builds this branch from source. Without `RELEASE=1` that
is a DEBUG build (`-DALLOW_DEBUG`, debug cert). On boot `pandad` compares the panda's
signature with the built `panda_h7.bin.signed` and flashes it if they differ, so installing
this branch and rebooting reflashes the panda automatically. **The milestone-2 build changes
the safety code (cluster TX / drop), so the first boot reflashes the panda.** No manual flash.

## What is wired

1. **Platform** `CAR.TESLA_AP1_MODELS` (`tesla_can.dbc` on `Bus.chassis`).
2. **CarState / CarController / packer** for `0x488`, `0x2b9`, `0x45` cancel, `0x349`
   all-zero Hold clear (`ACC_HOLD` is never echoed). EAC_FAULT disables.
3. **Stalk:** a single pull engages openpilot (no stock Autosteer split, no lockout).
4. `steerAtStandstill` is off for AP1 (BogGyver/Tinkla default).

## Ported from BogPilot `ap1-driving-milestone-2` (`92e84996`)

| BogPilot behavior | Here |
| --- | --- |
| EPAS steer-fault gating: latched hands-on code 3 / high-angle code 6 are not steer faults; other EPAS warnings and EAC_FAULT as Tinkla | `ap1_carstate.py`, `ap1_steer_fault.py` (unchanged from m1) |
| ANGLE at the measured wheel while EPAS is not `EAC_ACTIVE`, and a 300 ms measured-angle soft-start on engage | `ap1_actuator_plan.py` `ap1_hold_measured_angle`, `ap1_carcontroller.py` |
| Quiet "Steering not active" after ~1 s `EAC_INHIBITED` while openpilot wants lateral (not on level-3 self-shutoff or during the resume hold) | `ap1_hso.Ap1EpasInhibitAlert` → `CarStateSP.steerInactiveSilent` → `EventNameSP.steerInactiveQuiet` |
| Tinkla HSO: a temporary EPAS warning is warning-only (no soft disable, no no-entry) | `car_specific.py` swaps `steerTempUnavailable(Silent)` for `steerInactiveQuiet` on AP1. `latActive` still drops on `steerFaultTemporary` |
| Forward stock `0x488` / `0x2b9` until openpilot substitutes them | panda forward hook (unchanged from m1) |
| `steeringPressed` at EPAS hands level ≥ 1 (grey override border) | `ap1_carstate.py` (`ap1_driver_input`) |
| openpilot yields (0x488 type NONE) only at level ≥ 2; cruise stays up | `ap1_actuator_plan.py` |
| Resume hold: 0.5 s (`AP1_RESUME_HOLD_S`) of level 0, then the 300 ms soft-start; any touch restarts; disengage clears | `ap1_hso.Ap1DriverYield`; `CarStateSP.steerOverrideHold` adds `steerOverride` so the border stays grey during the hold |
| Removed the controlsd "hands-on clears latActive" pause | `controlsd.py` (a level-1 touch must not drop lateral) |
| ACC Hold clear | unchanged from m1 |
| Stalk `DTR_Dist_Rq` → follow distance | detent 1-3 → aggressive, 5 → standard, 7 → relaxed, 4 / 6 hold; `CarStateSP.personalityRequest`, applied by selfdrived on a change of detent (writes `LongitudinalPersonality`). The old `gapAdjustCruise` cycling is gone |
| Instrument cluster: `0x399` / `0x389` / `0x239` rebuilt from stock (counter +1, `0x239` has no checksum), lane-line usage kept | `ap1_cluster.py`, `ap1_carcontroller.py` |
| `0x239` path from modelV2, C0 = C1 = 0, through-origin C2 fit over 50 m × `IC_LANE_SCALE` 0.5, view range from the model capped at 100 m; fallback actuator curvature + 50 m | controlsd_ext fills `CarControlSP.modelPathX/Y` while engaged |
| `enableICIntegration` default on for AP1 | param `TeslaAp1IcIntegration` (default on) → `TeslaFlagsSP.AP1_IC_INTEGRATION`; toggle in Vehicle → Tesla, AP1 only, offroad only, applies on the next drive |

The stock cluster frames are read with no alive / counter / checksum checks, so they can
never make `canValid` false.

**MADS:** AP1 MADS is the limited mode (no vehicle bus). The car port treats lateral as
engaged when `CarControl.enabled` or MADS is active, so a MADS lateral-only engage gets the
same yield, resume hold and soft-start. Longitudinal and the cluster "engaged" state still
follow `CarControl.enabled`. sunnypilot's own blinker lateral pause still clears `latActive`
on top of this when the user turns it on.

## Not ported, and why

- **Planner false FCW at engage (`crash_cnt` clear):** not needed. On BogPilot it came from
  FrogPilot planning with zero accel limits while disengaged. sunnypilot's planner always
  uses the real ACCEL_MIN / ACCEL_MAX, and selfdrived only raises the planner FCW while
  enabled, so that stale-collision path does not exist here. FCW, model FCW and stock AEB are
  untouched.
- **Startup text ("Your m∞v" / "Hands present, mind at ease"):** sunnypilot has no
  user-settable startup text, only fixed `startup` alerts.
- **0x309 / 0x3a9 / 0x3e9, Tinkla ALCA, radar:** not part of milestone 2 (same as BogPilot).
- **Tinkla's HSO extras** (turn-stalk and 15° handoff restarts of the numb timer): BogPilot
  m2 does not use them either.
- **sunnylink remote setting for `TeslaAp1IcIntegration`:** the sunnylink schema has no AP1
  capability to hide it on other Teslas, so the toggle is on-device only.

## Still missing

- Exact stalk follow seconds (the stalk picks one of the 3 personalities).
- Radar (`radarUnavailable = True`).
- More AP1 FW versions (radar/EPAS) from other owners.
- Road test on SunnyTesla.

## Tests

- `opendbc/safety/tests/test_tesla.py`, `test_tesla_ap1.py` (incl. release-build long rejection,
  cluster TX / drop windows); MISRA `opendbc/safety/tests/misra/test_misra.sh`
- `opendbc/car/tesla/tests/test_tesla_ap1.py` (FW autodetect, default long)
- `opendbc/car/tesla/tests/test_tesla_ap1_cluster.py`, `test_tesla_ap1_milestone2.py`
  (BogPilot m2 tests, plus real-parser/packer wiring)
- `opendbc/car/tests`
- `openpilot/sunnypilot/selfdrive/car/tesla_ap1/tests` (`test_milestone2_events.py` needs a
  built tree for msgq / params)

## Engaging on a device (checklist, not a claim of safety)

1. Install this `sunny-tesla` build.
2. Reboot once so pandad flashes the DEBUG panda built from this tree (AP1 safety, cluster, long flag honored).
3. Check the car auto-detects as Tesla AP1 Model S (or select it in Vehicle settings).
4. Confirm bus 0 shows `0x45` / `0x2b9` / `0x488`.

Until a human road-tests it, treat the car as **not** safe to engage.
