"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""

from openpilot.cereal import log, custom
from opendbc.car import structs

from opendbc.car.chrysler.values import RAM_DT
from opendbc.car.tesla.values import TeslaFlags
from openpilot.selfdrive.selfdrived.events import Events
from openpilot.sunnypilot.selfdrive.selfdrived.events import EventsSP

EventName = log.OnroadEvent.EventName
EventNameSP = custom.OnroadEventSP.EventName
GearShifter = structs.CarState.GearShifter


class CarSpecificEventsSP:
  def __init__(self, CP: structs.CarParams, CP_SP: structs.CarParamsSP):
    self.CP = CP
    self.CP_SP = CP_SP

    self.low_speed_alert = False
    # CP.flags is per brand, so check the brand too
    self.tesla_ap1 = CP.brand == 'tesla' and bool(CP.flags & TeslaFlags.AP1)

  def update(self, CS: structs.CarState, events: Events, CS_SP=None):
    events_sp = EventsSP()

    if self.CP.brand == 'chrysler':
      if self.CP.carFingerprint in RAM_DT:
        # remove belowSteerSpeed event from CarSpecificEvents as RAM_DT uses a different logic
        if events.has(EventName.belowSteerSpeed):
          events.remove(EventName.belowSteerSpeed)

        # TODO-SP: use if/elif to have the gear shifter condition takes precedence over the speed condition
        # TODO-SP: add 1 m/s hysteresis
        if CS.vEgo >= self.CP.minEnableSpeed:
          self.low_speed_alert = False
        if self.CP.minEnableSpeed >= 14.5 and CS.gearShifter != GearShifter.drive:
          self.low_speed_alert = True
      if self.low_speed_alert:
        events.add(EventName.belowSteerSpeed)

    elif self.CP.brand == 'toyota':
      if self.CP.openpilotLongitudinalControl:
        if CS.cruiseState.standstill and not CS.brakePressed and self.CP_SP.enableGasInterceptor:
          if events.has(EventName.resumeRequired):
            events.remove(EventName.resumeRequired)

    elif self.tesla_ap1:
      self.update_tesla_ap1(events, events_sp, CS_SP)

    return events_sp

  @staticmethod
  def update_tesla_ap1(events: Events, events_sp: EventsSP, CS_SP) -> None:
    """Tesla AP1, ported from BogPilot ap1-driving-milestone-2.

    - Resume hold after a driver override: 0x488 stays type NONE until EPAS reports no hands for 0.5 s.
      steerOverride keeps selfdrived in overriding so the border stays grey until steering resumes.
    - Tinkla HSO: a temporary EPAS steer warning does not soft-disable or block entry. latActive still
      drops on CarState.steerFaultTemporary in controlsd; the alert is a quiet warning.
    - EPAS INHIBITED ~1 s while openpilot wants lateral: the same quiet warning.
    """
    if CS_SP is not None and CS_SP.steerOverrideHold:
      events.add(EventName.steerOverride)
    quiet = False
    for name in (EventName.steerTempUnavailable, EventName.steerTempUnavailableSilent):
      if events.has(name):
        events.remove(name)
        quiet = True
    if quiet or (CS_SP is not None and CS_SP.steerInactiveSilent):
      events_sp.add(EventNameSP.steerInactiveQuiet)
