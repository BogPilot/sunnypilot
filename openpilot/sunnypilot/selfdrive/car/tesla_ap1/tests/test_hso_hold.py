"""Decision tests. Not a drive test. Not wired to CAN or panda."""

from collections import deque

from openpilot.sunnypilot.selfdrive.car.tesla_ap1.actuator_plan import (
  ACC_HOLD,
  ACC_ON,
  DAS_CONTROL_CHASSIS,
  DAS_CONTROL_POWERTRAIN,
  STEERING_CONTROL_ANGLE,
  STEERING_CONTROL_NONE,
  ap1_long_acc_state,
  ap1_should_send_hold_clear,
  build_actuator_plan,
  longitudinal_command_allowed,
)
from openpilot.sunnypilot.selfdrive.car.tesla_ap1.hso import (
  AP1_HANDS_ON_LEVEL,
  ap1_hso_event_names,
  ap1_lat_active,
  ap1_steering_pressed,
)
from openpilot.sunnypilot.selfdrive.car.tesla_ap1.stalk_follow import (
  SNA,
  ap1_stalk_commands,
  apply_stalk_t_follow,
  follow_seconds,
  map_stalk_follow,
)
from openpilot.sunnypilot.selfdrive.car.tesla_ap1.steer_fault import steer_fault_temporary


def _plan(**kwargs):
  args = dict(
    frame=0,
    lat_active=False,
    hands_on_fault=False,
    openpilot_longitudinal_control=True,
    enabled=True,
    long_active=True,
    measured_angle_deg=8.0,
    requested_angle_deg=30.0,
    last_angle_deg=8.0,
    v_ego=15.0,
    accel=0.2,
    acc_state=ACC_ON,
    das_counters=deque([3]),
    pcm_cancel=False,
    chassis_das_only=True,
  )
  args.update(kwargs)
  return build_actuator_plan(**args)


def test_hands_threshold_is_tinkla_level_2():
  assert AP1_HANDS_ON_LEVEL == 2
  assert ap1_steering_pressed(0) is False
  assert ap1_steering_pressed(1) is False
  assert ap1_steering_pressed(2) is True
  assert ap1_steering_pressed(3) is True
  assert ap1_lat_active(True, 2) is False
  assert ap1_lat_active(True, 1) is True
  assert ap1_lat_active(False, 0) is False


def test_hands_pause_sends_measured_none_and_keeps_long():
  plan = _plan(lat_active=False, hands_on_level=2)
  assert plan.cancel is False
  assert len(plan.longitudinal) == 1
  assert plan.longitudinal_addrs == (DAS_CONTROL_CHASSIS,)
  assert DAS_CONTROL_POWERTRAIN not in plan.longitudinal_addrs
  assert plan.steer is not None
  assert plan.steer.control_type == STEERING_CONTROL_NONE
  assert plan.steer.angle_deg == 8.0


def test_hands_drop_resumes_angle_with_tinkla_rate():
  # v_ego 0 uses the first Tinkla up breakpoint (2 m/s, 8 deg/step), not 10.
  plan = _plan(lat_active=True, requested_angle_deg=10.0, measured_angle_deg=0.0,
               last_angle_deg=0.0, v_ego=0.0, accel=0.0, hands_on_level=1)
  assert plan.cancel is False
  assert plan.steer.control_type == STEERING_CONTROL_ANGLE
  assert plan.steer.angle_deg == 8.0


