"""Collision-aware navigation:
   exact obstacle geometry -> occupancy grid -> C-space (measured, asymmetric footprint x heading) ->
   lattice A* over (x, y, heading) -> corner-cutting smoothing -> accel-limited path follower ->
   reactive lidar safety layer.   NavigationManager is the single navigation system.
"""
import heapq, math, time
import numpy as np
import mujoco
from scipy import ndimage
from scipy.spatial import ConvexHull
import config as C
from robot import rot2, wrap
import raycast

GT_PLANE, GT_SPHERE, GT_CAP, GT_CYL, GT_BOX = 0, 2, 3, 5, 6   # mjtGeom codes as plain ints
NK = C.N_HEADINGS
DK = 2 * math.pi / NK
DIRS8 = {k: (int(round(math.cos(k * DK))), int(round(math.sin(k * DK)))) for k in range(0, NK, NK // 8)}


def kbin(yaw): return int(round(wrap(yaw) / DK)) % NK


class OccupancyGrid:
    def __init__(self, robot):
        self.rb = robot; m = robot.m
        self.res = C.GRID_RES
        self.x0, self.y0 = C.GRID_X[0], C.GRID_Y[0]
        self.nx = int(round((C.GRID_X[1] - C.GRID_X[0]) / self.res)); self.ny = int(round((C.GRID_Y[1] - C.GRID_Y[0]) / self.res))
        xs = self.x0 + (np.arange(self.nx) + 0.5) * self.res; ys = self.y0 + (np.arange(self.ny) + 0.5) * self.res
        self.X, self.Y = np.meshgrid(xs, ys, indexing="ij")
        self.static = self._rasterise_static()

    def cell(self, x, y):
        return (min(max(int((x - self.x0) / self.res), 0), self.nx - 1), min(max(int((y - self.y0) / self.res), 0), self.ny - 1))

    def world(self, ix, iy): return (self.x0 + (ix + 0.5) * self.res, self.y0 + (iy + 0.5) * self.res)

    def _rasterise_static(self):
        m, d, rb = self.rb.m, self.rb.d, self.rb
        occ = np.zeros((self.nx, self.ny), bool)
        for g in np.where(rb.geom_env)[0]:
            t = int(m.geom_type[g]); s = m.geom_size[g]; R = d.geom_xmat[g].reshape(3, 3); c = d.geom_xpos[g]
            if t == GT_PLANE: continue
            if t == GT_BOX: ext_z = float(np.abs(R[2]) @ s)
            elif t == GT_SPHERE: ext_z = float(s[0])
            elif t == GT_CYL: ext_z = abs(R[2, 2]) * s[1] + math.sqrt(max(0, 1 - R[2, 2] ** 2)) * s[0]
            elif t == GT_CAP: ext_z = abs(R[2, 2]) * s[1] + s[0]
            else: ext_z = float(m.geom_rbound[g])
            if c[2] - ext_z > C.ROBOT_Z_MAX or c[2] + ext_z < 0.008: continue
            dx, dy = self.X - c[0], self.Y - c[1]
            pad = 0.5 * self.res * 1.0      # conservative rasterisation: thin walls must never fall between cell centres
            if t == GT_BOX and abs(R[2, 2]) > 0.98:
                lx = R[0, 0] * dx + R[1, 0] * dy; ly = R[0, 1] * dx + R[1, 1] * dy
                occ |= (np.abs(lx) <= s[0] + pad) & (np.abs(ly) <= s[1] + pad)
            elif t == GT_SPHERE:
                occ |= dx * dx + dy * dy <= (s[0] + pad) ** 2
            elif t in (GT_CYL, GT_CAP) and abs(R[2, 2]) > 0.98:
                occ |= dx * dx + dy * dy <= (s[0] + pad) ** 2
            elif t in (GT_CYL, GT_CAP) and abs(R[2, 2]) < 0.1:
                ax = R[:2, 2] / (np.linalg.norm(R[:2, 2]) + 1e-9); half = s[1] + (s[0] if t == GT_CAP else 0)
                al = dx * ax[0] + dy * ax[1]; cr = -dx * ax[1] + dy * ax[0]
                occ |= (np.abs(al) <= half + pad) & (np.abs(cr) <= s[0] + pad)
            else:
                occ |= dx * dx + dy * dy <= m.geom_rbound[g] ** 2
        return occ

    def with_discs(self, discs):
        occ = self.static.copy()
        for cx, cy, r in discs:
            occ |= (self.X - cx) ** 2 + (self.Y - cy) ** 2 <= r * r
        return occ


class CSpace:
    """blocked[k][ix,iy] is True if the robot's inflated footprint at heading bin k hits an obstacle."""
    def __init__(self, grid, footprint, margin=C.FOOTPRINT_MARGIN):
        self.grid = grid; self.res = grid.res
        ang = np.linspace(0, 2 * math.pi, 16, endpoint=False)
        inflated = (footprint[:, None, :] + margin * np.stack([np.cos(ang), np.sin(ang)], 1)[None]).reshape(-1, 2)
        h = inflated[ConvexHull(inflated).vertices]
        self.hull = h
        r = int(math.ceil(np.linalg.norm(h, axis=1).max() / self.res)) + 1
        ii, jj = np.meshgrid(np.arange(-r, r + 1), np.arange(-r, r + 1), indexing="ij")
        pts = np.stack([ii * self.res, jj * self.res], -1)
        self.kernels = []
        for k in range(NK):
            hp = h @ rot2(k * DK).T
            eq = ConvexHull(hp).equations
            inside = np.all(pts @ eq[:, :2].T + eq[:, 2] <= 0, axis=-1)
            self.kernels.append(inside.astype(float))

    def build(self, occ):
        occf = occ.astype(float)
        self.blocked = [ndimage.correlate(occf, K, mode="constant", cval=1.0) > 0 for K in self.kernels]
        self.clear = ndimage.distance_transform_edt(~occ) * self.res
        return self

    def valid(self, x, y, yaw):
        ix, iy = self.grid.cell(x, y)
        return not self.blocked[kbin(yaw)][ix, iy]

    def valid_cont(self, x, y, yaw):
        """Conservative validity for arbitrary heading: both neighbouring bins must be free."""
        ix, iy = self.grid.cell(x, y); f = wrap(yaw) / DK; k0 = int(math.floor(f)) % NK; k1 = (k0 + 1) % NK
        return not (self.blocked[k0][ix, iy] or self.blocked[k1][ix, iy])


class LatticePlanner:
    def __init__(self, cs): self.cs = cs

    def plan(self, start, goals, max_expand=400000, allow_reverse=False):
        cs, g = self.cs, self.cs.grid; nx, ny = g.nx, g.ny
        sx, sy = g.cell(start[0], start[1]); sk = kbin(start[2])
        blocked = [b.copy() for b in cs.blocked]
        if blocked[sk][sx, sy]:       # started inside the inflated zone (e.g. after a grasp): carve a way out
            rr = int(0.16 / g.res)
            for b in blocked: b[max(0, sx - rr):sx + rr + 1, max(0, sy - rr):sy + rr + 1] = False
            for b, ob in zip(blocked, cs.blocked):
                pass
        goalset = set(); gmask = np.ones((nx, ny), bool)
        for (x, y, yaw) in goals:
            ix, iy = g.cell(x, y); k = kbin(yaw)
            if not blocked[k][ix, iy]: goalset.add((ix, iy, k)); gmask[ix, iy] = False
        if not goalset: return None
        hfield = ndimage.distance_transform_edt(gmask)
        clear = cs.clear
        start_s = (sx, sy, sk)
        openh = [(float(hfield[sx, sy]), 0, start_s)]
        gcost = {start_s: 0.0}; parent = {}; cnt = 0; exp = 0
        while openh and exp < max_expand:
            f, _, s = heapq.heappop(openh); ix, iy, k = s
            if s in goalset: return self._extract(parent, s, start)
            gc = gcost[s]
            if f - float(hfield[ix, iy]) > gc + 1e-9: continue
            exp += 1
            for dk in (-1, 1):
                nk = (k + dk) % NK
                if blocked[nk][ix, iy]: continue
                ns = (ix, iy, nk); ng = gc + 0.06
                if ng < gcost.get(ns, 1e9):
                    gcost[ns] = ng; parent[ns] = s; cnt += 1; heapq.heappush(openh, (ng + hfield[ix, iy], cnt, ns))
            if k in DIRS8:
                for sgn, mult in (((1, 1.0), (-1, 2.2)) if allow_reverse else ((1, 1.0),)):   # reverse only as a fallback
                    dx, dy = DIRS8[k]; nx_, ny_ = ix + sgn * dx, iy + sgn * dy
                    if 0 <= nx_ < nx and 0 <= ny_ < ny and not blocked[k][nx_, ny_]:
                        step = g.res * (1.4142 if dx and dy else 1.0)
                        pen = 1.0 + 2.5 * max(0.0, 0.35 - clear[nx_, ny_]) / 0.35
                        ns = (nx_, ny_, k); ng = gc + step * pen * mult
                        if ng < gcost.get(ns, 1e9):
                            gcost[ns] = ng; parent[ns] = s; cnt += 1; heapq.heappush(openh, (ng + hfield[nx_, ny_] * g.res, cnt, ns))
        return None

    def _extract(self, parent, s, start):
        g = self.cs.grid; out = []
        while True:
            out.append(s)
            if s not in parent: break
            s = parent[s]
        out.reverse()
        return [(*g.world(ix, iy), k * DK) for ix, iy, k in out]


def make_segments(poses, cs, start_pose, goal_yaw_exact=None):
    """Poses (x,y,yaw lattice) -> primitives [('line', (x,y), reverse), ('rot', yaw, False)].
    Forward-only paths get corner-cutting; paths containing reverse runs keep their lattice runs."""
    if not poses: return []
    runs = []          # (end_xy, reverse, k)
    for a, b in zip(poses[:-1], poses[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) < 1e-6: continue
        rev = (b[0] - a[0]) * math.cos(a[2]) + (b[1] - a[1]) * math.sin(a[2]) < 0
        if runs and runs[-1][1] == rev and abs(wrap(runs[-1][2] - a[2])) < 1e-6: runs[-1] = ((b[0], b[1]), rev, a[2])
        else: runs.append(((b[0], b[1]), rev, a[2]))
    final_yaw = goal_yaw_exact if goal_yaw_exact is not None else poses[-1][2]
    if any(r[1] for r in runs):
        segs = []; acc = 0.0; cur_yaw = poses[0][2]; i = 1; prev = poses[0]
        def flush():
            nonlocal acc
            if abs(acc) > 1e-6: segs.append(("rot", wrap(prev[2]), False)); acc = 0.0
        for p in poses[1:]:
            mv = math.hypot(p[0] - prev[0], p[1] - prev[1])
            if mv < 1e-6:                                   # in-place rotation step
                acc += wrap(p[2] - prev[2])
                if abs(acc) >= math.radians(60): segs.append(("rot", wrap(p[2]), False)); acc = 0.0
            else:
                flush()
                rev = (p[0] - prev[0]) * math.cos(prev[2]) + (p[1] - prev[1]) * math.sin(prev[2]) < 0
                if segs and segs[-1][0] == "line" and segs[-1][2] == rev and abs(wrap(segs[-1][3] - prev[2])) < 1e-6: segs[-1] = ("line", (p[0], p[1]), rev, prev[2])
                else: segs.append(("line", (p[0], p[1]), rev, prev[2]))
            prev = p
        flush()
        segs = [s[:3] for s in segs]
        segs.append(("rot", final_yaw, False))
        return segs
    corners = [(start_pose[0], start_pose[1])] + [r[0] for r in runs]
    def line_ok(p, q, yaw0):
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        if L < 1e-6: return True
        th = math.atan2(q[1] - p[1], q[0] - p[0])
        for s in np.arange(0, L + 1e-9, cs.res * 0.5):
            x, y = p[0] + (q[0] - p[0]) * s / L, p[1] + (q[1] - p[1]) * s / L
            if not cs.valid_cont(x, y, th): return False
        n_ = max(1, int(abs(wrap(th - yaw0)) / (DK / 2)))
        return all(cs.valid_cont(p[0], p[1], yaw0 + wrap(th - yaw0) * i / n_) for i in range(n_ + 1))
    sm = [corners[0]]; i = 0; yaw = start_pose[2]
    while i < len(corners) - 1:
        j = len(corners) - 1
        while j > i + 1 and not line_ok(corners[i], corners[j], yaw): j -= 1
        sm.append(corners[j])
        yaw = math.atan2(corners[j][1] - corners[i][1], corners[j][0] - corners[i][0]); i = j
    segs = [("line", b, False) for a, b in zip(sm[:-1], sm[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-3]
    segs.append(("rot", final_yaw, False))
    return segs


class PathFollower:
    """Accel-limited unicycle follower for ('line', end) / ('rot', yaw) segments."""
    def __init__(self):
        self.segs = []; self.i = 0; self.v = 0.0; self.w = 0.0; self.s0 = None

    def set(self, segs, pose):
        self.segs = segs; self.i = 0; self.s0 = (pose[0], pose[1]); self.v = self.v; self.w = self.w

    @property
    def done(self): return self.i >= len(self.segs)

    def update(self, pose, dt, vmax=C.BASE_V_MAX, wmax=C.BASE_W_MAX):
        if self.done: return self._ramp(0.0, 0.0, dt)
        seg = self.segs[self.i]; kind, tgt = seg[0], seg[1]; rev = seg[2] if len(seg) > 2 else False
        x, y, yaw = pose
        if kind == "rot":
            e = wrap(tgt - yaw)
            if abs(e) < C.GOAL_YAW_TOL and abs(self.w) < 0.08: self._advance(pose); return self._ramp(0.0, 0.0, dt)
            wd = math.copysign(min(wmax, math.sqrt(2 * C.BASE_ALPHA_MAX * 0.8 * abs(e)), 2.5 * abs(e) + 0.05), e)
            return self._ramp(0.0, wd, dt)
        sx, sy = self.s0; ex, ey = tgt; L = math.hypot(ex - sx, ey - sy)
        if L < 1e-6: self._advance(pose); return self._ramp(0.0, 0.0, dt)
        u = ((ex - sx) / L, (ey - sy) / L)
        th = math.atan2(u[1], u[0]) + (math.pi if rev else 0.0)          # robot heading while driving this segment
        along = (x - sx) * u[0] + (y - sy) * u[1]; rem = L - along
        cte_h = (-u[0] if rev else u[0]) * (y - sy) - (-u[1] if rev else u[1]) * (x - sx)
        he = wrap(th - yaw)
        if rem < 0.02 or (rem < 0.06 and abs(self.v) < 0.03):
            self._advance(pose); return self._ramp(0.0, 0.0, dt)
        if abs(he) > 0.35 and along < 0.05:      # heading not yet aligned: turn first
            return self._ramp(0.0, math.copysign(min(wmax, 2.5 * abs(he)), he), dt)
        vd = min(vmax * (0.6 if rev else 1.0), math.sqrt(2 * C.BASE_A_MAX * 0.8 * max(rem, 0.0)) + 0.03)
        vd *= max(0.0, 1.0 - abs(he) / 0.7)
        wd = float(np.clip(2.2 * he - 1.6 * cte_h, -wmax, wmax))
        return self._ramp(-vd if rev else vd, wd, dt)

    def _advance(self, pose):
        if self.segs[self.i][0] == "line": self.s0 = self.segs[self.i][1]
        else: self.s0 = (pose[0], pose[1])
        self.i += 1

    def _ramp(self, vd, wd, dt):
        lim = C.BASE_A_MAX * dt * (1.5 if abs(vd) < abs(self.v) else 1.0)
        self.v += float(np.clip(vd - self.v, -lim, lim))
        self.w += float(np.clip(wd - self.w, -C.BASE_ALPHA_MAX * dt, C.BASE_ALPHA_MAX * dt))
        return self.v, self.w


class SafetyMonitor:
    """Reactive layer: lidar-like rays at 3 cm height (sees all clutter); any return inside the footprint swept ahead stops the base."""
    ANGLES = np.radians(np.arange(-180, 180, 6))

    def __init__(self, robot, hull):
        self.rb = robot; self.hull_pts = hull
        eq = ConvexHull(hull).equations; self.eq = eq
        self.dirs_local = np.stack([np.cos(self.ANGLES), np.sin(self.ANGLES), np.zeros_like(self.ANGLES)], 1)
        self.last_hits = []

    def check_rotation(self, pose, sign, ignore_geoms=()):
        """Returns True if a lidar return lies inside the footprint as it would be after turning ~15 deg in direction `sign`."""
        x, y, yaw = pose; R = rot2(yaw)
        wd = np.zeros((len(self.ANGLES), 3)); wd[:, :2] = self.dirs_local[:, :2] @ R.T
        gid, dist = raycast.cast(self.rb.m, self.rb.d, (x, y, 0.03), wd, cutoff=1.0)
        ok = (gid >= 0)
        if ignore_geoms: ok &= ~np.isin(gid, list(ignore_geoms))
        loc = self.dirs_local[:, :2] * dist[:, None]; hit = np.zeros(len(loc), bool)
        for a in (0.0, 0.12, 0.25):
            p = loc @ rot2(-sign * a).T
            hit |= np.all(p @ self.eq[:, :2].T + self.eq[:, 2] <= 0.0, axis=1)
        hit &= ok; self.last_hits = [(float(loc[i, 0]), float(loc[i, 1])) for i in np.where(hit)[0]]
        return bool(hit.any())

    def check(self, pose, direction_sign=1.0, lookahead=C.SAFETY_LOOKAHEAD, ignore_geoms=()):
        x, y, yaw = pose; R = rot2(yaw)
        wd = np.zeros((len(self.ANGLES), 3)); wd[:, :2] = self.dirs_local[:, :2] @ R.T
        gid, dist = raycast.cast(self.rb.m, self.rb.d, (x, y, 0.03), wd, cutoff=1.2)
        ok = (gid >= 0)
        if ignore_geoms: ok &= ~np.isin(gid, list(ignore_geoms))
        loc = self.dirs_local[:, :2] * dist[:, None]
        shift = np.array([direction_sign * lookahead, 0.0])
        inside = np.all((loc - shift) @ self.eq[:, :2].T + self.eq[:, 2] <= 0.0, axis=1) & ok
        self.last_hits = [(float(loc[i, 0]), float(loc[i, 1])) for i in np.where(inside)[0]]
        return bool(inside.any())


class NavigationManager:
    def __init__(self, robot):
        self.rb = robot
        self.grid = OccupancyGrid(robot)
        self.cs = CSpace(self.grid, robot.footprint)
        self.cs_tight = CSpace(self.grid, robot.footprint, margin=0.02)
        self.planner = LatticePlanner(self.cs)
        self.planner_tight = LatticePlanner(self.cs_tight)
        self.follower = PathFollower()
        ang = np.linspace(0, 2 * math.pi, 16, endpoint=False)
        infl = (robot.footprint[:, None, :] + 0.03 * np.stack([np.cos(ang), np.sin(ang)], 1)[None]).reshape(-1, 2)
        self.safety = SafetyMonitor(robot, infl[ConvexHull(infl).vertices])
        self.path_xy = []; self.segs = []; self.last_plan_ms = 0.0; self.blocked_count = 0; self.goal = None
        self.rebuild([])

    def rebuild(self, clutter_xy, extra_discs=()):
        discs = [(x, y, C.CLUTTER_OBSTACLE_R) for x, y in clutter_xy] + list(extra_discs)
        self.occ = self.grid.with_discs(discs)
        self.cs.build(self.occ); self.cs_tight.build(self.occ)

    def plan_to(self, goals, start=None):
        """goals: list of (x,y,yaw).  Returns True when a path was found and installed in the follower."""
        start = start or self.rb.base_pose()
        t = time.perf_counter()
        poses = None; used = self.cs
        for cs, pl, rev in ((self.cs, self.planner, False), (self.cs_tight, self.planner_tight, False),
                            (self.cs, self.planner, True), (self.cs_tight, self.planner_tight, True)):
            poses = pl.plan(start, goals, allow_reverse=rev); used = cs
            if poses: break
        self.last_plan_ms = (time.perf_counter() - t) * 1e3
        if not poses: self.segs = []; self.path_xy = []; return False
        gx, gy, gyaw = poses[-1]
        exact = min(goals, key=lambda p: math.hypot(p[0] - gx, p[1] - gy) + abs(wrap(p[2] - gyaw)))
        self.segs = make_segments(poses, used, start, goal_yaw_exact=exact[2])
        self.path_xy = [(start[0], start[1])] + [s[1] for s in self.segs if s[0] == "line"]
        self.goal = exact
        self.follower.set(self.segs, start)
        return True

    def reachable_cost(self, goals, start=None):
        poses = self.planner.plan(start or self.rb.base_pose(), goals); return poses

    @property
    def arrived(self): return self.follower.done

    def step(self, dt, check_safety=True, ignore_geoms=()):
        pose = self.rb.base_pose()
        v, w = self.follower.update(pose, dt)
        look = 0.03 + v * v / 1.2          # stopping distance at BASE_A_MAX*2
        blocked = False
        if check_safety and abs(v) > 0.05: blocked = self.safety.check(pose, math.copysign(1.0, v), look, ignore_geoms)
        elif check_safety and abs(v) <= 0.05 and abs(w) > 0.15: blocked = self.safety.check_rotation(pose, math.copysign(1.0, w), ignore_geoms)
        if blocked:
            self.blocked_count += 1; self.follower.v = 0.0; self.follower.w = 0.0; self.rb.drive(0.0, 0.0); return "BLOCKED"
        self.rb.drive(v, w)
        return "OK"

    def stop(self): self.follower.v = self.follower.w = 0.0; self.rb.drive(0.0, 0.0)
