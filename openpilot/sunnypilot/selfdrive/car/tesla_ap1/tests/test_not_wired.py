"""AP1 is wired through opendbc. This file keeps a smoke import check."""

from opendbc.car.tesla.values import CAR, TeslaAp1SafetyFlags, TeslaSafetyFlags, TeslaFlags


def test_ap1_platform_and_flag_bits():
  assert CAR.TESLA_AP1_MODELS
  # AP1 safety param: BogGyver/Tinkla numbering
  assert int(TeslaAp1SafetyFlags.HAS_AP) == 16
  assert int(TeslaAp1SafetyFlags.LONG_CONTROL) == 2
  # Model 3/Y/X safety param is separate and has no AP1 bit
  assert {f.name for f in TeslaSafetyFlags} == {"LONG_CONTROL", "FSD_14"}
  # CarParams.flags (Python only, not a safety param)
  assert int(TeslaFlags.AP1) == 0x100
