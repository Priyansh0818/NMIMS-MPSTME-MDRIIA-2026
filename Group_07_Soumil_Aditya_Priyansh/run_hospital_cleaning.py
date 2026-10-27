#!/usr/bin/env python
"""Autonomous Mobile Manipulator for Hospital Housekeeping -- ONE command launcher.

    python run_hospital_cleaning.py                  # live MuJoCo window, clean presentation
    python run_hospital_cleaning.py --debug          # + footprint / path / target / HUD overlay
    python run_hospital_cleaning.py --benchmark      # live window + per-stage timing (find your lag source)
    python run_hospital_cleaning.py --headless       # no window, as fast as possible
    python run_hospital_cleaning.py --trials 50      # headless batch -> analytics/trials_summary.csv

Viewer keys:  SPACE pause/resume   D toggle debug overlay   1/2/3 speed 0.5x/1x/2x   ESC quit
"""
import argparse, math, os, sys, time
if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

import numpy as np
import gc
import mujoco
import config as C
import system as SYS
from presentation import CameraDirector, status_text


def parse():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seed", type=int, default=0, help="scene randomisation seed (default 0)")
    p.add_argument("--random", action="store_true", help="use a time-based random seed")
    p.add_argument("--headless", action="store_true", help="run without a window")
    p.add_argument("--trials", type=int, default=0, help="headless batch of N trials (seeds seed..seed+N-1)")
    p.add_argument("--debug", action="store_true", help="show debug overlay")
    p.add_argument("--benchmark", action="store_true", help="print per-stage timing every 5 s")
    p.add_argument("--speed", type=float, default=1.0, help="simulation speed multiplier (physics unchanged)")
    p.add_argument("--no-shadows", action="store_true", help="disable shadows (cheaper rendering)")
    p.add_argument("--max-time", type=float, default=2400.0, help="simulated seconds before giving up")
    p.add_argument("--quiet", action="store_true", help="suppress controller log lines")
    p.add_argument("--keep-open", action="store_true", help="keep the window open after the room is clean")
    p.add_argument("--cinematic", action="store_true", help="gentle camera motion; C switches viewpoints")
    p.add_argument("--output-dir", default=None, help="directory for this run's measurement files")
    p.add_argument("--scene", choices=tuple(C.SCENE_MODELS), default="nova", help="Nova3D hospital (default) or the previous classic appearance; same physics")
    return p.parse_args()


# ----------------------------------------------------------------------------------------------- headless / batch
def run_headless(seed, args, trial=0, tag=None):
    t0 = time.perf_counter()
    S = SYS.System(seed=seed, verbose=not args.quiet, tag=tag, out_dir=args.output_dir)
    try:
        while S.data.time - S.run_start < args.max_time and not S.done:
            S.step_physics(min(250, max(1, int(round((args.max_time-(S.data.time-S.run_start))/S.dt)))))
        s = S.ground_truth_summary(time.perf_counter() - t0, trial=trial)
        if s['run_status']=='in_progress': s['run_status']='timed_out'
        S.tele.write_summary(s)
    except BaseException as error:
        s=S.ground_truth_summary(time.perf_counter()-t0,trial=trial)
        s.update(run_status='interrupted' if isinstance(error,KeyboardInterrupt) else 'error',error=repr(error))
        S.tele.write_summary(s)
        raise
    finally: S.tele.close()
    return S, s


def run_batch(args):
    rows = []
    for i in range(args.trials):
        seed = args.seed + i
        trial_system, s = run_headless(seed, args, trial=i, tag=f"trial{i:03d}_seed{seed}")
        rows.append(s)
        print(f"[trial {i + 1}/{args.trials}] seed {seed}: cleaned {s['cleaned']}/{s['objects_total']}, "
              f"time {s['sim_time_s']:.0f}s, collisions {s['collision_events']}, grasp {s['grasp_success_rate']:.2f}", flush=True)
        del trial_system
        gc.collect()
    ok = sum(r["cleaned"] for r in rows); tot = sum(r["objects_total"] for r in rows)
    print(f"\nBATCH DONE: {ok}/{tot} objects cleaned over {len(rows)} trials -> {os.path.join(C.ANALYTICS_DIR, 'trials_summary.csv')}")


# ----------------------------------------------------------------------------------------------- viewer helpers
def _sphere(scn, pos, r, rgba):
    if scn.ngeom >= scn.maxgeom: return
    mujoco.mjv_initGeom(scn.geoms[scn.ngeom], mujoco.mjtGeom.mjGEOM_SPHERE, np.array([r, 0, 0]), np.asarray(pos, float),
                        np.eye(3).flatten(), np.asarray(rgba, np.float32)); scn.ngeom += 1


