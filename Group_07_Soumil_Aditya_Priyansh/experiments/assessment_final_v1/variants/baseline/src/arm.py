"""ArmCommander: rate-limited set-points for lift / arm / wrist / gripper / head (smooth, no jerks)."""
import math
import numpy as np
import config as C

SPEED = dict(lift=C.LIFT_SPEED, ext=C.ARM_SPEED, wrist_yaw=C.WRIST_SPEED, wrist_pitch=C.WRIST_SPEED,
             wrist_roll=C.WRIST_SPEED, gripper=C.GRIPPER_SPEED, head_pan=C.HEAD_SPEED, head_tilt=C.HEAD_SPEED)
ACT = dict(lift="lift", ext="arm", wrist_yaw="wrist_yaw", wrist_pitch="wrist_pitch", wrist_roll="wrist_roll",
           gripper="gripper", head_pan="head_pan", head_tilt="head_tilt")
RANGE = dict(lift=(0.0, 1.1), ext=(0.0, 0.52), wrist_yaw=(-1.39, 4.42), wrist_pitch=(-1.57, 0.56), wrist_roll=(-3.14, 3.14),
             gripper=(-0.02, 0.04), head_pan=(-4.04, 1.73), head_tilt=(-1.53, 0.79))
TOL = dict(lift=0.012, ext=0.010, wrist_yaw=0.05, wrist_pitch=0.05, wrist_roll=0.05, gripper=0.004, head_pan=0.06, head_tilt=0.06)


class ArmCommander:
    def __init__(self, robot):
        self.rb = robot
        self.sp = {}; self.goal = {}
        self.sync_from_ctrl()

    def sync_from_ctrl(self):
        d, a = self.rb.d, self.rb.act
        for k, an in ACT.items(): self.sp[k] = float(d.ctrl[a[an]])
        self.goal = dict(self.sp)

    def measured(self, k):
        rb = self.rb
        return {"lift": rb.lift(), "ext": rb.arm_ext(), "wrist_yaw": rb.q("joint_wrist_yaw"), "wrist_pitch": rb.q("joint_wrist_pitch"),
                "wrist_roll": rb.q("joint_wrist_roll"), "gripper": rb.gripper(), "head_pan": rb.q("joint_head_pan"),
                "head_tilt": rb.q("joint_head_tilt")}[k]

    def set(self, **kw):
        for k, v in kw.items():
            lo, hi = RANGE[k]; self.goal[k] = float(min(max(v, lo), hi))

    def update(self, dt):
        d, a = self.rb.d, self.rb.act
        for k in ACT:
            step = SPEED[k] * dt
            self.sp[k] += float(np.clip(self.goal[k] - self.sp[k], -step, step))
            d.ctrl[a[ACT[k]]] = self.sp[k]

    def settled(self, keys=None, tol_scale=1.0):
        for k in (keys or ACT):
            if abs(self.sp[k] - self.goal[k]) > 1e-6: return False
            if k == "gripper": continue          # may legitimately stall on an object
            if abs(self.measured(k) - self.goal[k]) > TOL[k] * tol_scale: return False
        return True

    def hold_gc_z(self, z_target, dt, gain=1.0):
        """Closed-loop: drive the lift so the gripper centre reaches z_target (compensates sag)."""
        err = z_target - self.rb.gc()[2]
        self.goal["lift"] = float(min(max(self.rb.lift() + gain * err, RANGE["lift"][0]), RANGE["lift"][1]))
        return err
