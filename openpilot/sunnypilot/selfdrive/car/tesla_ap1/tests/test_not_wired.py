"""AP1 is wired through opendbc. This file keeps a smoke import check."""

from opendbc.car.tesla.values import CAR, TeslaSafetyFlags, TeslaFlags


def test_ap1_platform_and_flag_bits():
  assert CAR.TESLA_AP1_MODELS
  assert int(TeslaSafetyFlags.AP1) == 0x100
  assert int(TeslaFlags.AP1) == 0x100
  assert int(TeslaSafetyFlags.LONG_CONTROL) == 1
  assert int(TeslaSafetyFlags.FSD_14) == 2
