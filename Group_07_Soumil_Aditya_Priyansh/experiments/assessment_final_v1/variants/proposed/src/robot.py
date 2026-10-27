"""RobotInterface: thin, cached access to the Stretch 3 inside MuJoCo + kinematic collision checking.
Nothing here moves the robot except by writing actuator controls (reset() is the only state write).
"""
import math
import numpy as np
import mujoco
from scipy.spatial import ConvexHull
import config as C

ARM_JOINTS = ["joint_arm_l3", "joint_arm_l2", "joint_arm_l1", "joint_arm_l0"]


def yaw_to_quat(yaw):
    return np.array([math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)])


def rot2(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s], [s, c]])


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class RobotInterface:
    ACT_NAMES = ["left_wheel_vel", "right_wheel_vel", "lift", "arm", "wrist_yaw", "wrist_pitch",
                 "wrist_roll", "gripper", "head_pan", "head_tilt"]

    def __init__(self, model, data, model_path=None):
        self.m, self.d = model, data
        self.model_path = str(model_path or C.MODEL_PATH)
        m = model
        self.act = {n: m.actuator(n).id for n in self.ACT_NAMES}
        self.base_id = m.body("base_link").id
        self.gc_id = m.body("link_grasp_center").id
        self.qadr = lambda j: int(m.joint(j).qposadr[0])
        self.vadr = lambda j: int(m.joint(j).dofadr[0])
        self.robot_bodies = self._subtree(self.base_id)
        self.geom_robot = np.array([m.geom_bodyid[g] in self.robot_bodies for g in range(m.ngeom)])
        self.geom_floor = np.array([m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE for g in range(m.ngeom)])
        self.clutter_bodies = {m.body(i).name: i for i in range(m.nbody) if m.body(i).name.startswith("clutter_")}
        self.geom_clutter = np.array([m.body(m.geom_bodyid[g]).name.startswith("clutter_") for g in range(m.ngeom)])
        physical = (m.geom_contype != 0) | (m.geom_conaffinity != 0)
        self.geom_env = ~(self.geom_robot | self.geom_floor | self.geom_clutter) & physical
        self.pad_geoms = [g for g in range(m.ngeom) if self.geom_robot[g] and
                          m.body(m.geom_bodyid[g]).name in ("rubber_tip_left", "rubber_tip_right",
                                                             "link_gripper_finger_left", "link_gripper_finger_right")]
        finger_bodies = self._subtree(m.body('link_gripper_finger_left').id) | self._subtree(m.body('link_gripper_finger_right').id)
        self.finger_geoms = {g for g in range(m.ngeom) if m.geom_bodyid[g] in finger_bodies}
        self.home_z = float(m.key("home").qpos[2])
        wl = m.body("link_left_wheel").id; wr = m.body("link_right_wheel").id
        self.wheel_track = float(np.linalg.norm(self.d.xpos[wl] - self.d.xpos[wr])) or 0.34
        self.gear = float(m.actuator_gear[self.act["left_wheel_vel"]][0])
        self.wheel_r = 0.0508
        self.ctrl_wheel_max = float(m.actuator_ctrlrange[self.act["left_wheel_vel"]][1])
        self.cm = None   # kinematic collision model (lazy)
        self._calibrate_geometry()

    # ------------------------------------------------------------------ basics
    def _subtree(self, root):
        m = self.m; out = set()
        for b in range(m.nbody):
            x = b
            while x > 0:
                if x == root: out.add(b); break
                x = m.body_parentid[x]
        return out

    def base_pose(self):
        R = self.d.xmat[self.base_id].reshape(3, 3)
        p = self.d.xpos[self.base_id]
        return float(p[0]), float(p[1]), math.atan2(R[1, 0], R[0, 0])

    def gc(self):
        return self.d.xpos[self.gc_id].copy()

    def q(self, name):
        return float(self.d.qpos[self.qadr(name)])

    def lift(self): return self.q("joint_lift")
    def arm_ext(self): return sum(self.q(j) for j in ARM_JOINTS)
    def gripper(self): return self.q("joint_gripper_slide")

    def reset(self, pose=None):
        pose = pose or C.START_POSE
        m, d = self.m, self.d
        mujoco.mj_resetDataKeyframe(m, d, m.key("home").id)
        d.qpos[0:3] = [pose[0], pose[1], self.home_z]
        d.qpos[3:7] = yaw_to_quat(pose[2])
        self.apply_posture(d.qpos, dict(lift=C.TRAVEL_LIFT, ext=0.0, wrist_yaw=0.0, wrist_pitch=C.TRAVEL_PITCH,
                                        wrist_roll=0.0, gripper=C.GRIPPER_OPEN, head_pan=0.0, head_tilt=C.SCAN_HEAD_TILT))
        d.qvel[:] = 0
        d.ctrl[:] = 0
        a = self.act
        d.ctrl[a["lift"]] = C.TRAVEL_LIFT; d.ctrl[a["arm"]] = 0.0; d.ctrl[a["wrist_yaw"]] = 0.0
        d.ctrl[a["wrist_pitch"]] = C.TRAVEL_PITCH; d.ctrl[a["wrist_roll"]] = 0.0
        d.ctrl[a["gripper"]] = C.GRIPPER_OPEN; d.ctrl[a["head_pan"]] = 0.0; d.ctrl[a["head_tilt"]] = C.SCAN_HEAD_TILT
        mujoco.mj_forward(m, d)

    def apply_posture(self, qpos, p):
        """Write joint positions (kinematic use only: reset() and the scratch collision model)."""
        if "lift" in p: qpos[self.qadr("joint_lift")] = p["lift"]
        if "ext" in p:
            for j in ARM_JOINTS: qpos[self.qadr(j)] = p["ext"] / 4.0
        for k, j in (("wrist_yaw", "joint_wrist_yaw"), ("wrist_pitch", "joint_wrist_pitch"), ("wrist_roll", "joint_wrist_roll"),
                     ("head_pan", "joint_head_pan"), ("head_tilt", "joint_head_tilt"), ("gripper", "joint_gripper_slide")):
            if k in p: qpos[self.qadr(j)] = p[k]
        if "gripper" in p:   # equality-coupled fingers: finger_open ~= 9.87 * slide (measured), so kinematic copies stay consistent
            for j in ("joint_gripper_finger_left_open", "joint_gripper_finger_right_open"): qpos[self.qadr(j)] = 9.87 * p["gripper"]

    # ------------------------------------------------------------------ wheel command
    def drive(self, v, w):
        """v [m/s], w [rad/s] -> wheel velocity servos (rad/s of motor, includes gear and friction FF)."""
        L = self.wheel_track
        vl, vr = v - w * L / 2, v + w * L / 2
        cl, cr = self._wheel_ctrl(vl), self._wheel_ctrl(vr)
        s = max(abs(cl), abs(cr)) / self.ctrl_wheel_max
        if s > 1: cl, cr = cl / s, cr / s
        self.d.ctrl[self.act["left_wheel_vel"]] = cl
        self.d.ctrl[self.act["right_wheel_vel"]] = cr

    def _wheel_ctrl(self, vel):
        if abs(vel) < 1e-4: return 0.0
        return self.gear * vel / self.wheel_r + math.copysign(C.WHEEL_FRICTION_FF, vel)

    # ------------------------------------------------------------------ geometry calibration
    def _scratch(self):
        d2 = mujoco.MjData(self.m)
        d2.qpos[:] = self.d.qpos
        return d2

    def _place(self, d2, pose):
        d2.qpos[0:3] = [pose[0], pose[1], self.home_z]
        d2.qpos[3:7] = yaw_to_quat(pose[2])

    def _calibrate_geometry(self):
        """Fit gripper-centre position (base frame) for the top-down pose: gc = (gx, gy0 - ext, gz0 + lift)."""
        m = self.m; d2 = self._scratch(); self._place(d2, (0, 0, 0))
        def gc_local(lift, ext, roll=0.0):
            self.apply_posture(d2.qpos, dict(lift=lift, ext=ext, wrist_yaw=0, wrist_pitch=C.TRAVEL_PITCH, wrist_roll=roll))
            mujoco.mj_kinematics(m, d2)
            return d2.xpos[self.gc_id].copy()
        a, b, c = gc_local(0.3, 0.0), gc_local(0.6, 0.0), gc_local(0.3, 0.2)
        self.gc_x = float(a[0]); self.gc_y0 = float(a[1]); self.gc_z0 = float(a[2] - 0.3)
        self.gc_roll_drift = float(abs(gc_local(0.3, 0.0, 1.0)[0] - a[0]))
        # sanity: affine model
        assert abs((b[2] - a[2]) - 0.3) < 1e-3 and abs((c[1] - a[1]) + 0.2) < 1e-3, "gc not affine in lift/ext"
        self.footprint = self._compute_footprint()

    def _compute_footprint(self):
        """Convex hull (base frame) of every colliding robot vertex in the travel posture."""
        m = self.m; d2 = self._scratch(); self._place(d2, (0, 0, 0))
        self.apply_posture(d2.qpos, dict(lift=C.TRAVEL_LIFT, ext=0.0, wrist_yaw=0, wrist_pitch=C.TRAVEL_PITCH,
                                         wrist_roll=0, gripper=C.GRIPPER_OPEN))
        mujoco.mj_kinematics(m, d2)
        pts = []
        for g in range(m.ngeom):
            if not self.geom_robot[g] or not (m.geom_contype[g] or m.geom_conaffinity[g]): continue
            R = d2.geom_xmat[g].reshape(3, 3); p = d2.geom_xpos[g]
            if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
                mid = m.geom_dataid[g]; a0 = m.mesh_vertadr[mid]; n = m.mesh_vertnum[mid]
                v = (R @ m.mesh_vert[a0:a0 + n].T).T + p
            else:
                r = m.geom_rbound[g]
                ang = np.linspace(0, 2 * math.pi, 12, endpoint=False)
                v = p + np.stack([r * np.cos(ang), r * np.sin(ang), np.zeros_like(ang)], 1)
            v = v[(v[:, 2] > 0.02) & (v[:, 2] < C.ROBOT_Z_MAX)]
            pts.append(v[:, :2])
        P = np.vstack(pts)
        h = ConvexHull(P)
        return P[h.vertices]

    # ------------------------------------------------------------------ kinematic collision model
    def _init_cm(self):
        self.cm = mujoco.MjModel.from_xml_path(self.model_path)
        self.cd = mujoco.MjData(self.cm)
        self._cm_env = np.where(self.geom_env | self.geom_clutter)[0]
        self._cm_robot_floor = self.geom_floor
        self._cm_body_names = [self.cm.body(i).name for i in range(self.cm.nbody)]

    def collisions(self, pose, posture, ignore=(), margin=0.015, include_clutter=True):
        """Return {body_name: min_dist} for robot-vs-environment proximity (< margin) at a hypothetical state."""
        if self.cm is None: self._init_cm()
        cm, cd = self.cm, self.cd
        cd.qpos[:] = self.d.qpos
        self._place(cd, pose)
        self.apply_posture(cd.qpos, posture)
        cm.geom_margin[:] = 0.0
        sel = self._cm_env if include_clutter else np.where(self.geom_env)[0]
        cm.geom_margin[sel] = margin
        mujoco.mj_kinematics(cm, cd)
        mujoco.mj_collision(cm, cd)
        hits = {}
        for i in range(cd.ncon):
            c = cd.contact[i]; g1, g2 = c.geom1, c.geom2
            r1, r2 = self.geom_robot[g1], self.geom_robot[g2]
            if r1 == r2: continue
            o = g2 if r1 else g1
            if self.geom_floor[o]: continue
            # A zero margin does not disable existing contacts. Honour the
            # caller's clutter policy in the returned hypothetical contacts too.
            if not include_clutter and self.geom_clutter[o]: continue
            nm = self._cm_body_names[cm.geom_bodyid[o]]
            if nm in ignore: continue
            hits[nm] = min(hits.get(nm, 9.0), float(c.dist))
        return hits
