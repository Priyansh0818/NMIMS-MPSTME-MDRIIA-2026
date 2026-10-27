"""Compare the imported presentation against the existing task, including autonomy.

The 60 second paired rollout is an integration regression, not a performance
study or evidence of a successful full-room clean.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys
import time
import unittest
import uuid
import gc

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import config as C
import raycast
from system import System


class NovaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / "docs/test_runs" / ("nova3d_" + uuid.uuid4().hex[:8])
        cls.output.mkdir(parents=True)
        cls.started = time.perf_counter()
        cls.old = System(seed=0, verbose=False, model_path=C.SCENE_MODELS['classic'],
                         out_dir=str(cls.output / "classic"), tag="classic")
        cls.new = System(seed=0, verbose=False, model_path=C.SCENE_MODELS['nova'],
                         out_dir=str(cls.output / "nova"), tag="nova")
        cls.report = dict(seed=0, mujoco=mujoco.__version__, role="development integration regression",
                          checks={}, outputs=str(cls.output.relative_to(ROOT)))

    @classmethod
    def tearDownClass(cls):
        for s in [cls.old, cls.new]: s.tele.close()
        cls.report['wall_s'] = round(time.perf_counter() - cls.started, 3)
        cls.report['passed'] = len(cls.report['checks']) == 4
        cls.report['scene_model_sha256'] = {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                            for name, path in C.SCENE_MODELS.items()}
        (ROOT / "docs/nova3d_integration_verification.json").write_text(json.dumps(cls.report, indent=2))
        cls.old=None; cls.new=None; gc.collect()

    def test_01_original_dynamics_and_contacts_unchanged(self):
        a, b = self.old.model, self.new.model
        self.assertEqual((a.nq, a.nv, a.nu, a.nbody), (b.nq, b.nv, b.nu, b.nbody))
        self.assertEqual(b.opt.timestep, .002)
        for attr in ['body_mass', 'body_inertia', 'body_ipos', 'body_iquat', 'body_pos', 'body_quat',
                     'jnt_pos', 'jnt_axis', 'jnt_range', 'dof_damping', 'dof_frictionloss',
                     'actuator_gainprm', 'actuator_biasprm', 'actuator_gear', 'qpos0']:
            np.testing.assert_array_equal(getattr(a, attr), getattr(b, attr), err_msg=attr)
        physical = np.flatnonzero((a.geom_contype != 0) | (a.geom_conaffinity != 0))
        for i in physical:
            # Robot collision geoms can be unnamed. Match their unchanged body
            # and local index, since extra world visuals shift global geom IDs.
            body = int(a.geom_bodyid[i])
            if a.geom(i).name:
                j = b.geom(a.geom(i).name).id
            else:
                j = int(b.body_geomadr[body] + i - a.body_geomadr[body])
            for attr in ['geom_type', 'geom_group', 'geom_contype', 'geom_conaffinity', 'geom_size',
                         'geom_pos', 'geom_quat', 'geom_friction', 'geom_solref', 'geom_solimp']:
                np.testing.assert_array_equal(getattr(a, attr)[i], getattr(b, attr)[j], err_msg=attr)
        self.report['checks']['physics_and_contacts'] = dict(passed=True, physical_geoms=len(physical),
                                                            nq=b.nq, nv=b.nv, actuators=b.nu, physics_hz=500)

    def test_02_visual_isolation_and_source_selection(self):
        s = self.new
        mask = np.array([s.model.geom(i).name.startswith('nova_') for i in range(s.model.ngeom)])
        self.assertEqual(int(mask.sum()), 310)  # 308 imported parts + stage and plinth
        self.assertTrue(np.all(s.model.geom_group[mask] == 5))
        self.assertFalse(s.model.geom_contype[mask].any())
        self.assertFalse(s.model.geom_conaffinity[mask].any())
        self.assertFalse(s.rb.geom_env[mask].any())
        self.assertEqual(raycast.GROUP0[5], 0)
        info = json.loads((ROOT / 'models/nova3d_integration_manifest.json').read_text())
        self.assertEqual(info['visual_parts'], 308)
        self.assertEqual(info['triangles'], 98854)
        self.assertFalse(any(p['assembly'] == 'headwall' for p in info['parts']))
        for assembly, top in [('hospital_bed', .734), ('bedside_table', .734),
                              ('coffee_table', .391), ('medical_cart', .731), ('visitor_chair', .449)]:
            skins = [p for p in info['parts'] if p['assembly'] == assembly and
                     any(t in p['part'] for t in ['visual_cover', 'visual_skin'])]
            self.assertTrue(skins)
            self.assertAlmostEqual(max(p['bounds_m'][1][2] for p in skins), top, places=8)
        for name, expected in info['asset_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / 'models' / name).read_bytes()).hexdigest(), expected)
        self.report['checks']['visual_isolation_and_source'] = dict(passed=True, imported_parts=308,
                                                                  imported_triangles=98854, geom_group=5)

    def test_03_initial_scene_sensors_and_navigation_identical(self):
        a, b = self.old, self.new
        np.testing.assert_array_equal(a.data.qpos, b.data.qpos)
        np.testing.assert_array_equal(a.data.qvel, b.data.qvel)
        np.testing.assert_array_equal(a.nav.grid.static, b.nav.grid.static)
        for name in a.cl.names:
            np.testing.assert_array_equal(a.cl.pos(name), b.cl.pos(name))
            np.testing.assert_array_equal(a.model.geom_rgba[a.cl.geom[name]], b.model.geom_rgba[b.cl.geom[name]])
        self.assertEqual(a.spawn_unstable, b.spawn_unstable)
        for camera in ['cam_head', 'cam_wrist']:
            x, y = getattr(a.det, camera).capture(), getattr(b.det, camera).capture()
            for key in ['dist', 'pts']:
                np.testing.assert_array_equal(x[key], y[key], err_msg=camera + '.' + key)
            # A mesh import changes global geom IDs. Compare physical identity,
            # not the arbitrary numeric index allocated by the XML compiler.
            def identities(system, ids):
                names = np.array([system.model.geom(i).name or
                    f'{system.model.body(int(system.model.geom_bodyid[i])).name}:{i-int(system.model.body_geomadr[system.model.geom_bodyid[i]])}'
                    for i in range(system.model.ngeom)] + ['MISS'], dtype=object)
                return names[np.where(ids >= 0, ids, len(names)-1)]
            np.testing.assert_array_equal(identities(a, x['gid']), identities(b, y['gid']))
        manifest = json.loads(Path(b.tele._manifest_path).read_text())
        self.assertEqual(manifest['scene_model'], 'hospital_nova3d.xml')
        self.assertIn('visual_asset_manifest_sha256', manifest)
        self.report['checks']['spawn_sensing_and_map'] = dict(passed=True, objects=15,
            matching_rgbd_cameras=2, identical_static_occupancy=True, unstable_spawns=b.spawn_unstable)

    def test_04_paired_autonomous_rollout_and_500hz_logging(self):
        a, b = self.old, self.new
        start = b.data.qpos.copy()
        max_error = 0.0
        for _ in range(120):
            a.step_physics(250); b.step_physics(250)
            max_error = max(max_error, float(np.max(np.abs(a.data.qpos - b.data.qpos))))
            np.testing.assert_array_equal(a.data.qpos, b.data.qpos)
            np.testing.assert_array_equal(a.data.qvel, b.data.qvel)
            np.testing.assert_array_equal(a.data.ctrl, b.data.ctrl)
            self.assertEqual(a.ctrl.state, b.ctrl.state)
        self.assertGreater(np.linalg.norm(b.data.qpos[:2] - start[:2]), .1)
        self.assertEqual(a.tele.events, b.tele.events)
        a.tele.close(); b.tele.close()
        rows = []
        for path in b.tele.physics_paths:
            with open(path, newline='') as f: rows.extend(csv.DictReader(f))
        self.assertEqual(len(rows), 30000)
        times = np.array([float(r['time_s']) for r in rows])
        np.testing.assert_allclose(np.diff(times), .002, atol=1e-10)
        summary = b.ground_truth_summary()
        summary.pop('run_id'); summary.pop('wall_s')
        self.report['checks']['paired_rollout'] = dict(passed=True, duration_s=60, samples=30000,
            max_qpos_difference=max_error, identical_states_and_commands=True,
            identical_object_events=True, telemetry_hz=500, nova_outcome=summary,
            limitation='One seed and a partial run; not a full-task validation or final experiment')


if __name__ == '__main__': unittest.main(verbosity=2)
