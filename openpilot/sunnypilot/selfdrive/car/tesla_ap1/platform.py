"""Recognize an AP1 Model S chassis address set. No actuation.

Recognition helper. The live platform is CAR.TESLA_AP1_MODELS in opendbc,
selected via CarPlatformBundle (fixed fingerprint). This classifier documents
the chassis address set used to validate an AP1 car.
"""

from dataclasses import dataclass
from enum import StrEnum


class TeslaPlatform(StrEnum):
  """Recognition only. preap and ap1_x have no production fingerprint."""

  preap = "preap"
  ap1_s = "ap1_s"
  ap1_x = "ap1_x"
  ap2 = "ap2"


# Names from the FrogPilot/BogPilot tree. sunnypilot CAR has no AP1 member.
AP1_MODEL_S = "TESLA_AP1_MODELS"
AP2_MODELS = "TESLA_AP2_MODELS"
RAVEN = "TESLA_MODELS_RAVEN"

# Chassis panda bus. AP1 0x45 / 0x2b9 / 0x488 are on this bus.
# sunnypilot Model 3 checks 0x2b9 and 0x488 on autopilot party bus 2.
CHASSIS_BUS = 0

_PRODUCTION = {
  AP1_MODEL_S: TeslaPlatform.ap1_s,
  AP2_MODELS: TeslaPlatform.ap2,
}

_FIXTURE_ONLY = (TeslaPlatform.preap, TeslaPlatform.ap1_x)

# tesla_can.dbc chassis. 0x2bf is powertrain DAS_control and is not part of
# this signature. 0x2b9f is not a message this port uses.
_AP1_CHASSIS_ADDRS = frozenset((0x45, 0x2B9, 0x488))


@dataclass(frozen=True)
class EarlyPlatformFixture:
  """Test-only identity for preap and ap1_x. Not a CAN fingerprint."""

  platform: TeslaPlatform

  def __post_init__(self) -> None:
    if self.platform not in _FIXTURE_ONLY:
      raise ValueError("EarlyPlatformFixture is only for preap and ap1_x")


def classify_ap1_chassis(addrs) -> TeslaPlatform | None:
  """Return ap1_s when the set contains 0x45, 0x2b9, and 0x488.

  Extra addresses are allowed. 0x2bf is not required and is not sufficient.
  Never returns preap, ap1_x, or ap2.
  """
  observed = _integer_addrs(addrs)
  if observed is None:
    return None
  if _AP1_CHASSIS_ADDRS <= observed:
    return TeslaPlatform.ap1_s
  return None


def classify_tesla_platform(fingerprint) -> TeslaPlatform | None:
  """Return one TeslaPlatform, or None when empty or ambiguous.

  A bus-0 address set classifies as ap1_s only through classify_ap1_chassis.
  The same three IDs on another bus do not. Raven is not ap2.
  """
  if isinstance(fingerprint, EarlyPlatformFixture):
    return fingerprint.platform

  if isinstance(fingerprint, (set, frozenset)):
    observed = _integer_addrs(fingerprint)
    if observed is not None:
      return classify_ap1_chassis(observed)

  if isinstance(fingerprint, dict):
    bus0 = fingerprint.get(CHASSIS_BUS)
    if isinstance(bus0, (dict, set, frozenset)):
      observed = _integer_addrs(bus0)
      if observed is not None:
        return classify_ap1_chassis(observed)
    return None

  candidates = _candidates(fingerprint)
  if not candidates:
    return None

  matched: set[TeslaPlatform] = set()
  for token in candidates:
    if isinstance(token, EarlyPlatformFixture):
      matched.add(token.platform)
      continue
    try:
      resolved = _PRODUCTION.get(token)
    except TypeError:
      resolved = None
    if resolved is not None:
      matched.add(resolved)

  if len(matched) != 1:
    return None
  return next(iter(matched))


def long_control_allowed(platform: TeslaPlatform | None) -> bool:
  """Legacy helper. Longitudinal is decided by CarInterface + alpha long.

  Still False here so callers that only have a recognition result do not
  enable long by themselves.
  """
  return False


def _integer_addrs(container) -> frozenset[int] | None:
  if isinstance(container, dict):
    keys = container.keys()
  elif isinstance(container, (set, frozenset)):
    keys = container
  else:
    return None
  addrs = []
  for key in keys:
    if type(key) is not int:
      return None
    addrs.append(key)
  return frozenset(addrs)


def _candidates(fingerprint) -> list:
  if fingerprint is None:
    return []
  if isinstance(fingerprint, (str, bytes)):
    return [fingerprint]
  if isinstance(fingerprint, dict):
    return []
  if isinstance(fingerprint, (list, tuple, set, frozenset)):
    return list(fingerprint)
  return [fingerprint]
