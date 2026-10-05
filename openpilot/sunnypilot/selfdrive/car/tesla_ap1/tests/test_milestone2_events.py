"""AP1 selfdrived events from BogPilot ap1-driving-milestone-2. Unit tests only, not road-tested."""

import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.tesla.ap1_hso import ap1_driver_input
from opendbc.car.tesla.values import CAR
from openpilot.cereal import custom, log

# selfdrived events need the built tree (msgq, libparams_c). Skip on a bare checkout.
try:
  from openpilot.selfdrive.selfdrived.events import Events, ET
  from openpilot.sunnypilot.selfdrive.car.car_specific import CarSpecificEventsSP
  from openpilot.sunnypilot.selfdrive.selfdrived.events import EVENTS_SP
except (ImportError, OSError) as e:  # pragma: no cover
  pytest.skip(f"openpilot not built: {e}", allow_module_level=True)

EventName = log.OnroadEvent.EventName
EventNameSP = custom.OnroadEventSP.EventName


def _params(car):
  CI = interfaces[car]
  fp = gen_empty_fingerprint()
  CP = CI.get_params(car, fp, [], False, False, False)
  CP_SP = CI.get_params_sp(CP, car, fp, [], False, False, False)
  return CP, CP_SP


def _run(car, names, cs_sp=None):
  CP, CP_SP = _params(car)
  events = Events()
  for n in names:
    events.add(n)
  events_sp = CarSpecificEventsSP(CP, CP_SP).update(structs.CarState(), events, cs_sp)
  return events.names, events_sp.names


def test_grey_border_level_1():
  assert [ap1_driver_input(lv) for lv in range(4)] == [False, True, True, True]


def test_temp_steer_warning_is_quiet_on_ap1():
  for name in (EventName.steerTempUnavailable, EventName.steerTempUnavailableSilent):
    names, names_sp = _run(CAR.TESLA_AP1_MODELS, [name])
    assert name not in names
    assert EventNameSP.steerInactiveQuiet in names_sp
  names, names_sp = _run(CAR.TESLA_AP1_MODELS, [EventName.steerUnavailable])
  assert EventName.steerUnavailable in names  # permanent faults untouched
  assert names_sp == []


def test_override_hold_and_inhibit_flags():
  cs_sp = structs.CarStateSP()
  cs_sp.steerOverrideHold = True
  names, names_sp = _run(CAR.TESLA_AP1_MODELS, [], cs_sp)
  assert EventName.steerOverride in names and names_sp == []
  cs_sp = structs.CarStateSP()
  cs_sp.steerInactiveSilent = True
  names, names_sp = _run(CAR.TESLA_AP1_MODELS, [], cs_sp)
  assert names == [] and names_sp == [EventNameSP.steerInactiveQuiet]


def test_model3_and_other_teslas_untouched():
  cs_sp = structs.CarStateSP()
  cs_sp.steerOverrideHold = True
  cs_sp.steerInactiveSilent = True
  names, names_sp = _run(CAR.TESLA_MODEL_3, [EventName.steerTempUnavailable], cs_sp)
  assert names == [EventName.steerTempUnavailable]
  assert names_sp == []


def test_quiet_alert_is_warning_only_and_silent():
  alerts = EVENTS_SP[EventNameSP.steerInactiveQuiet]
  assert set(alerts) == {ET.WARNING}
  a = alerts[ET.WARNING]
  assert a.alert_text_1 == "Steering not active"
  assert a.audible_alert == structs.CarControl.HUDControl.AudibleAlert.none
  assert a.visual_alert == structs.CarControl.HUDControl.VisualAlert.none
