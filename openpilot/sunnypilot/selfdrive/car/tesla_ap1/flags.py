"""BogPilot panda flag bits. Not a sunnypilot safetyParam.

sunnypilot opendbc TeslaSafetyFlags is a different mode:
  LONG_CONTROL = 1
  FSD_14 = 2
BogPilot panda safety_tesla.h is:
  POWERTRAIN = 1
  LONGITUDINAL_CONTROL = 2
  RAVEN = 4
  AP1 = 8
Do not OR intended_flags() into sunnypilot's Tesla safety config. Bit 1
there is longitudinal, not powertrain. This module is not imported by
the car interface.
"""

FLAG_POWERTRAIN = 1
FLAG_LONGITUDINAL_CONTROL = 2
FLAG_RAVEN = 4
FLAG_AP1 = 8

AP1_MODEL_S = "TESLA_AP1_MODELS"
RAVEN = "TESLA_MODELS_RAVEN"
POWERTRAIN_BUS = 6
POWERTRAIN_DAS = 0x2BF


def _has_powertrain_das(fingerprint) -> bool:
  """True only for 0x2bf on the auxiliary powertrain bus. Chassis 0x2bf does not count."""
  if not isinstance(fingerprint, dict):
    return False
  bus = fingerprint.get(POWERTRAIN_BUS)
  if not isinstance(bus, dict):
    return False
  return POWERTRAIN_DAS in bus


def intended_flags(candidate, fingerprint) -> tuple[int, ...]:
  """Flag tuple BogPilot would request. Not applied to panda here.

  AP1 with no 0x2bf is FLAG_AP1 | FLAG_LONGITUDINAL_CONTROL (10). That names
  chassis 0x2b9. POWERTRAIN is not set. 0x2bf is not required.
  """
  if FLAG_AP1 != 8:
    raise RuntimeError("TESLA_FLAG_AP1 must be 8")

  flags = FLAG_RAVEN if candidate == RAVEN else 0
  if candidate == AP1_MODEL_S:
    flags |= FLAG_AP1
    flags |= FLAG_LONGITUDINAL_CONTROL

  if _has_powertrain_das(fingerprint):
    flags |= FLAG_LONGITUDINAL_CONTROL
    return (flags, flags | FLAG_POWERTRAIN)
  return (flags,)