def test_code_6_and_latched_code_3_send_angle_once_hands_below_2():
  assert steer_fault_temporary("EAC_ERROR_HIGH_ANGLE_REQ", True) is False
  assert steer_fault_temporary("EAC_ERROR_HANDS_ON", True) is False
  assert steer_fault_temporary("EAC_ERROR_HIGH_ANGLE_REQ", False) is True
  assert steer_fault_temporary("EAC_ERROR_HANDS_ON", False) is False
  assert steer_fault_temporary("EAC_ERROR_IDLE", True) is False
  assert steer_fault_temporary("EAC_ERROR_HIGH_ANGLE_RATE_REQ", True) is True

  code6 = _plan(lat_active=False, hands_on_level=1, measured_angle_deg=4.0,
                last_angle_deg=4.0, requested_angle_deg=25.0,
                epas_error="EAC_ERROR_HIGH_ANGLE_REQ")
  assert code6.cancel is False
  assert code6.steer.control_type == STEERING_CONTROL_ANGLE
  assert code6.steer.angle_deg == 4.0
  assert len(code6.longitudinal) == 1

  code3 = _plan(lat_active=False, hands_on_level=0, measured_angle_deg=4.0,
                last_angle_deg=4.0, requested_angle_deg=25.0,
                epas_error="EAC_ERROR_HANDS_ON")
  assert code3.steer.control_type == STEERING_CONTROL_ANGLE
  assert code3.cancel is False

  paused = _plan(lat_active=True, hands_on_level=2, measured_angle_deg=4.0,
                 last_angle_deg=4.0, epas_error="EAC_ERROR_HANDS_ON")
  assert paused.steer.control_type == STEERING_CONTROL_NONE
  assert paused.cancel is False
  assert len(paused.longitudinal) == 1


def test_other_codes_and_eac_fault_and_disengaged():
  other = _plan(lat_active=False, measured_angle_deg=4.0,
                epas_error="EAC_ERROR_HIGH_ANGLE_RATE_REQ")
  assert other.steer.control_type == STEERING_CONTROL_NONE
  fault = _plan(lat_active=True, eac_fault=True, measured_angle_deg=4.0,
                last_angle_deg=4.0, epas_error="EAC_ERROR_HIGH_ANGLE_REQ")
  assert fault.steer.control_type == STEERING_CONTROL_NONE
  off = _plan(enabled=False, long_active=False, lat_active=False,
              epas_error="EAC_ERROR_HIGH_ANGLE_REQ")
  assert off.steer is None
  assert off.longitudinal == ()
  model3 = _plan(chassis_das_only=False, lat_active=False,
                 epas_error="EAC_ERROR_HIGH_ANGLE_REQ")
  assert model3.steer is None


def test_clip_is_measured_plus_20_not_a_model3_rate():
  plan = _plan(lat_active=True, requested_angle_deg=40.0, measured_angle_deg=0.0,
               last_angle_deg=20.0, v_ego=0.0, epas_error="EAC_ERROR_HIGH_ANGLE_REQ")
  assert plan.steer.control_type == STEERING_CONTROL_ANGLE
  assert plan.steer.angle_deg == 20.0


def test_hold_clear_and_acc_on():
  assert ap1_long_acc_state(ACC_HOLD, True) == ACC_ON
  assert ap1_long_acc_state(ACC_HOLD, False) == ACC_HOLD
  counters = deque([7])
  plan = _plan(acc_state=ACC_HOLD, das_counters=counters, lat_active=False,
               measured_angle_deg=0.0, requested_angle_deg=0.0, last_angle_deg=0.0,
               v_ego=0.0, accel=0.0)
  assert plan.longitudinal[0].acc_state == ACC_ON
  assert list(counters) == []
  assert ap1_should_send_hold_clear(True, True, ACC_HOLD, 1) is True
  assert ap1_should_send_hold_clear(True, True, ACC_ON, 0) is True
  assert ap1_should_send_hold_clear(True, True, ACC_ON, 50) is False
  assert ap1_should_send_hold_clear(True, False, ACC_HOLD, 0) is False
  assert ap1_should_send_hold_clear(False, True, ACC_HOLD, 0) is False
  assert longitudinal_command_allowed(True, True, False) is False


def test_stalk_commands_and_silent_steer_event():
  assert ap1_hso_event_names(["steerTempUnavailable"]) == ["steerTempUnavailableSilent"]
  assert ap1_hso_event_names(["steerUnavailable"]) == ["steerUnavailable"]
  decision = map_stalk_follow(0)
  assert ap1_stalk_commands(decision) == (True, None)
  assert follow_seconds(decision) == 1.0
  assert ap1_stalk_commands(map_stalk_follow(SNA)) == (None, None)
  assert apply_stalk_t_follow(1.75, 1.25, True) == 1.25
  assert apply_stalk_t_follow(1.75, 1.25, False) == 1.75
