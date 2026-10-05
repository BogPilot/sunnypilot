# AP1 Model S port note

**Not road-tested on this SunnyTesla branch.** BogPilot `ap1-driving-milestone-1`
(`013f1ffa`) was driven on 2026-10-04. This port wires that behavior into
sunnypilot's opendbc layout. Do not treat green unit tests as permission to drive.

## Base

- SunnyTesla `sunny-tesla` on sunnypilot `master` `a5f44653`
- opendbc submodule: BogPilot fork (see `.gitmodules`), carrying AP1 car + safety
- panda submodule: unchanged pin `74a0adce` (safety is compiled from opendbc)

## Flag bit mapping

| Meaning | BogPilot panda | SunnyTesla / sunnypilot opendbc |
| --- | --- | --- |
| Longitudinal | bit 1 value **2** | bit 0 value **1** (`LONG_CONTROL`) |
| FSD 14 | (n/a in BogPilot) | bit 1 value **2** |
| Raven | bit 2 value **4** | (not used for AP1) |
| AP1 | bit 3 value **8** | bit 8 value **0x100** |

AP1 chassis long safetyParam = `AP1 | LONG_CONTROL` = **0x101**.

Do **not** put BogPilot's value `10` into sunnypilot's Tesla safety param. That
would mean `LONG_CONTROL | FSD_14` here.

## What is wired

1. **Platform** `CAR.TESLA_AP1_MODELS` in opendbc (`tesla_can.dbc` on `Bus.chassis`).
2. **Selection**: set Vehicle → `Tesla AP1 Model S` (CarPlatformBundle / fixed
   fingerprint). There is no FW_VERSIONS row and no legacy CAN fingerprint list.
   Live bus 0 should still show `0x45`, `0x2b9`, `0x488`.
3. **CarState / CarController / packer** for `0x488`, `0x2b9`, `0x45` cancel,
   `0x349` all-zero Hold clear. Hands ≥ 2 pause (type NONE, cruise kept). EPAS
   code 6 and latched code 3 are not temporary faults; ANGLE resumes once hands
   < 2. EAC_FAULT disables. Tinkla angle-rate table + ±20° clip.
4. **Panda safety** (`opendbc/safety/modes/tesla_ap1.h`): AP1 TX allowlist,
   interceptor forward hook (0x488 within 100 ms; 0x2b9 within 50 ms with long
   flag and no stock AEB). Model 3/Y path unchanged when AP1 bit is clear.
5. **controlsd**: AP1 hands-on clears `latActive` (flag `0x100`).
6. **Stalk → personality**: DTR_Dist_Rq changes emit `gapAdjustCruise` button
   events so sunnypilot cycles `LongitudinalPersonality`. Exact detent → follow
   seconds (BogPilot `speedOffset` / FrogPilotFollowing) has **no** sunnypilot
   consumer; helpers remain in `ap1_stalk_follow.py`.

## What is not wired / still blocks a naïve install

- **Panda firmware on device**: you must build and flash panda from this tree
  (opendbc safety is compiled into panda). No new signing keys; debug cert only
  unless you set `RELEASE` + `CERT`.
- **Alpha longitudinal**: must be enabled for chassis `0x2b9` / Hold clear.
  Without it, safetyParam is AP1-only (`0x100`) and long TX is rejected.
- **Instrument cluster frames**: not ported.
- **Stock Autosteer lockout**: not ported (user declined).
- **Radar**: `radarUnavailable = True`.
- **Follow-time seconds from stalk**: documented gap (personality cycle only).
- **Road test on SunnyTesla**: none. Fingerprint + engage on device requires
  CarPlatformBundle selection, alpha long, and flashed AP1 panda safety.

## Tests

- `opendbc/safety/tests/test_tesla.py` (Model 3/Y unchanged)
- `opendbc/safety/tests/test_tesla_ap1.py` (AP1 interceptor, flags, TX)
- `opendbc/car/tesla` + car interface / docs / car_list
- `openpilot/sunnypilot/selfdrive/car/tesla_ap1/tests`

## Engaging on a device (checklist, not a claim of safety)

1. Install this `sunny-tesla` build.
2. Flash panda built against the forked opendbc (AP1 safety).
3. Select **Tesla AP1 Model S** in Vehicle settings.
4. Enable Alpha Longitudinal.
5. Confirm chassis fingerprint traffic includes `0x45` / `0x2b9` / `0x488`.

Until those steps are done and a human road-tests, treat the car as **not**
safe to engage.
