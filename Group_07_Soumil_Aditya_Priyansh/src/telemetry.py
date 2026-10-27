"""Physics samples at 500 Hz, lightweight status at 10 Hz, events and run provenance."""
import csv, json, os, time, hashlib, uuid
from pathlib import Path
import numpy as np
import config as C

EVENT_COLS = ["timestamp", "object", "type", "class", "destination", "obj_x", "obj_y", "nav_time", "grasp_attempts",
              "grasp_success", "collisions", "pickup_time", "sort_time", "total_time", "result"]
TS_COLS = ["timestamp", "x", "y", "heading", "state", "target", "v", "w", "lift", "ext", "gripper", "contacts", "collision"]
TRIAL_COLS = ["run_id", "condition", "trial", "seed", "run_status", "sim_time_s", "objects_total", "detected", "detection_acc", "classification_acc", "cleaned", "pending",
              "failed", "grasp_attempts", "grasp_success_rate", "nav_legs", "nav_success_rate", "collision_events",
              "collisions_per_object", "avg_pickup_s", "avg_sort_s", "total_clean_time_s", "wall_s"]


class TelemetryManager:
    def __init__(self, tag=None, out_dir=None):
        self.dir = out_dir or C.ANALYTICS_DIR; os.makedirs(self.dir, exist_ok=True)
        self.tag = (tag or time.strftime("%Y%m%d_%H%M%S"))+'_'+uuid.uuid4().hex[:8]
        self.ts_path = os.path.join(self.dir, f"timeseries_{self.tag}.csv")
        self.ev_path = os.path.join(self.dir, f"events_{self.tag}.csv")
        self._ts = open(self.ts_path, "w", newline=""); self._tsw = csv.writer(self._ts); self._tsw.writerow(TS_COLS)
        self._ev = open(self.ev_path, "w", newline=""); self._evw = csv.writer(self._ev); self._evw.writerow(EVENT_COLS)
        self.events = []; self.nav_legs = 0; self.nav_ok = 0; self.collision_events = 0
        self.grasp_attempts = 0; self.grasp_success = 0; self._last_ts = -1.0
        self.carry_drops = 0
        self.physics_rows = 0
        self._physics = None
        self.effort = np.zeros(10)
        self._physics_buffer = []
        self.physics_paths = []
        self.chunk_rows = 50000
        self._closed = False

    def start_run(self, system, seed):
        """Record exact provenance before the first controller step."""
        import mujoco
        self.effort = np.zeros(system.model.nu)
        self.run_id = self.tag
        names = [system.model.actuator(i).name for i in range(system.model.nu)]
        self._physics_columns = (['run_id','seed','condition','time_s','state','target','robot_collision','contact_count','base_x','base_y','base_yaw',
            'lift_m','extension_m','ee_x','ee_y','ee_z','ref_x','ref_y','ref_z','reference_valid',
            'error_x','error_y','error_z','base_vx','base_vy','base_wz'] +
            ['command_'+n for n in names] + ['force_'+n for n in names])
        self._open_chunk()
        self.seed = seed
        metadata = dict(run_id=self.tag, seed=seed, condition='proposed', mujoco=mujoco.__version__,
            scene_model=Path(system.model_path).name,
            sample_columns=self._physics_columns,
            collision_check_hz=1/system.model.opt.timestep,
            collision_policy='Robot/environment and unhandled clutter contacts every physics step; floor and intended finger-target/support interactions excluded; episodes separated by a 1 s contact-free gap',
            timestep_s=system.model.opt.timestep, control_hz=C.CONTROL_HZ,
            physics_log_hz=1/system.model.opt.timestep,
            reference='Calibrated top-down gripper position from instantaneous rate-limited arm setpoints; reference_valid limits applicability',
            effort='Per actuator integral of actuator_force squared over simulation time; retain force and torque channels separately',
            perception='Simulation ray/instance IDs and model colours with known prototypes; simulator base pose',
            spawn_distribution=C.SPAWN, yaw_uniform_radians=[-np.pi,np.pi],
            spawn_acceptance='Reject overlapping, wrong-support or grasp-validator-unreachable candidates',
            initial_positions={n:system.cl.pos(n).tolist() for n in system.cl.names},
            spawn_unstable=system.spawn_unstable,
            source_sha256={os.path.basename(p):hashlib.sha256(Path(p).read_bytes()).hexdigest()
                for p in [system.model_path]+[os.path.join(C.ROOT,'src',f) for f in os.listdir(os.path.join(C.ROOT,'src')) if f.endswith('.py')]})
        metadata['model_sha256']={f:hashlib.sha256(Path(C.ROOT,'models',f).read_bytes()).hexdigest()
                                   for f in os.listdir(os.path.join(C.ROOT,'models')) if f.endswith('.xml')}
        if Path(system.model_path).name == 'hospital_nova3d.xml':
            path=Path(C.ROOT,'models/nova3d_integration_manifest.json')
            metadata['visual_asset_manifest_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        self._manifest_path=os.path.join(self.dir,f'manifest_{self.tag}.json')
        self._metadata=metadata
        with open(self._manifest_path,'w') as f: json.dump(metadata,f,indent=2)

    def _open_chunk(self):
        if self._physics: self._physics.close()
        path=os.path.join(self.dir,f'{self.tag}_part{len(self.physics_paths)+1:03d}_real_trials.csv')
        self.physics_paths.append(path)
        if len(self.physics_paths)==1: self.physics_path=path
        self._physics=open(path,'w',newline='',buffering=1024*1024)
        self._pw=csv.writer(self._physics); self._pw.writerow(self._physics_columns)

    def physics_sample(self, system):
        """One numeric sample per physics step; retain reference validity and units."""
        rb, d, ctrl = system.rb, system.data, system.ctrl
        if self.physics_rows and self.physics_rows % self.chunk_rows == 0:
            self._pw.writerows(self._physics_buffer); self._physics_buffer.clear()
            self._open_chunk()
        pose = rb.base_pose()
        x,y,yaw = pose
        sp=ctrl.arm.sp
        local=np.array([rb.gc_x, rb.gc_y0-sp['ext']])
        c,s=np.cos(yaw),np.sin(yaw)
        reference=np.array([x+c*local[0]-s*local[1],y+s*local[0]+c*local[1],rb.gc_z0+sp['lift']])
        ee=rb.gc()
        valid=(abs(rb.q('joint_wrist_pitch')-C.TRAVEL_PITCH)<.06
               and abs(rb.q('joint_wrist_yaw'))<.06 and abs(rb.q('joint_wrist_roll'))<.06)
        values=[self.run_id,self.seed,'proposed',f'{d.time-system.run_start:.6f}',ctrl.state,
            ctrl.target.name if ctrl.target else '',int(ctrl.collision_active),int(d.ncon),*pose,rb.lift(),rb.arm_ext(),*ee,*reference,int(valid),
            *(reference-ee),d.qvel[0],d.qvel[1],d.qvel[5],*d.ctrl,*d.actuator_force]
        self._physics_buffer.append([f'{v:.7g}' if isinstance(v,(float,np.floating)) else v for v in values])
        self.effort += d.actuator_force**2 * system.dt
        self.physics_rows += 1
        if len(self._physics_buffer)>=500:
            self._pw.writerows(self._physics_buffer); self._physics_buffer.clear()

    def sample(self, t, pose, state, target, v, w, lift, ext, grip, contacts, collision):
        if t - self._last_ts < 1.0 / C.TELEMETRY_HZ - 1e-9: return
        self._last_ts = t
        self._tsw.writerow([f"{t:.2f}", f"{pose[0]:.3f}", f"{pose[1]:.3f}", f"{pose[2]:.3f}", state, target or "", f"{v:.3f}",
                            f"{w:.3f}", f"{lift:.3f}", f"{ext:.3f}", f"{grip:.4f}", contacts, int(collision)])

    def nav_leg(self, success): self.nav_legs += 1; self.nav_ok += int(bool(success))
    def collision(self): self.collision_events += 1
    def grasp(self, success): self.grasp_attempts += 1; self.grasp_success += int(bool(success))

    def object_event(self, t, **kw):
        row = dict(timestamp=f"{t:.1f}", **kw); self.events.append(row)
        self._evw.writerow([row.get(c, "") for c in EVENT_COLS]); self._ev.flush()

    def summary(self, sim_time, gt_total, gt_detected, class_correct, cleaned, failed, wall=0.0, trial=0, seed=0):
        ev = [e for e in self.events]
        def mean(k):
            values=[float(e[k]) for e in ev if e.get(k, "") != "" and e["result"] == "CLEANED"]
            return round(float(np.mean(values)),1) if values else None
        n_att = max(len(ev), 1)
        return dict(run_id=self.tag,condition='proposed',trial=trial, seed=seed, sim_time_s=round(sim_time, 1), objects_total=gt_total, detected=gt_detected,
                    detection_acc=round(gt_detected / max(gt_total, 1), 3),
                    classification_acc=round(class_correct / max(gt_detected, 1), 3), cleaned=cleaned, failed=failed,
                    grasp_attempts=self.grasp_attempts, carry_drops=self.carry_drops,
                    grasp_success_rate=round(self.grasp_success / max(self.grasp_attempts, 1), 3), nav_legs=self.nav_legs,
                    nav_success_rate=round(self.nav_ok / max(self.nav_legs, 1), 3), collision_events=self.collision_events,
                    collisions_per_object=round(self.collision_events / n_att, 3), avg_pickup_s=mean("pickup_time"),
                    avg_sort_s=mean("sort_time"), total_clean_time_s=round(sim_time, 1), wall_s=round(wall, 1))

    def write_summary(self, s, path=None):
        path = path or os.path.join(self.dir, f"summary_{self.tag}.json")
        with open(path,'w') as f: json.dump(s,f,indent=2,allow_nan=False)
        tp = os.path.join(self.dir, "trials_summary.csv"); new = not os.path.exists(tp)
        with open(tp, "a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(TRIAL_COLS)
            w.writerow([s.get(c, "") for c in TRIAL_COLS])
        return path

    def close(self):
        if self._closed: return
        self._closed=True
        if self._physics:
            self._pw.writerows(self._physics_buffer); self._physics_buffer.clear()
            self._physics.close()
            self._metadata.update(sample_count=self.physics_rows,
                data_files=[os.path.basename(p) for p in self.physics_paths])
            with open(self._manifest_path,'w') as f: json.dump(self._metadata,f,indent=2)
        for f in (self._ts, self._ev): f.flush(); f.close()
