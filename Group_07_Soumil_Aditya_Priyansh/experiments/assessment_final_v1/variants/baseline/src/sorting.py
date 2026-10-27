"""SortingManager: category -> destination zone, drop-pose planning, physical placement verification."""
import math
import numpy as np
import mujoco
import config as C
from robot import rot2, wrap
import navigation as N


class DropCandidate:
    def __init__(self, pose, ext, lift_drop): self.pose, self.ext, self.lift_drop = pose, ext, lift_drop


class SortingManager:
    def __init__(self, robot, nav):
        self.rb, self.nav = robot, nav
        m, d = robot.m, robot.d
        self.zone = {}; self.count = {}
        for name, z in C.ZONES.items():
            bid = m.body(z["body"]).id
            self.zone[name] = dict(z, center=d.xpos[bid][:2].copy(), body_id=bid)

    OFFSETS = [(0, 0), (-0.07, 0.05), (0.07, -0.05), (-0.07, -0.05), (0.07, 0.05), (0, 0.085), (0, -0.085), (-0.09, 0), (0.09, 0)]

    def zone_for(self, category): return C.CATEGORY_TO_ZONE[category]

    def next_offset(self, zone_name):
        """Spread successive drops over the container so items do not pile up at one point."""
        k = self.count.get(zone_name, 0); z = self.zone[zone_name]
        dx, dy = self.OFFSETS[k % len(self.OFFSETS)]
        return np.array([dx * z["ix"] / 0.15, dy * z["iy"] / 0.15])

    def plan_drop(self, zone_name, held_height, hold_off_local=(0.0, 0.0), target_off=(0.0, 0.0)):
        rb, nav = self.rb, self.nav; z = self.zone[zone_name]
        cx, cy = np.array(z["center"]) + np.asarray(target_off)
        hold = np.asarray(hold_off_local, float)
        obj_bottom_over_gc = max(held_height - C.GRASP_DEPTH, 0.0)
        gc_z = z["rim_z"] + C.DROP_CLEARANCE + obj_bottom_over_gc
        lift = gc_z - rb.gc_z0
        self.last_reason = ""
        if lift > C.LIFT_RANGE[1]: self.last_reason = "lift_range"; return None
        cands = []
        for ext in C.DROP_EXTS:
            for k in range(N.NK):
                psi = k * N.DK
                base = np.array([cx, cy]) - rot2(psi) @ (np.array([rb.gc_x, rb.gc_y0 - ext]) + hold)
                if not nav.cs.valid(base[0], base[1], psi): continue
                post = dict(lift=lift, ext=ext, wrist_yaw=0.0, wrist_pitch=C.TRAVEL_PITCH, wrist_roll=0.0, gripper=C.GRIPPER_OPEN)
                if rb.collisions((base[0], base[1], psi), post, ignore=set(), margin=0.02, include_clutter=False): continue
                cands.append(DropCandidate((float(base[0]), float(base[1]), psi), ext, lift))
        if not cands: self.last_reason = "no_valid_drop_pose"; return None
        if not nav.plan_to([c.pose for c in cands]): self.last_reason = f"no_path ({len(cands)} valid poses)"; return None
        gx, gy, gyaw = nav.goal
        return min(cands, key=lambda c: math.hypot(c.pose[0] - gx, c.pose[1] - gy) + abs(wrap(c.pose[2] - gyaw)))

    def verify_placement(self, zone_name, obj_pos, half_h=0.0):
        """Physical check: object centre inside the container footprint and between its floor and just above its rim."""
        z = self.zone[zone_name]; cx, cy = z["center"]
        inside = abs(obj_pos[0] - cx) <= z["ix"] and abs(obj_pos[1] - cy) <= z["iy"]
        return bool(inside and z["floor_z"] - 0.03 <= obj_pos[2] <= z["rim_z"] + 0.03)
