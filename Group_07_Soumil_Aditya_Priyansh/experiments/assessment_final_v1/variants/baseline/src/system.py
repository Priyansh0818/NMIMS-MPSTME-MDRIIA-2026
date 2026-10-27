"""System: builds the complete simulation + autonomy stack once (shared by the launcher, tests and batch trials)."""
import math, time
import numpy as np
import mujoco
import config as C
from robot import RobotInterface
from scene import ClutterManager
from navigation import NavigationManager
from detection import ObjectDetector, WorldModel, Track
from grasp import GraspPlanner
from sorting import SortingManager
from telemetry import TelemetryManager
from controller import CleaningController


class System:
    def __init__(self, seed=0, verbose=True, tag=None, out_dir=None, only=None, model_path=None):
        self.seed = seed
        self.model_path = str(model_path or C.MODEL_PATH)
        self.model = mujoco.MjModel.from_xml_path(self.model_path); self.data = mujoco.MjData(self.model)
        self.rb = RobotInterface(self.model, self.data, model_path=self.model_path); self.rb.reset()
        self.nav = NavigationManager(self.rb); self.nav.rebuild([])
        self.cl = ClutterManager(self.rb); self.grasp = GraspPlanner(self.rb, self.nav)
        self.rng = np.random.default_rng(seed)
        bad = self.cl.randomize(self.rng, validator=self._reachable)
        for _ in range(3):
            if not bad: break
            bad = self.cl.randomize(self.rng, validator=self._reachable)
        self.spawn_unstable = bad
        if only:                                    # debugging aid: keep only some objects in the room
            for n in self.cl.names:
                if n not in only: self.data.qpos[self.cl.qadr[n]:self.cl.qadr[n] + 3] = [-8, -8, 0.1]
        self.world = WorldModel(); self.det = ObjectDetector(self.rb, self.cl)
        self.sorter = SortingManager(self.rb, self.nav)
        self.tele = TelemetryManager(tag=tag, out_dir=out_dir)
        self.ctrl = CleaningController(self.rb, self.nav, self.det, self.world, self.cl, self.grasp, self.sorter, self.tele, verbose=verbose)
        self.dt = self.model.opt.timestep
        self.ctrl_every = int(round(1.0 / C.CONTROL_HZ / self.dt)); self._n = 0
        self.run_start = float(self.data.time)
        self.tele.start_run(self, seed)

    def _reachable(self, name, xy, top):
        """Spawn validator: grasp approach poses must exist even with ~1 cm perception error (surface objects get 3 probes)."""
        probes = [(0.0, 0.0, 0.0)] if top < 0.2 else [(0.0, 0.0, 0.0), (0.012, 0.012, 0.01), (-0.012, -0.012, 0.01)]
        for dx, dy, dz in probes:
            tr = Track(dict(name=name, xy=np.array((xy[0] + dx, xy[1] + dy)), top=top + dz, support=0.0, type=name.split("_")[0],
                            category="X", conf=1.0, height=top, range=1.0), 0.0)
            cands, _ = self.grasp.candidates(tr, "clutter_" + name, self.cl.body[name], include_clutter=False)
            if len(cands) < 2: return False
        return True

    def step_physics(self, n=1):
        m, d = self.model, self.data
        for _ in range(n):
            mujoco.mj_step(m, d); self._n += 1
            if self._n % self.ctrl_every == 0: self.ctrl.step(self.ctrl_every * self.dt)
            self.tele.physics_sample(self)
            if self.done: break

    @property
    def done(self): return self.ctrl.state == "DONE"

    def ground_truth_summary(self, wall=0.0, trial=0):
        cl, sorter, ctrl, world = self.cl, self.sorter, self.ctrl, self.world
        total = len(cl.names); detected = len(world.votes)
        correct = 0
        for n, v in world.votes.items():
            pred = max(set(v), key=v.count); correct += int(pred == cl.type_of[n])
        cleaned = 0
        placed = set()
        for n in cl.names:
            zone = C.CATEGORY_TO_ZONE[C.CATEGORY_OF_TYPE[cl.type_of[n]]]
            if sorter.verify_placement(zone, cl.pos(n), cl.half_h[n]):
                cleaned += 1; placed.add(n)
        failed_names = {n for n, tr in world.tracks.items() if tr.status == Track.FAILED} - placed
        result = self.tele.summary(self.data.time - self.run_start, total, detected, correct,
                                   cleaned, len(failed_names), wall=wall, trial=trial, seed=self.seed)
        result.update(pending=total - cleaned - len(failed_names),
                      run_status=("completed" if cleaned == total else "exhausted") if self.done else "in_progress",
                      physics_hz=1.0/self.dt, controller_hz=1.0/(self.ctrl_every*self.dt),
                      telemetry_hz=1.0/self.dt, samples=self.tele.physics_rows,
                      effort_by_actuator=self.tele.effort.tolist())
        return result