def _line(scn, p0, p1, w, rgba):
    if scn.ngeom >= scn.maxgeom: return
    g = scn.geoms[scn.ngeom]
    mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_CAPSULE, np.zeros(3), np.zeros(3), np.zeros(9), np.asarray(rgba, np.float32))
    mujoco.mjv_connector(g, mujoco.mjtGeom.mjGEOM_CAPSULE, w, np.asarray(p0, float), np.asarray(p1, float)); scn.ngeom += 1


def draw_debug(S, scn):
    """Footprint, planned path, target object, destination, grasp target, lidar hits -- drawn inside the MuJoCo window."""
    scn.ngeom = 0
    rb, nav, ctrl = S.rb, S.nav, S.ctrl
    x, y, yaw = rb.base_pose(); R = np.array([[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]])
    hull = nav.safety.hull_pts @ R.T + [x, y]
    col = (1, 0.1, 0.1, 1) if ctrl.collision_active else (1.0, 0.85, 0.1, 1)
    for a, b in zip(hull, np.roll(hull, -1, axis=0)): _line(scn, (*a, 0.02), (*b, 0.02), 0.006, col)
    pts = nav.path_xy
    for a, b in zip(pts[:-1], pts[1:]): _line(scn, (*a, 0.03), (*b, 0.03), 0.008, (0.1, 0.9, 0.2, 1))
    tr = ctrl.target
    if tr is not None:
        _sphere(scn, (*tr.xy, tr.top + 0.05), 0.02, (1, 0.1, 0.1, 1))
        z = S.sorter.zone[S.sorter.zone_for(tr.category)]
        _sphere(scn, (*z["center"], z["rim_z"] + 0.25), 0.03, (0.2, 0.4, 1, 1))
        if ctrl.state in ("DESCEND", "REFINE", "PREGRASP", "CLOSE"):
            _sphere(scn, (*tr.xy, max(C.GRASP_MIN_Z, tr.top - C.GRASP_DEPTH)), 0.015, (1, 0, 1, 1))
    for hx, hy in nav.safety.last_hits[:12]:
        w = R @ np.array([hx, hy]) + [x, y]; _sphere(scn, (*w, 0.05), 0.012, (1, 0, 0, 1))
    for t in S.world.pending(): _sphere(scn, (*t.xy, t.top + 0.1), 0.012, (0.9, 0.9, 0.2, 1))


def hud_text(S, fps, rtf):
    return "\n".join(S.ctrl.hud_lines() + [f"sim t {S.data.time:6.1f}s   RTF {rtf:4.1f}x   viewer {fps:4.0f} fps"])


def set_hud(v, text):
    if hasattr(v, "set_texts"):
        v.set_texts((mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_TOPLEFT, text, ""))


