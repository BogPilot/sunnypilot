from openpilot.sunnypilot.selfdrive.car.tesla_ap1.flags import (
  AP1_MODEL_S,
  FLAG_AP1,
  FLAG_LONG_CONTROL,
  intended_flags,
)


def test_ap1_flags_are_chassis_long():
  flags = intended_flags(AP1_MODEL_S, {0: {0x45: 8, 0x2B9: 8, 0x488: 4}})
  assert flags == (FLAG_AP1 | FLAG_LONG_CONTROL,)
  assert flags == (0x101,)
  assert (flags[0] & FLAG_AP1) == FLAG_AP1
  assert (flags[0] & FLAG_LONG_CONTROL) == FLAG_LONG_CONTROL


def test_non_ap1_is_zero():
  assert intended_flags("TESLA_MODEL_Y", {}) == (0,)
