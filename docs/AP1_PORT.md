# AP1 Model S port note

This is not a driveable Tesla port. Nothing here was road-tested. Do not install this branch to drive.

Base: sunnypilot `master` `a5f44653d7f43ad57fef2f546f3916ec4cbf3c56`
(`mici: add a refresh models button to the models panel (#2018)`).

opendbc submodule pin (not modified): `f95f996f5917dcbbf2e32fe51b606a24cf836af6`
panda submodule pin (not modified): `74a0adced421e8b7acd728d0f9988ce225423f13`

Source of the AP1 behavior: BogPilot/openpilot `bogpilot-tesla` through `013f1ffa`
(hands-on unlatch is `4595909a`). The startup-alert text change in `013f1ffa` was
not ported. It is FrogPilot UI.

## Why a blind copy is wrong

sunnypilot's Tesla support is comma's Model 3 / Model Y / Model X HW3-HW4 port.
It lives in the opendbc submodule, not in `selfdrive/car/tesla/` the way FrogPilot
0.9.7 does.

- Fingerprint is EPS firmware at `0x730` (`TeM3_` / `TeMYG4_` strings), merged with
  `opendbc/sunnypilot/car/tesla/fingerprints_ext.py`. There is no AP1 CAN fingerprint.
- Buses: party `0`, vehicle `1`, autopilot party `2`. DAS `0x2b9` and `0x488` are
  checked on bus 2 in `opendbc/safety/modes/tesla.h`.
- AP1 Model S (BogPilot / Tinkla) is chassis bus 0: `0x45` stalk, `0x2b9` chassis
  DAS_control, `0x488` chassis steering. `0x2bf` (powertrain DAS_control) and
  `0x2b9f` are not required.
- Angle limits differ. sunnypilot `CarControllerParams.ANGLE_LIMITS` is
  `MAX_ANGLE_RATE = 5` deg per 20 ms frame. Tinkla's AP1 panda table is speeds
  `{2, 7, 17}` m/s, up `{8, 4, 2.5}`, down `{9, 5, 4.5}`.
- Safety flag bits differ and must not be mixed.
  sunnypilot `TeslaSafetyFlags`: `LONG_CONTROL = 1`, `FSD_14 = 2`.
  BogPilot panda: `POWERTRAIN = 1`, `LONGITUDINAL_CONTROL = 2`, `RAVEN = 4`,
  `AP1 = 8`. AP1 chassis long is `8|2 = 10`, with powertrain left unset.
  Putting `10` into the sunnypilot safety param would mean `LONG_CONTROL|FSD_14`,
  which is a Model 3/Y mode, not AP1.
- DBCs differ (`tesla_model3_party` / `tesla_model3_vehicle` vs `tesla_can` /
  `tesla_powertrain`). Copying BogPilot `teslacan.py` into this tree would pack
  the wrong signals.

Registering `TESLA_AP1_MODELS` on the existing `CarInterface` would select
`SafetyModel.tesla` (the party-bus mode) and could open Model 3 longitudinal.
That was not done.

## What landed

Unwired Python under `openpilot/sunnypilot/selfdrive/car/tesla_ap1/`. It is not
imported by card, CarInterface, or safety.

- Chassis fingerprint: bus 0 must include `0x45`, `0x2b9`, and `0x488`. Extra
  addresses are allowed. `0x2bf` and `0x2b9f` are not required and are not
  sufficient. The same three IDs on bus 1 or 2 do not match.
- Recognition does not allow longitudinal (`long_control_allowed` is false).
- `flags.py` records the BogPilot bit values only. It is not passed to panda.
- Hands-on pause at level >= 2: lateral plan goes to control type NONE, cruise
  is not cancelled.
- EPAS code 6 (`EAC_ERROR_HIGH_ANGLE_REQ`) and latched code 3
  (`EAC_ERROR_HANDS_ON`) are not temporary faults on AP1, so once hands are
  below 2 and it is not `EAC_FAULT` the decision is ANGLE. Other non-idle names
  still warn. Model 3/Y (`chassis_das_only` false) does not take that fallback.
- Stalk `DTR_Dist_Rq` detent map (0, 33, 66, 100, 133, 166, 200, SNA 255) to
  follow seconds. Those numbers are the FrogPilot default follow times, not a
  new CAN scale.
- Hold-clear *decision* (`ap1_should_send_hold_clear`) and rewriting camera
  ACC_HOLD (3) to ACC_ON (4) for AP1 chassis long. The `0x349` frame is not packed.
- Angle step in this helper uses the Tinkla lookup above, then +/- 20 deg around
  the measured wheel. BogPilot's Python `CarControllerParams` still uses the
  shared non-AP1 table (`0/5/15` m/s). This helper does not.

## What did not transfer

- No change to `opendbc_repo` or `panda`. No `TESLA_FLAG_AP1` in
  `opendbc/safety/modes/tesla.h`. No TX allow for chassis `0x488` / `0x2b9` /
  `0x349` on bus 0. No forward hook that lets stock Mobileye `0x488` and `0x2b9`
  pass until openpilot substitutes them.
- No `teslacan.py`, no DBC, no CAN parser, no carstate, no CarController, no
  radar interface, no interface `_get_params`.
- No panda firmware, no model weights.
- No controlsd hands-pause wiring, no FrogPilot follow publisher, no UI,
  including the BogPilot startup alert strings.
- `preap` and `ap1_x` still have no fingerprint.
- An AP1 car will not fingerprint as this platform on a device. The classifier
  is library code until a later change adds a safety mode that does not alter
  Model 3/Y.

Do not treat a green unit test as permission to drive.
