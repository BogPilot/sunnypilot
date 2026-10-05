from openpilot.sunnypilot.selfdrive.car.tesla_ap1.flags import (
  AP1_MODEL_S,
  FLAG_AP1,
  FLAG_LONGITUDINAL_CONTROL,
  FLAG_POWERTRAIN,
  FLAG_RAVEN,
  RAVEN,
  intended_flags,
)


def test_ap1_flags_are_chassis_long_without_powertrain():
  flags = intended_flags(AP1_MODEL_S, {0: {0x45: 8, 0x2B9: 8, 0x488: 4}})
  assert flags == (FLAG_AP1 | FLAG_LONGITUDINAL_CONTROL,)
  assert flags == (10,)
  assert FLAG_POWERTRAIN not in (flags[0] & FLAG_POWERTRAIN,) or (flags[0] & FLAG_POWERTRAIN) == 0
  assert (flags[0] & FLAG_POWERTRAIN) == 0
  assert (flags[0] & FLAG_AP1) == 8


def test_0x2bf_on_chassis_does_not_add_powertrain():
  flags = intended_flags(AP1_MODEL_S, {0: {0x45: 1, 0x2B9: 1, 0x488: 1, 0x2BF: 1}})
  assert flags == (10,)


def test_0x2bf_on_powertrain_bus_adds_a_second_config():
  flags = intended_flags(AP1_MODEL_S, {6: {0x2BF: 8}})
  assert flags[0] == 10
  assert flags[1] == 10 | FLAG_POWERTRAIN


def test_raven_keeps_its_bit_and_not_ap1():
  flags = intended_flags(RAVEN, {})
  assert flags == (FLAG_RAVEN,)
  assert (flags[0] & FLAG_AP1) == 0
