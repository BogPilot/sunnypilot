# AP1 Model S port note

**Not road-tested on this SunnyTesla branch.** BogPilot `ap1-driving-milestone-1`
(`013f1ffa`) was driven on 2026-10-04. This port carries that behavior into
sunnypilot's opendbc layout. Green unit tests do not mean it is safe to drive.

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

## What is wired

1. **Platform** `CAR.TESLA_AP1_MODELS` (`tesla_can.dbc` on `Bus.chassis`).
2. **CarState / CarController / packer** for `0x488`, `0x2b9`, `0x45` cancel, `0x349`
   all-zero Hold clear. Hands ≥ 2 pause (type NONE, cruise kept). EPAS code 6 and latched
   code 3 are not temporary faults; ANGLE resumes once hands < 2. EAC_FAULT disables.
3. **controlsd**: AP1 hands-on clears `latActive` (Tesla brand + `TeslaFlags.AP1`).
4. **Stalk → personality**: DTR_Dist_Rq changes emit `gapAdjustCruise`. A single stalk
   pull engages openpilot (no stock Autosteer split, no lockout).
5. `steerAtStandstill` is off for AP1 (BogGyver/Tinkla default).

## Still missing

- Exact stalk follow seconds (only the 3 personalities cycle; helpers in `ap1_stalk_follow.py`).
- Instrument cluster frames.
- Radar (`radarUnavailable = True`).
- More AP1 FW versions (radar/EPAS) from other owners.
- MISRA/cppcheck not run on the box (cppcheck not installed).
- Road test on SunnyTesla.

## Tests

- `opendbc/safety/tests/test_tesla.py`, `test_tesla_ap1.py` (incl. release-build long rejection)
- `opendbc/car/tesla/tests/test_tesla_ap1.py` (FW autodetect, default long)
- `opendbc/car/tests`
- `openpilot/sunnypilot/selfdrive/car/tesla_ap1/tests`

## Engaging on a device (checklist, not a claim of safety)

1. Install this `sunny-tesla` build.
2. Flash a DEBUG panda built from this tree (AP1 safety, long flag honored).
3. Check the car auto-detects as Tesla AP1 Model S (or select it in Vehicle settings).
4. Confirm bus 0 shows `0x45` / `0x2b9` / `0x488`.

Until a human road-tests it, treat the car as **not** safe to engage.
