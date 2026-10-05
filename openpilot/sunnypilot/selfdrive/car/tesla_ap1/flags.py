"""Tesla AP1 Model S safety-param bits.

AP1 uses BogGyver/Tinkla's own safety param numbering (BogGyver/panda board/safety/safety_tesla.h,
FLAG_TESLA_*), mirrored in opendbc TeslaAp1SafetyFlags and opendbc/safety/modes/tesla_ap1.h:
  LONG_CONTROL = 2   chassis 0x2b9 longitudinal (panda honors it only in ALLOW_DEBUG builds)
  HAS_AP       = 16  AP hardware on the chassis bus; selects the AP1 safety inside the Tesla mode

It is not the Model 3/Y/X layout (opendbc TeslaSafetyFlags LONG_CONTROL = 1, FSD_14 = 2). HAS_AP is
clear of every Model 3/Y/X bit, so a Model 3/Y param can never select the AP1 safety.

AP1 always requests openpilot longitudinal: HAS_AP | LONG_CONTROL = 18. It is not gated on
AlphaLongitudinalEnabled.
"""

FLAG_LONG_CONTROL = 2
FLAG_HAS_AP = 16

AP1_MODEL_S = "TESLA_AP1_MODELS"


def intended_flags(candidate, fingerprint) -> tuple[int, ...]:
  """Flag tuple the CarInterface requests for AP1."""
  if candidate != AP1_MODEL_S:
    return (0,)
  return (FLAG_HAS_AP | FLAG_LONG_CONTROL,)
