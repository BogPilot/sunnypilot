from openpilot.sunnypilot.selfdrive.car.tesla_ap1.platform import (
  AP1_MODEL_S,
  AP2_MODELS,
  CHASSIS_BUS,
  RAVEN,
  EarlyPlatformFixture,
  TeslaPlatform,
  classify_ap1_chassis,
  classify_tesla_platform,
  long_control_allowed,
)

_AP1_CHASSIS = frozenset((0x45, 0x2B9, 0x488))


def test_ap1_name_and_long_stays_off():
  platform = classify_tesla_platform(AP1_MODEL_S)
  assert platform == TeslaPlatform.ap1_s
  assert long_control_allowed(platform) is False
  assert long_control_allowed(None) is False


def test_empty_and_garbage_are_unmatched():
  for fingerprint in (None, "", [], set(), {}, {0: {0x2BF: 8}}, b"\x00", 0, "not-a-tesla", "HONDA_CIVIC"):
    assert classify_tesla_platform(fingerprint) is None
    assert long_control_allowed(classify_tesla_platform(fingerprint)) is False


def test_ambiguous_ap1_and_ap2_is_refused():
  both = [AP1_MODEL_S, AP2_MODELS]
  assert classify_tesla_platform(both) is None
  assert classify_tesla_platform(set(both)) is None


def test_raven_is_not_ap2():
  assert classify_tesla_platform(RAVEN) is None
  assert classify_tesla_platform([RAVEN, AP2_MODELS]) == TeslaPlatform.ap2
  assert classify_tesla_platform([RAVEN, AP1_MODEL_S]) == TeslaPlatform.ap1_s


def test_ap2_alone_maps_without_long():
  platform = classify_tesla_platform(AP2_MODELS)
  assert platform == TeslaPlatform.ap2
  assert long_control_allowed(platform) is False


def test_preap_and_ap1_x_only_from_fixture():
  assert classify_tesla_platform(EarlyPlatformFixture(TeslaPlatform.preap)) == TeslaPlatform.preap
  assert classify_tesla_platform(EarlyPlatformFixture(TeslaPlatform.ap1_x)) == TeslaPlatform.ap1_x
  try:
    EarlyPlatformFixture(TeslaPlatform.ap1_s)
    raised = False
  except ValueError:
    raised = True
  assert raised
  for platform in TeslaPlatform:
    assert long_control_allowed(platform) is False


def test_chassis_addrs_do_not_require_0x2bf_or_0x2b9f():
  assert CHASSIS_BUS == 0
  assert 0x2BF not in _AP1_CHASSIS
  assert 0x2B9F not in _AP1_CHASSIS
  assert classify_ap1_chassis(_AP1_CHASSIS) == TeslaPlatform.ap1_s
  assert classify_ap1_chassis({0x45: 8, 0x2B9: 8, 0x488: 4}) == TeslaPlatform.ap1_s
  bus0 = {0: {addr: 1 for addr in _AP1_CHASSIS}}
  assert classify_tesla_platform(bus0) == TeslaPlatform.ap1_s
  with_extra = {0: {0x45: 8, 0x2B9: 8, 0x488: 4, 0x100: 8, 0x2BF: 1, 0x2B9F: 1}, 6: {0x2BF: 1}}
  assert classify_tesla_platform(with_extra) == TeslaPlatform.ap1_s
  assert classify_ap1_chassis({0x2BF}) is None
  assert classify_tesla_platform({0: {0x2BF: 8}}) is None
  assert classify_tesla_platform({6: {0x2BF: 8}}) is None
  assert classify_ap1_chassis({0x2B9F}) is None
  for missing in (
    frozenset((0x45, 0x2B9)),
    frozenset((0x45, 0x488)),
    frozenset((0x2B9, 0x488)),
  ):
    assert classify_ap1_chassis(missing) is None
  elsewhere = {1: {0x45: 1, 0x2B9: 1, 0x488: 1}, 2: {0x45: 1, 0x2B9: 1, 0x488: 1}}
  assert classify_tesla_platform(elsewhere) is None
