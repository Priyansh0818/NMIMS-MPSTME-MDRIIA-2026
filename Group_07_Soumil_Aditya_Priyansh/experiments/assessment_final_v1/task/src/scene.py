"""Clutter spawning: randomised-but-valid initial placement (no teleporting during a run)."""
import math
import numpy as np
import mujoco
import config as C
import raycast

GT_SPHERE, GT_CAP, GT_CYL, GT_BOX = 2, 3, 5, 6


class ClutterManager:
    def __init__(self, robot):
        self.rb = robot; m = robot.m
        self.names = [n[len("clutter_"):] for n in robot.clutter_bodies]      # e.g. 'cup_1'
        self.type_of = {n: n.split("_")[0] for n in self.names}
        self.body = {n: m.body("clutter_" + n).id for n in self.names}
        self.qadr = {n: int(m.joint(n + "_free").qposadr[0]) for n in self.names}
        self.vadr = {n: int(m.joint(n + "_free").dofadr[0]) for n in self.names}
        self.geom = {n: m.geom(n + "_geom").id for n in self.names}
        self.geom_ids = set(self.geom.values())
        g = self.geom
        self.half_h = {}
        for n in self.names:
            t = int(m.geom_type[g[n]]); s = m.geom_size[g[n]]
            self.half_h[n] = {GT_SPHERE: s[0], GT_CYL: s[1], GT_CAP: s[1] + s[0], GT_BOX: s[2]}[t]
        self.spawn = {}      # ground-truth initial xy (evaluation only)

    def pos(self, n): return self.rb.d.xpos[self.body[n]].copy()

    def world_half_extents(self, n):
        """Actual orientation-aware bounding half-sizes, for placement evaluation."""
        g = self.geom[n]; m, d = self.rb.m, self.rb.d
        size = m.geom_size[g]; rotation = d.geom_xmat[g].reshape(3, 3)
        typ = int(m.geom_type[g]); axis = rotation[:, 2]
        if typ == GT_BOX: return np.abs(rotation) @ size
        if typ == GT_SPHERE: return np.full(3, size[0])
        if typ == GT_CYL:
            return np.abs(axis)*size[1] + size[0]*np.sqrt(np.maximum(0, 1-axis*axis))
        if typ == GT_CAP: return size[0] + np.abs(axis)*size[1]
        raise ValueError(f'Unsupported clutter shape {typ}')

    def _surface_z(self, x, y):
        gid, dist = raycast.ray1(self.rb.m, self.rb.d, (x, y, 1.9), (0, 0, -1.0), cutoff=3.0)
        return 1.9 - dist if gid >= 0 else None

    def randomize(self, rng, settle_s=1.5, validator=None):
        m, d = self.rb.m, self.rb.d
        for k, n in enumerate(self.names):                          # park everything far away first
            a = self.qadr[n]; d.qpos[a:a + 7] = [-6 + 0.4 * k, -6, 0.2, 1, 0, 0, 0]; d.qvel[self.vadr[n]:self.vadr[n] + 6] = 0
        mujoco.mj_forward(m, d)
        placed = {}
        for n in self.names:
            x0, x1, y0, y1, mode = C.SPAWN[n]
            for _ in range(60):
                x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
                if any(math.hypot(x - px, y - py) < 0.14 for px, py in placed.values()): continue
                sz = self._surface_z(x, y)
                if sz is None: continue
                if mode == "floor" and sz > 0.02: continue          # landed on furniture -> invalid floor spot
                if mode == "surface" and sz < 0.15: continue
                if validator is not None and not validator(n, (x, y), sz + 2 * self.half_h[n]): continue
                yaw = rng.uniform(-math.pi, math.pi) if C.SPAWN_JITTER_YAW else 0.0
                a = self.qadr[n]
                d.qpos[a:a + 3] = [x, y, sz + self.half_h[n] + 0.004]
                d.qpos[a + 3:a + 7] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
                placed[n] = (x, y); break
            else:
                raise RuntimeError(f"could not place {n}")
        mujoco.mj_forward(m, d)
        for _ in range(int(settle_s / m.opt.timestep)): mujoco.mj_step(m, d)
        bad = [n for n in self.names if np.linalg.norm(d.qvel[self.vadr[n]:self.vadr[n] + 3]) > 0.05 or
               math.hypot(*(self.pos(n)[:2] - np.array(placed[n]))) > 0.12]
        self.spawn = {n: self.pos(n) for n in self.names}
        return bad
