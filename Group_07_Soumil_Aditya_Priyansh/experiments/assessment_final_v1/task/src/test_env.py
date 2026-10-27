# Sprint 0 Toolchain and MuJoCo Simulation Environment Verification
# Group: MDRIIA Group 07
# Domain: Hospital Clutter Manipulation & Room Turnaround

import sys
import os

def run_environment_verification():
    print("=" * 65)
    print("MDRIIA GROUP 07 - TOOLCHAIN AND PHYSICS VERIFICATION")
    print("=" * 65)
    print(f"[OK] Python Version: {sys.version.split()[0]}")

    # 1. Verify Scientific Stack
    for pkg in ["numpy", "scipy", "matplotlib"]:
        try:
            mod = __import__(pkg)
            print(f"[OK] {pkg.capitalize()} Version: {mod.__version__}")
        except ImportError:
            print(f"[ERROR] Required library missing: {pkg}. Run: pip install {pkg}")

    # 2. Verify MuJoCo Physics Engine
    try:
        import mujoco
        print(f"[OK] MuJoCo Version: {mujoco.__version__}")

        model_path = os.path.join(os.path.dirname(__file__), "..", "models", "hospital_clutter_manipulator.xml")
        if os.path.exists(model_path):
            m = mujoco.MjModel.from_xml_path(model_path)
            d = mujoco.MjData(m)

            # Load keyframe and settle
            try:
                key_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, "ready")
                if key_id >= 0:
                    mujoco.mj_resetDataKeyframe(m, d, key_id)
            except Exception:
                pass

            # Run 500 steps to check stability
            for _ in range(500):
                mujoco.mj_step(m, d)

            # Check for NaN/Inf instability
            has_nan = any(
                val != val or abs(val) > 1e10
                for val in d.qvel[:10]
            )

            print(f"[{'ERROR' if has_nan else 'SUCCESS'}] "
                  f"Compiled MJCF model: {os.path.basename(model_path)}")
            print(f"[INFO] System DoF: {m.nv}, Actuators: {m.nu}, "
                  f"Geoms: {m.ngeom}, Bodies: {m.nbody}")
            print(f"[INFO] Integrator: {['Euler','RK4','implicit','implicitfast'][m.opt.integrator]}")

            # Report object positions
            clutter_objects = [
                "clutter_cup", "clutter_bottle", "clutter_box",
                "clutter_towel", "clutter_lid", "clutter_wrapper"
            ]
            found = 0
            for name in clutter_objects:
                bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, name)
                if bid >= 0:
                    pos = d.xpos[bid]
                    print(f"[INFO]   {name:22s} at ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
                    found += 1
            print(f"[INFO] Clutter objects detected: {found}/{len(clutter_objects)}")

            if has_nan:
                print("[ERROR] Simulation unstable — NaN detected in qvel")
                sys.exit(1)
            else:
                print("[SUCCESS] Simulation stable after 500 steps")

        else:
            print(f"[WARNING] Model file not found at {model_path}")
    except ImportError:
        print("[ERROR] MuJoCo library not installed. Run: pip install mujoco")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] MuJoCo model compilation error: {e}")
        sys.exit(1)

    print("=" * 65)
    print("Sprint 0 toolchain check complete.")

if __name__ == "__main__":
    run_environment_verification()