def run_viewer(args):
    import mujoco.viewer
    S = SYS.System(seed=(int(time.time()) % 100000) if args.random else args.seed, verbose=not args.quiet, out_dir=args.output_dir)
    m, d = S.model, S.data
    if args.no_shadows: m.light_castshadow[:] = 0
    state = dict(paused=False, debug=args.debug, speed=args.speed)
    director=CameraDirector(); director.orbit=args.cinematic

    def on_key(k):
        if k == 32: state["paused"] = not state["paused"]
        elif k in (68, 100): state["debug"] = not state["debug"]
        elif k == 49: state["speed"] = 0.5
        elif k == 50: state["speed"] = 1.0
        elif k == 51: state["speed"] = 2.0
        elif k in (67,99): director.next(); state['camera_changed']=True
        elif k in (79,111): director.orbit=not director.orbit

    dt = m.opt.timestep; max_steps = int(C.MAX_CATCHUP_S / dt)
    st = dict(phys=0.0, ctrl=0.0, sync=0.0, steps=0, ctrl_calls=0, syncs=0)
    if args.benchmark:
        orig = S.ctrl.step
        def timed(dt_):
            t = time.perf_counter(); orig(dt_); st["ctrl"] += time.perf_counter() - t; st["ctrl_calls"] += 1
        S.ctrl.step = timed

    with mujoco.viewer.launch_passive(m, d, key_callback=on_key, show_left_ui=False, show_right_ui=False) as v:
        director.apply(v.cam,S)
        v.opt.geomgroup[1]=1; v.opt.geomgroup[3]=0; v.opt.geomgroup[5]=1
        t_start = time.perf_counter(); wall0 = t_start; sim0 = d.time
        last_sync = last_dbg = last_bench = t_start; fps_t = rtf_w = t_start; fps_n = 0; fps = 0.0; rtf = 1.0; rtf_s = d.time
        done_at = None; hud_on = False; last_speed=state['speed']; summary_written=False
        while v.is_running():
            now = time.perf_counter()
            if state['speed'] != last_speed:
                wall0=now-(d.time-sim0)/state['speed']; last_speed=state['speed']
            if state["paused"]:
                wall0 = now - (d.time - sim0) / state["speed"]; time.sleep(0.02); v.sync(); continue
            due = int(((now - wall0) * state["speed"] - (d.time - sim0)) / dt)
            if due > max_steps:                              # cannot keep up: run slower than real time rather than spiral
                due = max_steps; wall0 = now - (d.time - sim0) / state["speed"]
            if due > 0 and not S.done:
                t = time.perf_counter(); S.step_physics(due); st["phys"] += time.perf_counter() - t; st["steps"] += due
            if S.done and done_at is None:
                done_at = now; print_summary(S, now - t_start); summary_written=True
            if now - last_sync >= 1.0 / C.RENDER_FPS:
                last_sync = now
                if state.get('camera_changed') or director.orbit or director.index==1:
                    state['camera_changed'] = not director.apply(v.cam,S,smooth=True)
                if state["debug"]:
                    if now - last_dbg >= 1.0 / C.DEBUG_DRAW_HZ:
                        last_dbg = now
                        try:
                            with v.lock(): draw_debug(S, v.user_scn)
                            hud_on = True
                        except Exception as e:               # never let a debug overlay kill the demo
                            state["debug"] = False; print(f"[debug overlay disabled: {e}]")
                elif hud_on:
                    with v.lock(): v.user_scn.ngeom = 0
                    hud_on = False
                set_hud(v,status_text(S,director,fps,rtf))
                t = time.perf_counter(); v.sync(); st["sync"] += time.perf_counter() - t; st["syncs"] += 1; fps_n += 1
                if now - fps_t >= 1.0: fps = fps_n / (now - fps_t); fps_n = 0; fps_t = now
                if now - rtf_w >= 1.0: rtf = (d.time - rtf_s) / (now - rtf_w); rtf_w = now; rtf_s = d.time
            else:
                time.sleep(0.0005)
            if args.benchmark and now - last_bench >= 5.0:
                print_bench(st, now - last_bench, rtf, fps); last_bench = now
                st.update(phys=0.0, ctrl=0.0, sync=0.0, steps=0, ctrl_calls=0, syncs=0)
            if d.time-S.run_start > args.max_time: break
            if done_at is not None and not args.keep_open and now - done_at > 5.0: break
    if not summary_written:
        s=S.ground_truth_summary(time.perf_counter()-t_start)
        s['run_status']='timed_out' if d.time-S.run_start >= args.max_time else 'interrupted'
        S.tele.write_summary(s)
    S.tele.close()


def print_bench(s, span, rtf, fps):
    ph = max(s["phys"] - s["ctrl"], 0.0)
    print(f"[bench] RTF {rtf:4.2f}x | viewer {fps:3.0f} fps | physics {ph / max(s['steps'], 1) * 1e6:5.0f} us/step | "
          f"controller {s['ctrl'] / max(s['ctrl_calls'], 1) * 1e3:5.2f} ms/call | viewer.sync {s['sync'] / max(s['syncs'], 1) * 1e3:5.2f} ms/call | "
          f"CPU share: physics {ph / span * 100:3.0f}% ctrl {s['ctrl'] / span * 100:3.0f}% sync {s['sync'] / span * 100:3.0f}%", flush=True)


def print_summary(S, wall):
    s = S.ground_truth_summary(wall); S.tele.write_summary(s); print_summary_dict(s)
    print(f"  logs in {C.ANALYTICS_DIR}")


def print_summary_dict(s):
    print("\n=========== ROOM CLEANING SUMMARY ===========")
    for k, v in s.items(): print(f"  {k:22s} {v}")
    print("=============================================", flush=True)


def main():
    args = parse()
    C.MODEL_PATH = C.SCENE_MODELS[args.scene]
    if args.trials > 0: run_batch(args); return
    if args.headless:
        _, s = run_headless((int(time.time()) % 100000) if args.random else args.seed, args)
        print_summary_dict(s); return
    run_viewer(args)


if __name__ == "__main__":
    main()
