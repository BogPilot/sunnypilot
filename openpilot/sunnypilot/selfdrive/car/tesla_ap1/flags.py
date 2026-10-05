"""Tesla AP1 safety-param bits.

sunnypilot opendbc TeslaSafetyFlags (this tree):
  LONG_CONTROL = 1
  FSD_14 = 2
  AP1 = 0x100

BogPilot panda (ap1-driving-milestone-1) used a different numbering on its own
safety_tesla.h:
  POWERTRAIN = 1
  LONGITUDINAL_CONTROL = 2
  RAVEN = 4
  AP1 = 8

SunnyTesla maps AP1 chassis long as AP1 | LONG_CONTROL = 0x101.
Do not put BogPilot's value 10 into sunnypilot's Tesla safety param.
"""

FLAG_LONG_CONTROL = 1
FLAG_FSD_14 = 2
FLAG_AP1 = 0x100

AP1_MODEL_S = "TESLA_AP1_MODELS"


def intended_flags(candidate, fingerprint) -> tuple[int, ...]:
  """Flag tuple the CarInterface requests for AP1."""
  if candidate != AP1_MODEL_S:
    return (0,)
  return (FLAG_AP1 | FLAG_LONG_CONTROL,)
