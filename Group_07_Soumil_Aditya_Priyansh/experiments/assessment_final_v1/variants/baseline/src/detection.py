"""Perception stack (modular):
   SimulatedRGBDCamera  -> ray-cast depth + instance/colour sampling from a Stretch camera pose (no GL context,
                           runs headless, only invoked when the state machine requests it at PERCEPTION_HZ)
   ObjectDetector       -> instance clusters -> 3-D features
   ObjectClassifier     -> features -> object type + category + confidence   (swap for YOLO later)
   WorldModel           -> persistent tracks with status
"""
import math
import numpy as np
import mujoco
import config as C
import raycast


class SimulatedRGBDCamera:
    def __init__(self, robot, cam_name, size, fov_deg_xy=None):
        self.rb = robot; self.cam = robot.m.camera(cam_name).id
        W, H = size; self.W, self.H = W, H
        fovy = math.radians(robot.m.cam_fovy[self.cam]); aspect = W / H
        tx = math.tan(fovy / 2) * aspect; ty = math.tan(fovy / 2)
        u = (2 * (np.arange(W) + 0.5) / W - 1) * tx; v = (1 - 2 * (np.arange(H) + 0.5) / H) * ty
        U, V = np.meshgrid(u, v)
        dirs = np.stack([U, V, -np.ones_like(U)], -1).reshape(-1, 3)
        self.dirs_cam = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)

    def capture(self):
        d = self.rb.d
        o = d.cam_xpos[self.cam].copy(); R = d.cam_xmat[self.cam].reshape(3, 3)
        dirs = self.dirs_cam @ R.T
        gid, dist = raycast.cast(self.rb.m, d, o, dirs, cutoff=6.0)
        pts = o + dirs * dist[:, None]
        return dict(origin=o, gid=gid.reshape(self.H, self.W), dist=dist.reshape(self.H, self.W),
                    pts=pts.reshape(self.H, self.W, 3), fwd=-R[:, 2].copy())


class ObjectClassifier:
    def __init__(self, protos=C.TYPE_PROTOTYPES): self.protos = protos

    def classify(self, height, width, rgb):
        sc = {}
        for t, (h, w, c) in self.protos.items():
            dist = 3.0 * np.linalg.norm(np.array(rgb) - np.array(c)) + abs(height - h) / 0.04 + 0.3 * abs(width - w) / 0.04
            sc[t] = dist
        best = min(sc, key=sc.get)
        e = np.exp(-np.array(list(sc.values())) + sc[best]); conf = float(1.0 / e.sum())
        return best, C.CATEGORY_OF_TYPE[best], conf


class ObjectDetector:
    MIN_PIXELS = 2

    def __init__(self, robot, clutter, classifier=None):
        self.rb, self.cl = robot, clutter
        self.cls = classifier or ObjectClassifier()
        m = robot.m
        self.gid_to_name = {g: n for n, g in clutter.geom.items()}
        self.cam_head = SimulatedRGBDCamera(robot, "d435i_camera_rgb", C.SCAN_RAYS)
        self.cam_wrist = SimulatedRGBDCamera(robot, "d405_rgb", (64, 48))
        self.rgba = m.geom_rgba
        self.calls = 0

    def detect(self, cam="head", only=None):
        cam = self.cam_head if cam == "head" else self.cam_wrist
        fr = cam.capture(); self.calls += 1
        gid = fr["gid"]; pts = fr["pts"]; o = fr["origin"]
        out = []
        env_mask = (gid >= 0) & ~np.isin(gid, list(self.gid_to_name))
        for g, name in self.gid_to_name.items():
            if only and name != only: continue
            mk = gid == g
            n = int(mk.sum())
            if n < self.MIN_PIXELS: continue
            P = pts[mk]; ys, xs = np.where(mk)
            top = float(P[:, 2].max()); cen = P.mean(0)
            ext = P.max(0) - P.min(0); width = float(max(ext[0], ext[1]))
            # support height = median z of nearby non-object returns in the surrounding pixel window
            y0, y1, x0, x1 = max(ys.min() - 4, 0), ys.max() + 5, max(xs.min() - 4, 0), xs.max() + 5
            win = env_mask[y0:y1, x0:x1]; Q = pts[y0:y1, x0:x1][win]
            near = Q[np.linalg.norm(Q[:, :2] - cen[:2], axis=1) < 0.15]
            support = float(np.median(near[:, 2])) if len(near) >= 3 else 0.0
            height = max(top - support, 0.02)
            # the visible surface centroid is biased toward the camera by ~ half the object's width
            vh = cen[:2] - o[:2]; horiz = np.linalg.norm(vh); frac = horiz / (np.linalg.norm(cen - o) + 1e-9)
            est_xy = cen[:2] + (vh / (horiz + 1e-9)) * frac * min(0.5 * max(width, 0.04), 0.045)   # ~0 for top-down views
            rgb = tuple(self.rgba[g][:3])
            typ, cat, conf = self.cls.classify(height, max(width, 0.04), rgb)
            rng_ = float(np.linalg.norm(cen - o))
            conf *= min(1.0, n / 6.0)
            out.append(dict(name=name, xy=est_xy, top=top, support=support, height=height, width=width,
                            type=typ, category=cat, conf=conf, pixels=n, range=rng_))
        return out


class Track:
    PENDING, DONE, FAILED = "PENDING", "DONE", "FAILED"
    def __init__(self, det, t):
        self.name = det["name"]; self.xy = det["xy"].copy(); self.top = det["top"]; self.support = det["support"]
        self.type = det["type"]; self.category = det["category"]; self.conf = det["conf"]
        self.first_seen = t; self.last_seen = t; self.n_obs = 1; self.status = Track.PENDING
        self.attempts = 0; self.used_poses = []; self.nav_time = 0.0; self.height = det["height"]
        self.range = det["range"]

    def update(self, det, t):
        a = 0.5 if det["range"] <= self.range else 0.2          # trust closer observations more
        self.xy = (1 - a) * self.xy + a * det["xy"]; self.top = (1 - a) * self.top + a * det["top"]
        self.support = (1 - a) * self.support + a * det["support"]; self.height = (1 - a) * self.height + a * det["height"]
        if det["conf"] >= self.conf or det["range"] < self.range:
            self.type, self.category, self.conf = det["type"], det["category"], det["conf"]
        self.range = min(self.range, det["range"]); self.last_seen = t; self.n_obs += 1


class WorldModel:
    def __init__(self): self.tracks = {}; self.votes = {}

    def integrate(self, dets, t):
        new = 0
        for det in dets:
            self.votes.setdefault(det["name"], []).append(det["type"])
            tr = self.tracks.get(det["name"])
            if tr is None: self.tracks[det["name"]] = Track(det, t); new += 1
            elif tr.status == Track.PENDING: tr.update(det, t)
        return new

    def pending(self): return [t for t in self.tracks.values() if t.status == Track.PENDING]
