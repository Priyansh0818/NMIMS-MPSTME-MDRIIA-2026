"""CleaningController: the single state machine (runs at CONTROL_HZ).
SCAN -> SELECT -> NAV_APPROACH -> PREGRASP -> REFINE -> DESCEND -> CLOSE -> VERIFY_GRIP -> LIFT -> STOW ->
PLAN_DROP -> NAV_DROP -> DROP_DEPLOY -> RELEASE -> VERIFY_PLACE -> RETRACT -> SELECT ...  -> DONE
Nothing is teleported: every motion is an actuator command executed by MuJoCo physics.
"""
import math
import numpy as np
import mujoco
import config as C
from robot import rot2, wrap
from arm import ArmCommander
import navigation as N
from detection import Track

VANTAGE = [(2.75, 1.05), (0.55, -1.65), (-0.75, 1.35), (2.95, -1.95), (-0.75, -0.2)]
SCAN_W = 0.9


class CleaningController:
    def __init__(self, robot, nav, detector, world, clutter, grasp, sorter, tele, debug=False, verbose=True):
        self.rb, self.nav, self.det, self.world, self.cl = robot, nav, detector, world, clutter
        self.grasp, self.sorter, self.tele = grasp, sorter, tele
        self.arm = ArmCommander(robot); self.verbose = verbose; self.debug = debug
        self.t = 0.0; self.state = "INIT"; self.t_state = 0.0; self.sub = 0
        self.target = None; self.cand = None; self.drop = None
        self.retract_object = None
        self.vantage_left = [v for v in VANTAGE]; self.vantage_goal = None
        self.scan_yaw = 0.0; self.scan_last = None; self._last_det = -1.0; self.scans_done = 0
        self.collision_active = False; self.obj_collisions = 0
        self.task_t0 = 0.0; self.pickup_t = None; self.carry_t0 = None; self.nav_time = 0.0; self.task_nav_t0 = 0.0
        self.z0_obj = 0.0; self.stable_t = 0.0; self.blocked_t = 0.0; self.replans = 0; self.detect_miss_t = 0.0
        self.cleaned = []; self.failed = []; self.msgs = []; self.grasp_ok_flag = False
        self.revisit_round = 0
        self.last_drop_height = 0.1
        self.v_cmd = 0.0; self.w_cmd = 0.0; self.avoid_discs = []; self.last_contact_t = -9.0; self.nav_goals = []

    # ------------------------------------------------------------------ utilities
    def log(self, msg):
        line = f"[{self.t:7.1f}s] {msg}"; self.msgs.append(line); self.msgs = self.msgs[-40:]
        if self.verbose: print(line, flush=True)

    def goto(self, state):
        self.state, self.t_state, self.sub = state, 0.0, 0

    def travel_posture(self, lift=None):
        self.arm.set(ext=0.0, wrist_yaw=0.0, wrist_pitch=C.TRAVEL_PITCH, wrist_roll=0.0, lift=lift if lift is not None else C.TRAVEL_LIFT)

    def clutter_obstacles(self, exclude=()):
        # Uncollected failed tasks are still physical obstacles.
        return [tuple(tr.xy) for tr in self.world.tracks.values()
                if tr.status != Track.DONE and tr.name not in exclude]

    def grip_force(self, name):
        gid = self.cl.geom[name]; tot = 0.0; f = np.zeros(6)
        for i in range(self.rb.d.ncon):
            c = self.rb.d.contact[i]
            other = c.geom2 if c.geom1 == gid else (c.geom1 if c.geom2 == gid else -1)
            if other >= 0 and other in self.rb.finger_geoms:
                mujoco.mj_contactForce(self.rb.m, self.rb.d, i, f); tot += abs(f[0])
        return tot

    def obj_pos(self, name): return self.cl.pos(name)

    def monitor_collisions(self, timestamp=None):
        rb = self.rb; d = rb.d; hit = False
        now = self.t if timestamp is None else float(timestamp)
        ign = set()
        if self.target is not None and self.state in ("PREGRASP", "REFINE", "DESCEND", "CLOSE", "VERIFY_GRIP", "LIFT", "RECOVER",
                                                      "STOW", "PLAN_DROP", "NAV_DROP", "DROP_DEPLOY", "RELEASE", "VERIFY_PLACE"):
            ign.add(self.cl.geom[self.target.name])
        if self.state == 'RETRACT' and self.retract_object is not None:
            ign.add(self.cl.geom[self.retract_object])
        for i in range(d.ncon):
            c = d.contact[i]; a, b = c.geom1, c.geom2
            if rb.geom_robot[a] == rb.geom_robot[b]: continue
            o = b if rb.geom_robot[a] else a
            if rb.geom_floor[o]: continue
            robot_geom = a if rb.geom_robot[a] else b
            if o in ign and robot_geom in rb.finger_geoms: continue
            if (self.state in ("DESCEND", "CLOSE", "VERIFY_GRIP", "RECOVER", "REFINE") and
                    rb.geom_env[o] and robot_geom in rb.finger_geoms):
                # fingertips resting on the supporting surface during the grasp are expected
                if self.rb.m.body(self.rb.m.geom_bodyid[o]).name in getattr(self, "support", ()): continue
            if self.state in ("DROP_DEPLOY", "RELEASE", "VERIFY_PLACE", "RETRACT") and self.rb.m.body(self.rb.m.geom_bodyid[o]).name in self.sorter.zone:
                pass   # still a collision if the arm touches a bin; counted
            hit = (self.rb.m.body(self.rb.m.geom_bodyid[a if rb.geom_robot[a] else b]).name, self.rb.m.body(self.rb.m.geom_bodyid[o]).name); break
        if hit and not self.collision_active and now - self.last_contact_t > 1.0:
            self.tele.collision(); self.obj_collisions += 1
            self.log(f"COLLISION detected in {self.state}: robot '{hit[0]}' vs '{hit[1]}'")
        if hit: self.last_contact_t = now
        self.collision_active = bool(hit)

    # ------------------------------------------------------------------ main step
    def step(self, dt):
        self.t += dt; self.t_state += dt
        if self.target is not None and self.state in ('STOW','PLAN_DROP','NAV_DROP'):
            force = self.grip_force(self.target.name)
            if force < C.HOLD_MIN_FORCE:
                change = min(.001, C.HOLD_FORCE_GAIN*(C.HOLD_MIN_FORCE-force)*dt)
                self.arm.set(gripper=self.arm.goal['gripper']-change)
        getattr(self, "s_" + self.state.lower())(dt)
        self.arm.update(dt, gripper_speed=C.RELEASE_GRIPPER_SPEED if self.state == 'RELEASE' else None)
        if self.state.startswith("NAV"): self.nav_time += dt
        self.tele.sample(self.t, self.rb.base_pose(), self.state, self.target.name if self.target else None, self.nav.follower.v,
                         self.nav.follower.w, self.rb.lift(), self.rb.arm_ext(), self.rb.gripper(), self.rb.d.ncon, self.collision_active)

    # ------------------------------------------------------------------ states
    def s_init(self, dt):
        self.rb.drive(0, 0); self.travel_posture()
        if self.t_state > 1.0: self.arm.sync_from_ctrl(); self.begin_scan()

    def begin_scan(self):
        self.goto("SCAN"); self.scan_yaw = 0.0; self.scan_last = self.rb.base_pose()[2]; self.new_found = 0
        self.arm.set(head_pan=0.0, head_tilt=C.SCAN_HEAD_TILT); self.travel_posture()
        self.log(f"Scanning room (spin #{self.scans_done + 1})")

    def s_scan(self, dt):
        yaw = self.rb.base_pose()[2]
        if self.nav.safety.check_rotation(self.rb.base_pose(), 1):
            self.nav.stop()
            self.log('Scan rotation obstructed; choose a mapped task or a different vantage')
            self.goto('SELECT'); return
        self.scan_yaw += abs(wrap(yaw - self.scan_last)); self.scan_last = yaw
        self.nav.follower._ramp(0.0, SCAN_W, dt); self.rb.drive(0.0, self.nav.follower.w)
        if self.t - self._last_det >= 1.0 / C.PERCEPTION_HZ:
            self._last_det = self.t
            self.new_found += self.world.integrate(self.det.detect("head"), self.t)
        if self.scan_yaw >= 2 * math.pi + 0.15:
            self.nav.stop(); self.scans_done += 1
            self.log(f"Scan complete: {len(self.world.tracks)} objects known ({self.new_found} new)")
            self.goto("SELECT")

    def s_select(self, dt):
        self.rb.drive(0, 0)
        pend = [t for t in self.world.pending() if t.attempts < C.MAX_GRASP_ATTEMPTS]
        if not pend:
            retry = [t for t in self.world.tracks.values()
                     if t.status == Track.FAILED and t.attempts < C.MAX_GRASP_ATTEMPTS]
            if retry and self.revisit_round < 1:
                self.revisit_round += 1
                for tr in retry: tr.status = Track.PENDING; tr.used_poses = []
                self.log(f'Rechecking {len(retry)} failed task(s) after clearing other clutter')
                return
            # All catalogue items have been observed and their attempts are
            # complete. Additional search spins cannot discover another item.
            if len(self.world.tracks) == len(self.cl.names):
                self.log('All catalogue tasks attempted; stopping for verified placement evaluation')
                self.goto('DONE'); return
            if self.vantage_left:
                x, y, _ = self.rb.base_pose()
                vp = min(self.vantage_left, key=lambda p: math.hypot(p[0] - x, p[1] - y)); self.vantage_left.remove(vp)
                self.nav.rebuild(self.clutter_obstacles())
                goals = [(vp[0], vp[1], k * N.DK) for k in range(0, N.NK, 3)]
                if self.nav.plan_to(goals): self.vantage_goal = vp; self.log(f"Searching: moving to vantage {vp}"); self.goto("NAV_VANTAGE"); return
                self.log(f"vantage {vp} unreachable; skipping"); return
            self.log("Search finished: no pending tracks; consult verified placement summary for room outcome"); self.goto("DONE"); return
        x, y, _ = self.rb.base_pose()
        key = {"nearest": lambda t: math.hypot(t.xy[0] - x, t.xy[1] - y),
               "confidence": lambda t: -t.conf, "category": lambda t: (t.category, math.hypot(t.xy[0] - x, t.xy[1] - y))}[C.PRIORITY]
        skipped = []
        for tr in sorted(pend, key=key):
            self.nav.rebuild(self.clutter_obstacles())      # the target itself stays an obstacle: never drive over it
            cand = self.grasp.plan_approach(tr, "clutter_" + tr.name, self.cl.body[tr.name], used=tr.used_poses)
            if cand is None:
                st = self.grasp.last_stats
                blockers = set(st.get("hit", {}))
                if blockers and all(b.startswith("clutter_") for b in blockers) and len(pend) > 1:
                    skipped.append(tr); continue                # blocked only by other clutter: try again after they are cleaned
                self.log(f"{tr.name}: no feasible approach ({st}) -> marking FAILED")
                self.finish_object(tr, "UNREACHABLE", zone="")
                continue
            self.target, self.cand = tr, cand
            self.support = self.grasp.object_support_bodies(self.cl.body[tr.name], tr.xy, tr.top)
            self.task_t0 = self.t; self.obj_collisions = 0; self.nav_time = 0.0; self.pickup_t = None; self.carry_t0 = None
            zone = self.sorter.zone_for(tr.category)
            self.log(f"Target {tr.name} [{tr.type}→{tr.category}→{zone}] at ({tr.xy[0]:.2f},{tr.xy[1]:.2f},top {tr.top:.2f}) "
                     f"approach pose ({cand.pose[0]:.2f},{cand.pose[1]:.2f},{math.degrees(cand.pose[2]):.0f}°) plan {self.nav.last_plan_ms:.0f} ms")
            self.travel_posture(); self.arm.set(gripper=C.GRIPPER_OPEN)
            self.replans = 0; self.blocked_t = 0.0; self.goto("NAV_APPROACH"); return
        if skipped:
            tr = skipped[0]; self.log(f"{tr.name}: blocked by neighbouring clutter and nothing else to do -> marking FAILED"); self.finish_object(tr, "UNREACHABLE", zone="")

    def _navigate(self, dt, target_state, fail_cb, ignore=()):
        if self.t - self._last_det >= 1.0 / C.PERCEPTION_HZ:          # keep mapping clutter while driving
            self._last_det = self.t
            new = self.world.integrate(self.det.detect("head"), self.t)
            if new and self.nav.goal is not None:
                self.log(f"  new object(s) seen while driving ({new}); updating map and re-planning")
                excl = {self.target.name} if (self.target is not None and self.state == "NAV_DROP") else set()
                self.nav.occ = self.nav.grid.with_discs([(*c, C.CLUTTER_OBSTACLE_R) for c in self.clutter_obstacles(exclude=excl)] + self.avoid_discs)
                self.nav.cs.build(self.nav.occ); self.nav.cs_tight.build(self.nav.occ)
                if not self.nav.plan_to([self.nav.goal]): self.tele.nav_leg(False); self.nav.stop(); fail_cb("NO_REPLAN"); return
        res = self.nav.step(dt, ignore_geoms=ignore)
        if res == "BLOCKED":
            self.blocked_t += dt
            if self.blocked_t > 1.5:
                self.blocked_t = 0.0; self.replans += 1
                x, y, yaw = self.rb.base_pose(); hits = [tuple(rot2(yaw) @ np.array(h) + np.array([x, y])) for h in self.nav.safety.last_hits]
                self.avoid_discs += [(hx, hy, 0.10) for hx, hy in hits[:6]]
                self.log(f"Path blocked (lidar) -> replan #{self.replans}")
                if self.replans > C.REPLAN_LIMIT: self.tele.nav_leg(False); fail_cb("NAV_BLOCKED"); return
                self.nav.occ = self.nav.grid.with_discs([(*c, C.CLUTTER_OBSTACLE_R) for c in self.clutter_obstacles()] + self.avoid_discs)
                self.nav.cs.build(self.nav.occ)
                goals = [self.goal_pose]
                if not self.nav.plan_to(goals): self.tele.nav_leg(False); fail_cb("NO_REPLAN")
            return
        self.blocked_t = 0.0
        if self.nav.arrived:
            self.nav.stop(); self.tele.nav_leg(True); self.goto(target_state)
        elif self.t_state > 150: self.nav.stop(); self.tele.nav_leg(False); fail_cb("NAV_TIMEOUT")

    @property
    def goal_pose(self): return self.nav.goal

    def s_nav_vantage(self, dt):
        self._navigate(dt, "SCAN_AT_VANTAGE", lambda r: (self.log(f"vantage nav failed: {r}"), self.goto("SELECT")))

    def s_scan_at_vantage(self, dt): self.avoid_discs = []; self.begin_scan()

    def s_nav_approach(self, dt):
        self._navigate(dt, "PREGRASP", self.fail_attempt, ignore={self.cl.geom[self.target.name]})

    def s_pregrasp(self, dt):
        c = self.cand
        if self.sub == 0:
            self.arm.set(wrist_roll=c.roll, wrist_pitch=C.TRAVEL_PITCH, gripper=C.GRIPPER_OPEN,
                         lift=max(c.lift_hover, self.rb.lift()))
            self.sub = 1
        elif self.sub == 1 and self.arm.settled(["lift", "wrist_roll", "wrist_pitch"]):
            self.arm.set(ext=c.ext); self.sub = 2
        elif self.sub == 2 and self.arm.settled(["ext", "gripper"]) :
            self.goto("REFINE"); self.detect_miss_t = 0.0; self.stable_t = 0.0
        elif self.t_state > 25: self.fail_attempt("PREGRASP_TIMEOUT")

    def s_refine(self, dt):
        """Wrist-camera look at the target; creep the base to centre it between the fingers; fix arm extension."""
        rb, tr = self.rb, self.target; x, y, yaw = rb.base_pose()
        if self.t - self._last_det >= 1.0 / C.PERCEPTION_HZ:
            self._last_det = self.t
            dets = self.det.detect("wrist", only=tr.name)
            if dets:
                dd = dets[0]; self.detect_miss_t = 0.0
                tr.xy = 0.3 * tr.xy + 0.7 * dd["xy"]; tr.top = 0.3 * tr.top + 0.7 * dd["top"]
                if dd.get('long_axis_yaw') is not None: tr.long_axis_yaw = dd['long_axis_yaw']
            else: self.detect_miss_t += 1.0 / C.PERCEPTION_HZ
        loc = rot2(yaw).T @ (tr.xy - np.array([x, y]))
        ex = loc[0] - rb.gc_x                       # error along robot forward axis (cannot be fixed by the arm)
        ext_new = -(loc[1] - rb.gc_y0)
        if C.EXT_RANGE[0] <= ext_new <= C.EXT_RANGE[1]: self.arm.set(ext=ext_new)
        v = 0.0
        if abs(ex) > 0.008: v = float(np.clip(1.5 * ex, -C.BASE_V_FINAL, C.BASE_V_FINAL))
        self.nav.follower._ramp(v, 0.0, dt); rb.drive(self.nav.follower.v, 0.0)
        ok = abs(ex) <= 0.012 and abs(self.arm.measured("ext") - self.arm.goal["ext"]) < 0.01
        self.stable_t = self.stable_t + dt if ok else 0.0
        if self.stable_t > 0.3 or (self.detect_miss_t > 1.5 and self.t_state > 3):
            self.nav.stop(); self.log(f"  refined {tr.name}: lateral err {ex*100:.1f} cm, ext {self.arm.goal['ext']:.2f} m")
            axis = getattr(tr, 'long_axis_yaw', None)
            if tr.type == 'slipper' and axis is not None and abs(math.cos(yaw-axis)) > math.sin(math.radians(30)):
                self.fail_attempt('SLIPPER_ROTATION_REPLAN'); return
            if self.cand.refine_only:
                post = dict(lift=max(C.GRASP_MIN_Z, tr.top-C.GRASP_DEPTH)-rb.gc_z0,
                            ext=self.arm.goal['ext'], wrist_yaw=0.0, wrist_pitch=C.TRAVEL_PITCH,
                            wrist_roll=self.cand.roll, gripper=C.GRIPPER_OPEN)
                hits = rb.collisions(rb.base_pose(), post, ignore={'clutter_'+tr.name}, margin=.002)
                if self.detect_miss_t > 0 or hits:
                    self.log(f"  wrist observation did not establish a clear descent: {hits}")
                    self.fail_attempt('OBSERVATION_BLOCKED'); return
                self.log('  wrist observation established a collision-free descent')
            self.goto("DESCEND"); self.stable_t = 0.0
        elif self.t_state > 20: self.nav.stop(); self.fail_attempt("REFINE_TIMEOUT")

    def s_descend(self, dt):
        tr = self.target; z = max(C.GRASP_MIN_Z, tr.top - C.GRASP_DEPTH)
        err = self.arm.hold_gc_z(z, dt)
        ok = abs(err) < 0.006
        self.stable_t = self.stable_t + dt if ok else 0.0
        if self.stable_t > 0.4: self.arm.set(gripper=C.GRIPPER_CLOSE); self.goto("CLOSE")
        elif self.t_state > 20: self.fail_attempt("DESCEND_TIMEOUT")

    def s_close(self, dt):
        if self.t_state > 1.4: self.goto("VERIFY_GRIP")

    def s_verify_grip(self, dt):
        tr = self.target; f = self.grip_force(tr.name); q = self.rb.gripper()
        ok = f >= C.MIN_GRIP_FORCE and q > -0.006
        if ok:
            self.z0_obj = self.obj_pos(tr.name)[2]
            hold = max(C.GRIPPER_CLOSE, q - C.HOLD_SQUEEZE)      # moderate holding force, avoids squeeze-out and release 'pop'
            self.arm.sp["gripper"] = self.arm.goal["gripper"] = hold
            lift_up = min(self.rb.lift() + C.CARRY_LIFT_EXTRA, C.LIFT_RANGE[1])
            self.arm.set(lift=lift_up); self.log(f"  grip OK: {f:.0f} N, aperture {q*1000:.0f} mm -> lifting")
            self.goto("LIFT")
        elif self.t_state > 0.6:
            self.log(f"  grip FAILED: force {f:.1f} N, aperture {q*1000:.1f} mm"); self.tele.grasp(False); self.fail_attempt("NO_GRIP", counted=True)

    def held(self, name, tol=0.10): return np.linalg.norm(self.obj_pos(name) - self.rb.gc()) < tol

    def s_lift(self, dt):
        tr = self.target
        if self.arm.settled(["lift"], 1.5) and self.t_state > 0.8:
            rise = self.obj_pos(tr.name)[2] - self.z0_obj
            if rise >= C.LIFT_VERIFY_RISE and self.held(tr.name):
                self.tele.grasp(True); self.pickup_t = self.t - self.task_t0; self.carry_t0 = self.t
                self.last_drop_height = tr.height
                # Base/marker geometry reaches above 0.20 m. The previous
                # 0.13 m payload-bottom assumption made a held cube scrape the
                # base during retraction and slip while turning.
                need = C.CARRY_MIN_BOTTOM_Z + max(tr.height - C.GRASP_DEPTH, 0.0) - self.rb.gc_z0 + 0.03
                self.carry_lift = max(C.TRAVEL_LIFT, need)
                self.log(f"  lift verified (+{rise*100:.0f} cm) -> stowing arm")
                self.arm.set(lift=max(self.carry_lift, self.rb.lift())); self.goto("STOW")
            else:
                self.log(f"  lift check FAILED (rise {rise*100:.1f} cm)"); self.tele.grasp(False); self.fail_attempt("LIFT_FAIL", counted=True)
        elif self.t_state > 8: self.tele.grasp(False); self.fail_attempt("LIFT_TIMEOUT", counted=True)

    def s_stow(self, dt):
        if not self.held(self.target.name, 0.12): self.dropped(); return
        if self.sub == 0 and self.arm.settled(['lift'], 1.5):
            self.arm.set(ext=0.0); self.sub = 1
        elif self.sub == 1 and self.arm.settled(["ext", "lift"], 1.5): self.goto("PLAN_DROP")
        elif self.t_state > 15:
            self.log('  stow failed to settle; stopping the carry attempt')
            self.drop_fail('STOW_TIMEOUT')

    def dropped(self):
        tr = self.target; self.log(f"  {tr.name} DROPPED during carry -> will re-scan")
        self.tele.carry_drops += 1
        # Retain the hazard in the global map. Prefer a fresh camera estimate;
        # if occluded, predict its last held position rather than using ground truth.
        dets = self.det.detect('wrist', only=tr.name)
        if not dets: dets = self.det.detect('head', only=tr.name)
        if dets:
            tr.xy = dets[0]['xy'].copy(); tr.top = dets[0]['top']
            tr.last_seen = self.t; tr.n_obs += 1
        else:
            tr.xy = self.rb.gc()[:2].copy(); tr.top = max(tr.height, self.rb.gc()[2])
        tr.attempts += 1; tr.used_poses = []
        if tr.attempts >= C.MAX_GRASP_ATTEMPTS:
            self.finish_object(tr, 'REPEATED_DROP', self.sorter.zone_for(tr.category))
        self.arm.set(gripper=C.GRIPPER_OPEN); self.target = None
        self.rb.drive(0, 0); self.goto("RECOVER"); self.recover_next = "RESCAN"

    def measure_hold_offset(self):
        """Wrist-camera estimate of where the held object sits relative to the gripper centre (base frame, x/y)."""
        x, y, yaw = self.rb.base_pose(); offs = []
        for _ in range(3):
            dets = self.det.detect("wrist", only=self.target.name)
            if dets: offs.append(rot2(yaw).T @ (dets[0]["xy"] - self.rb.gc()[:2]))
        if not offs: return np.zeros(2)
        return np.clip(np.median(offs, axis=0), -0.09, 0.09)

    def s_plan_drop(self, dt):
        tr = self.target; zone = self.sorter.zone_for(tr.category)
        self.nav.rebuild(self.clutter_obstacles(exclude={tr.name}))
        self.avoid_discs = []
        self.hold_off = self.measure_hold_offset(); toff = self.sorter.next_offset(zone)
        drop = self.sorter.plan_drop(zone, tr.height, self.hold_off, toff, held_body='clutter_'+tr.name)
        if drop is None:
            self.log(f"  no safe receiving pose for {zone} ({self.sorter.last_reason}); holding payload and stopping")
            self.nav.stop(); self.finish_object(tr, 'NO_DROP_POSE', zone); self.goto('SAFE_STOP'); return
        self.drop = drop; self.nav.goal = drop.pose; self.sorter.count[zone] = self.sorter.count.get(zone, 0) + 1
        self.log(f"  carrying to {zone}; hold offset ({self.hold_off[0]*100:.0f},{self.hold_off[1]*100:.0f}) cm; drop pose ({drop.pose[0]:.2f},{drop.pose[1]:.2f},{math.degrees(drop.pose[2]):.0f}°)")
        if self.sorter.last_offset_attempts > 1:
            self.log(f"  found alternate placement after {self.sorter.last_offset_attempts} receiving-point checks")
        self.replans = 0; self.blocked_t = 0.0; self.goto("NAV_DROP")

    def s_nav_drop(self, dt):
        if not self.held(self.target.name, 0.14): self.dropped(); return
        self._navigate(dt, "DROP_DEPLOY", lambda r: self.drop_fail(r))

    def drop_fail(self, reason):
        tr = self.target; self.log(f"  delivery stopped ({reason}); retaining the payload")
        self.nav.stop(); self.finish_object(tr, reason, self.sorter.zone_for(tr.category))
        self.goto('SAFE_STOP')

    def s_drop_deploy(self, dt):
        if not self.held(self.target.name, .14):
            if self.sub >= 2:
                self.log('  load separated during placement; stop and verify the receiving zone')
                self.nav.stop(); self.arm.set(ext=self.rb.arm_ext(), lift=self.rb.lift(), gripper=C.GRIPPER_OPEN)
                self.goto('RELEASE')
            else: self.dropped()
            return
        if self.sub == 0:
            self.arm.set(lift=max(self.drop.lift_hover, self.rb.lift())); self.sub = 1
        elif self.sub == 1 and self.arm.settled(["lift"], 1.5):
            self.arm.set(ext=self.drop.ext); self.sub = 2
        elif self.sub == 2 and self.arm.settled(["ext"], .5):
            self.sub = 3; self.stable_t = 0
        elif self.sub == 3:
            xy_error = self.align_receiving_point()
            self.stable_t = self.stable_t+dt if xy_error<.004 else 0
            if self.stable_t>.25:
                self.nav.stop(); self.sub=4; self.stable_t=0
        elif self.sub == 4:
            xy_error = self.align_receiving_point()
            error = self.arm.hold_gc_z(self.drop.release_z, dt)
            self.stable_t = self.stable_t+dt if abs(error)<.004 and xy_error<.004 else 0
            if self.stable_t > .3:
                self.nav.stop(); self.goto("RELEASE"); self.stable_t=0
        if self.t_state > 30: self.drop_fail('DEPLOY_TIMEOUT')

    def align_receiving_point(self):
        """Close the loop on robot kinematics and the mapped bin, not object ground truth."""
        yaw=self.rb.base_pose()[2]
        error=rot2(yaw).T @ (self.drop.target_xy-self.rb.gc()[:2])
        self.arm.set(ext=self.rb.arm_ext()-error[1])
        self.rb.drive(float(np.clip(1.2*error[0], -.025, .025)), 0)
        return float(np.linalg.norm(error))

    def s_release(self, dt):
        self.arm.hold_gc_z(self.drop.release_z, dt)
        if self.sub == 0:
            force=self.grip_force(self.target.name)
            if force>C.RELEASE_MAX_FORCE:
                self.arm.set(gripper=self.arm.sp['gripper']+C.RELEASE_RELAX_SPEED*dt)
                self.stable_t=0
            else:
                # Freeze as soon as the item separates. Fully sweeping open
                # fingers through a light cube can act like a catapult.
                self.arm.set(gripper=self.arm.sp['gripper']); self.stable_t+=dt
            if self.stable_t>.12:
                self.sub=1; self.release_free_at=self.t_state
            elif self.t_state>18:
                self.drop_fail('RELEASE_TIMEOUT'); return
        if self.sub == 1 and self.t_state-self.release_free_at>.6:
            self.goto("VERIFY_PLACE"); self.stable_t = 0.0

    def s_verify_place(self, dt):
        tr = self.target; zone = self.sorter.zone_for(tr.category)
        v = np.linalg.norm(self.rb.d.qvel[self.cl.vadr[tr.name]:self.cl.vadr[tr.name] + 3])
        self.stable_t = self.stable_t + dt if v < 0.03 else 0.0
        if self.stable_t > 0.5 or self.t_state > 5:
            half = self.cl.world_half_extents(tr.name)
            ok = self.sorter.verify_placement(zone, self.obj_pos(tr.name), half[2], half[:2])
            sort_t = self.t - (self.carry_t0 or self.t)
            if ok: self.log(f"  placement VERIFIED: {tr.name} in {zone} (sort time {sort_t:.0f}s)")
            else: self.log(f"  placement FAILED: {tr.name} not in {zone} at {np.round(self.obj_pos(tr.name),2)}")
            self.retract_object = tr.name
            self.finish_object(tr, "CLEANED" if ok else "MISPLACED", zone, sort_t=sort_t)
            self.arm.set(lift=max(self.drop.lift_hover, self.rb.lift()))
            self.goto("RETRACT")

    def s_retract(self, dt):
        if self.sub == 0 and self.arm.settled(["lift"], 1.5):
            self.arm.set(ext=0.0, gripper=C.GRIPPER_OPEN); self.sub = 1
        elif self.sub == 1 and self.arm.settled(["ext"], 1.5): self.travel_posture(); self.sub = 2
        elif self.sub == 2 and self.arm.settled(["lift"], 2.0):
            self.check_withdrawal(); self.goto("SELECT")
        elif self.t_state > 20:
            self.travel_posture(); self.check_withdrawal(); self.goto("SELECT")

    def check_withdrawal(self):
        name=self.retract_object; self.retract_object=None
        if name is None: return
        tr=self.world.tracks[name]; zone=self.sorter.zone_for(tr.category)
        half=self.cl.world_half_extents(name)
        if tr.status==Track.DONE and not self.sorter.verify_placement(zone,self.obj_pos(name),half[2],half[:2]):
            self.log(f'  {name} placement did not survive tool withdrawal; scheduling recovery')
            self.finish_object(tr,'WITHDRAWAL_MISPLACED',zone)
            if name in self.cleaned: self.cleaned.remove(name)
            tr.attempts+=1
            if tr.attempts<C.MAX_GRASP_ATTEMPTS: tr.status=Track.PENDING
            dets=self.det.detect('wrist',only=name) or self.det.detect('head',only=name)
            if dets: tr.xy=dets[0]['xy'].copy(); tr.top=dets[0]['top']

    def s_recover(self, dt):
        """Open the gripper, lift clear, retract, return to travel posture (used after any failure)."""
        if self.sub == 0:
            self.arm.set(gripper=C.GRIPPER_OPEN, lift=min(max(self.rb.lift(), C.TRAVEL_LIFT) + 0.12, C.LIFT_RANGE[1])); self.sub = 1
        elif self.sub == 1 and self.t_state > 1.0 and self.arm.settled(["lift"], 2.0):
            self.arm.set(ext=0.0); self.sub = 2
        elif self.sub == 2 and self.arm.settled(["ext"], 2.0):
            self.travel_posture(); self.sub = 3
        elif self.sub == 3 and self.arm.settled(["lift"], 2.0):
            nxt = getattr(self, "recover_next", "SELECT")
            if nxt == "RESCAN": self.begin_scan()
            else: self.goto("SELECT")
        elif self.t_state > 20: self.travel_posture(); self.goto("SELECT")

    def s_done(self, dt): self.rb.drive(0, 0)

    def s_safe_stop(self, dt): self.rb.drive(0, 0)

    # ------------------------------------------------------------------ bookkeeping
    def fail_attempt(self, reason, counted=False):
        tr = self.target; self.nav.stop()
        if tr is None: self.goto("SELECT"); return
        tr.attempts += 1; tr.used_poses.append(self.cand.pose)
        self.log(f"  attempt {tr.attempts}/{C.MAX_GRASP_ATTEMPTS} for {tr.name} failed: {reason}")
        if tr.attempts >= C.MAX_GRASP_ATTEMPTS:
            self.finish_object(tr, "GRASP_FAILED", self.sorter.zone_for(tr.category))
        else:
            self.target = None
        self.goto("RECOVER"); self.recover_next = "SELECT"

    def finish_object(self, tr, result, zone, sort_t=0.0):
        tr.status = Track.DONE if result == "CLEANED" else Track.FAILED
        if result == 'CLEANED':
            if tr.name not in self.cleaned: self.cleaned.append(tr.name)
            if tr.name in self.failed: self.failed.remove(tr.name)
        elif tr.name not in self.failed: self.failed.append(tr.name)
        active = self.target is tr
        total = self.t - self.task_t0 if active else 0.0
        self.tele.object_event(self.t, object=tr.name, type=tr.type, **{"class": tr.category}, destination=zone,
                               obj_x=f"{tr.xy[0]:.3f}", obj_y=f"{tr.xy[1]:.3f}", nav_time=f"{self.nav_time if active else 0:.1f}",
                               grasp_attempts=tr.attempts + (1 if result == "CLEANED" else 0),
                               grasp_success=int(active and self.pickup_t is not None), collisions=self.obj_collisions if active else 0,
                               pickup_time=f"{self.pickup_t:.1f}" if active and self.pickup_t is not None else "", sort_time=f"{sort_t:.1f}",
                               total_time=f"{total:.1f}", result=result)
        self.log(f"Object {tr.name}: {result} (cleaned {len(self.cleaned)}, failed {len(self.failed)}, "
                 f"remaining {len(self.world.pending())})")
        if result in ("CLEANED", "MISPLACED"): self.target = None

    # ------------------------------------------------------------------ HUD
    def hud_lines(self):
        tr = self.target
        return [f"STATE {self.state}", f"target {tr.name if tr else '-'} [{tr.category if tr else '-'}]",
                f"cleaned {len(self.cleaned)}  failed {len(self.failed)}  remaining {len(self.world.pending())}",
                f"collision {'YES' if self.collision_active else 'no'}  contacts {self.rb.d.ncon}"]
