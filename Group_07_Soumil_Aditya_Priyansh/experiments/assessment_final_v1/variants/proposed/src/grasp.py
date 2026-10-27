"""GraspPlanner: object estimate -> ranked, collision-checked top-down pinch grasps with approach base poses."""
import math
import numpy as np
import config as C
from robot import rot2, wrap
import navigation as N


class GraspCandidate:
    def __init__(self, pose, ext, lift_hover, lift_grasp, roll=0.0, refine_only=False):
        self.pose, self.ext, self.lift_hover, self.lift_grasp, self.roll = pose, ext, lift_hover, lift_grasp, roll
        self.refine_only = refine_only

    def key(self): return (round(self.pose[0], 2), round(self.pose[1], 2), round(self.pose[2], 2))


class GraspPlanner:
    def __init__(self, robot, nav):
        self.rb, self.nav = robot, nav
        self.last_stats = {}

    def object_support_bodies(self, name_body_id, xy, top):
        """Bodies directly under / next to the object (ignored by the grasp-pose contact check)."""
        import raycast, mujoco
        rb = self.rb; out = set()
        for dx, dy in [(0, 0), (0.04, 0), (-0.04, 0), (0, 0.04), (0, -0.04)]:
            gid, dist = raycast.ray1_excl(rb.m, rb.d, (xy[0] + dx, xy[1] + dy, top + 0.2), (0, 0, -1.0), name_body_id)
            if gid > 0: out.add(rb.m.body(rb.m.geom_bodyid[gid]).name)
        return out

    def candidates(self, track, body_name, body_id, used=(), headings=None, include_clutter=True, allow_refinement=False):
        rb, nav = self.rb, self.nav
        ox, oy = track.xy; top = track.top
        z_hover = top + C.HOVER_CLEARANCE
        z_grasp = max(C.GRASP_MIN_Z, top - C.GRASP_DEPTH)
        lift_h, lift_g = z_hover - rb.gc_z0, z_grasp - rb.gc_z0
        if not (C.LIFT_RANGE[0] <= lift_g and lift_h <= C.LIFT_RANGE[1]): return [], dict(reason="lift_range")
        support = self.object_support_bodies(body_id, track.xy, top)
        ignore_grasp = {body_name}   # supporting furniture is NOT ignored: pads must clear it
        ks = range(N.NK) if headings is None else headings
        raw = []; stats = dict(total=0, cspace=0, reach=0, coll=0)
        for ext in C.APPROACH_EXTS:
            if not (C.EXT_RANGE[0] <= ext <= C.EXT_RANGE[1]): continue
            for k in ks:
                psi = k * N.DK; stats["total"] += 1
                axis = getattr(track, 'long_axis_yaw', None)
                if track.type == 'slipper' and axis is not None:
                    # Open fingers separate along base X. Pinch across the
                    # slipper's short axis rather than across its full length.
                    if abs(math.cos(psi-axis)) > math.sin(math.radians(25)):
                        continue
                local = np.array([rb.gc_x, rb.gc_y0 - ext])
                base = np.array([ox, oy]) - rot2(psi) @ local
                if not nav.cs.valid(base[0], base[1], psi): continue
                stats["cspace"] += 1
                if any(math.hypot(base[0] - u[0], base[1] - u[1]) < 0.12 and abs(wrap(psi - u[2])) < 0.2 for u in used): continue
                raw.append(GraspCandidate((float(base[0]), float(base[1]), psi), ext, lift_h, lift_g))
        good = []; observation = []
        for cand in raw:
            ok = False
            for extra in (0.0, 0.06, 0.12):                   # try progressively higher hover heights to clear furniture edges
                lh = cand.lift_hover + extra
                if lh > C.LIFT_RANGE[1]: break
                post_h = dict(lift=lh, ext=cand.ext, wrist_yaw=0.0, wrist_pitch=C.TRAVEL_PITCH, wrist_roll=0.0, gripper=C.GRIPPER_OPEN)
                if not rb.collisions(cand.pose, post_h, ignore={body_name}, margin=0.02, include_clutter=include_clutter):
                    cand.lift_hover = lh; ok = True; break
            if not ok:
                stats["coll"] += 1
                for b in rb.collisions(cand.pose, post_h, ignore={body_name}, margin=0.02, include_clutter=include_clutter): stats.setdefault('hit', {}); stats['hit'][b] = stats['hit'].get(b, 0) + 1
                continue
            post_g = dict(post_h, lift=cand.lift_grasp)
            hg = rb.collisions(cand.pose, post_g, ignore=ignore_grasp, margin=0.004, include_clutter=include_clutter)
            if hg:
                stats["coll"] += 1
                for b in hg: stats.setdefault('hit', {}); stats['hit'][b] = stats['hit'].get(b, 0) + 1
                # A distant depth estimate can be ~2 cm off at a bed edge. A
                # safe hover permits a wrist-camera observation, not permission
                # to descend through the supporting furniture. The controller
                # must revalidate the descent after that closer measurement.
                if allow_refinement and set(hg).issubset(support):
                    cand.refine_only = True; observation.append(cand)
                continue
            good.append(cand)
        if not good and observation:
            good = observation; stats['observation_only'] = len(observation)
        stats["valid"] = len(good); self.last_stats = stats
        return good, stats

    def plan_approach(self, track, body_name, body_id, used=()):
        """Pick the cheapest reachable candidate (single multi-goal A*).  Returns candidate or None."""
        cands, stats = self.candidates(track, body_name, body_id, used, allow_refinement=True)
        if not cands: return None
        goals = [c.pose for c in cands]
        if not self.nav.plan_to(goals): return None
        gx, gy, gyaw = self.nav.goal
        return min(cands, key=lambda c: math.hypot(c.pose[0] - gx, c.pose[1] - gy) + abs(wrap(c.pose[2] - gyaw)))
