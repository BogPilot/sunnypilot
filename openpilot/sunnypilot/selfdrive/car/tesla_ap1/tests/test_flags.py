from opendbc.car import gen_empty_fingerprint
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR, TeslaAp1SafetyFlags, TeslaSafetyFlags

from openpilot.sunnypilot.selfdrive.car.tesla_ap1.flags import (
  AP1_MODEL_S,
  FLAG_HAS_AP,
  FLAG_LONG_CONTROL,
  intended_flags,
)


def test_ap1_flags_are_boggyver_layout():
  flags = intended_flags(AP1_MODEL_S, {0: {0x45: 8, 0x2B9: 8, 0x488: 4}})
  assert flags == (FLAG_HAS_AP | FLAG_LONG_CONTROL,)
  assert flags == (18,)
  assert FLAG_HAS_AP == int(TeslaAp1SafetyFlags.HAS_AP)
  assert FLAG_LONG_CONTROL == int(TeslaAp1SafetyFlags.LONG_CONTROL)


def test_ap1_selector_clear_of_model3y_bits():
  for flag in TeslaSafetyFlags:
    assert not (FLAG_HAS_AP & int(flag))


def test_non_ap1_is_zero():
  assert intended_flags("TESLA_MODEL_Y", {}) == (0,)


def test_interface_matches_intended_flags_without_alpha_long():
  for alpha_long in (False, True):
    CP = CarInterface.get_params(CAR.TESLA_AP1_MODELS, gen_empty_fingerprint(), [], alpha_long, False, False)
    assert CP.openpilotLongitudinalControl
    assert (CP.safetyConfigs[0].safetyParam,) == intended_flags(AP1_MODEL_S, {})
