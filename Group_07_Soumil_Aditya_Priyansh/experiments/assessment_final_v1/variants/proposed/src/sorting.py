"""SortingManager: category -> destination zone, drop-pose planning, physical placement verification."""
import math
import numpy as np
import mujoco
import config as C
from robot import rot2, wrap
import navigation as N


class DropCandidate:
    def __init__(self, pose, ext, lift_drop, lift_hover, release_z, target_xy):
        self.pose, self.ext, self.lift_drop = pose, ext, lift_drop
        self.lift_hover, self.release_z = lift_hover, release_z
        self.target_xy = np.asarray(target_xy, float)


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

    def plan_drop(self, zone_name, held_height, hold_off_local=(0.0, 0.0), target_off=(0.0, 0.0), held_body=None):
        """Try the requested receiving point, then alternate points inside the bin.

        Each point must have a collision-checked endpoint and a reachable route.
        Failure at one offset is not evidence that the entire bin is unreachable.
        """
        z = self.zone[zone_name]
        offsets = [np.zeros(2)]
        offsets += [np.array([dx,dy]) for dx,dy in [(-.025,0),(.025,0),(0,-.025),(0,.025),
                                                    (-.025,-.025),(.025,.025),(-.05,0),(.05,0)]]
        offsets += [np.asarray(target_off, float)]
        offsets += [np.array([dx*z['ix']/0.15, dy*z['iy']/0.15]) for dx,dy in self.OFFSETS]
        used = set(); reasons = []
        for offset in offsets:
            key = tuple(np.round(offset, 6))
            if key in used: continue
            used.add(key)
            result = self._plan_drop_at(zone_name, held_height, hold_off_local, offset, held_body)
            if result is not None:
                self.last_offset = offset.copy()
                self.last_offset_attempts = len(used)
                return result
            reasons.append(self.last_reason)
        self.last_offset_attempts = len(used)
        self.last_reason = f"all_{len(used)}_offsets_unavailable: " + ','.join(sorted(set(reasons)))
        return None

    def _plan_drop_at(self, zone_name, held_height, hold_off_local, target_off, held_body):
        rb, nav = self.rb, self.nav; z = self.zone[zone_name]
        cx, cy = np.array(z["center"]) + np.asarray(target_off)
        hold = np.asarray(hold_off_local, float)
        obj_bottom_over_gc = max(held_height - C.GRASP_DEPTH, 0.0)
        hover_z = z["rim_z"] + C.DROP_CLEARANCE + obj_bottom_over_gc
        # A shallow return tray already holding an item cannot admit the whole
        # open gripper alongside it. Release above its rim instead; deep bins
        # admit the fingertips and catch light-object separation motion.
        bottom = z['rim_z']+.02 if z['rim_z']-z['floor_z'] < .15 else max(z['floor_z']+.02,z['rim_z']-C.DROP_INSERTION_DEPTH)
        gc_z = bottom + obj_bottom_over_gc
        lift = gc_z - rb.gc_z0; lift_hover = hover_z-rb.gc_z0
        self.last_reason = ""
        if lift_hover > C.LIFT_RANGE[1]: self.last_reason = "lift_range"; return None
        cands = []
        for ext in C.DROP_EXTS:
            for k in range(N.NK):
                psi = k * N.DK
                # Centre the gripper inside the opening. The held item may sit
                # off-centre between fingers, but its bounds must still fit.
                obj_offset = np.asarray(target_off) + rot2(psi) @ hold
                if abs(obj_offset[0]) > z['ix']-.07 or abs(obj_offset[1]) > z['iy']-.07: continue
                base = np.array([cx, cy]) - rot2(psi) @ np.array([rb.gc_x, rb.gc_y0 - ext])
                if not nav.cs.valid(base[0], base[1], psi): continue
                post = dict(lift=lift, ext=ext, wrist_yaw=0.0, wrist_pitch=C.TRAVEL_PITCH, wrist_roll=0.0, gripper=C.GRIPPER_OPEN)
                pose = (float(base[0]), float(base[1]), psi)
                clear = True
                for level in np.linspace(lift_hover, lift, 5):
                    post['lift'] = float(level)
                    for aperture in [0.0, .01, .02, .03, C.GRIPPER_OPEN]:
                        post['gripper'] = aperture
                        if rb.collisions(pose, post, ignore={held_body} if held_body else set(),
                                         margin=.012, include_clutter=held_body is not None):
                            clear = False; break
                    if not clear: break
                if clear: cands.append(DropCandidate(pose, ext, lift, lift_hover, gc_z, (cx,cy)))
        if not cands: self.last_reason = "no_valid_drop_pose"; return None
        if not nav.plan_to([c.pose for c in cands]): self.last_reason = f"no_path ({len(cands)} valid poses)"; return None
        gx, gy, gyaw = nav.goal
        return min(cands, key=lambda c: math.hypot(c.pose[0] - gx, c.pose[1] - gy) + abs(wrap(c.pose[2] - gyaw)))

    def verify_placement(self, zone_name, obj_pos, half_h=0.0, half_xy=(0.0, 0.0)):
        """Physical containment, with 5 mm tolerance for contact compliance.

        Entire horizontal bounds must fit; the object must rest above the floor
        and penetrate the receiving opening rather than balance on its rim.
        """
        z = self.zone[zone_name]; cx, cy = z["center"]
        inside = (abs(obj_pos[0]-cx)+half_xy[0] <= z['ix']+.005 and
                  abs(obj_pos[1]-cy)+half_xy[1] <= z['iy']+.005)
        bottom = obj_pos[2]-half_h
        return bool(inside and bottom >= z['floor_z']-.005 and
                    obj_pos[2] <= z['rim_z']+.005 and bottom < z['rim_z']-.005)
