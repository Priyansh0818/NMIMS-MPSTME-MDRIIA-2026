"""Meaningful foundation checks: physics invariants, outcome bookkeeping and real sample cadence."""
from pathlib import Path
import csv
import json
import sys
import uuid
import unittest
import gc
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from system import System
from presentation import CameraDirector


class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/'docs/test_runs'/uuid.uuid4().hex[:8]
        cls.output.mkdir(parents=True)
        cls.system=System(seed=0,verbose=False,out_dir=str(cls.output),tag='foundation')

    @classmethod
    def tearDownClass(cls):
        cls.system.tele.close()
        cls.system=None; gc.collect()

    def test_01_no_visual_obstacles_or_added_dynamics(self):
        s=self.system
        self.assertEqual(s.model.nq,132)
        self.assertEqual(s.model.nv,116)
        self.assertEqual(s.model.nu,10)
        self.assertEqual(s.dt,.002)
        decor=np.array([s.model.geom(i).name.startswith(('design_', 'nova_')) for i in range(s.model.ngeom)])
        self.assertGreater(decor.sum(),40)
        self.assertFalse(s.rb.geom_env[decor].any())
        self.assertFalse(s.model.geom_contype[decor].any())
        self.assertFalse(s.model.geom_conaffinity[decor].any())
        self.assertEqual(s.spawn_unstable,[])
        inertias=json.loads((ROOT/'models/robot_inertia_baseline.json').read_text())
        for name,values in inertias.items():
            bid=s.model.body(name).id
            self.assertAlmostEqual(float(s.model.body_mass[bid]),values['mass'])
            np.testing.assert_allclose(s.model.body_inertia[bid],values['diaginertia'],rtol=1e-12,atol=1e-14)

    def test_02_unfinished_objects_are_pending(self):
        summary=self.system.ground_truth_summary()
        self.assertEqual(summary['cleaned'],0)
        self.assertEqual(summary['failed'],0)
        self.assertEqual(summary['pending'],15)
        self.assertEqual(summary['run_status'],'in_progress')
        json.dumps(summary,allow_nan=False)

    def test_03_actual_physics_cadence_and_commands(self):
        s=self.system; s.tele.chunk_rows=500; s.step_physics(1000)
        self.assertTrue(np.isfinite(s.data.qpos).all())
        self.assertTrue(np.isfinite(s.data.qvel).all())
        self.assertEqual(s.tele.physics_rows,1000)
        s.tele._physics.flush()
        self.assertEqual(len(s.tele.physics_paths),2)
        rows=[]
        for path in s.tele.physics_paths:
            with open(path,newline='') as f: rows.extend(csv.DictReader(f))
        self.assertEqual(len(rows),1000)
        times=np.array([float(r['time_s']) for r in rows])
        np.testing.assert_allclose(np.diff(times),.002,atol=1e-10)
        self.assertEqual(len({r['run_id'] for r in rows}),1)
        self.assertIn('force_gripper',rows[0]); self.assertIn('ref_x',rows[0])
        self.assertGreater(float(s.tele.effort.sum()),0)

    def test_04_floor_is_not_a_bin_and_camera_is_visual_only(self):
        s=self.system
        self.assertFalse(s.sorter.verify_placement('recycling_bin',np.array([.2,1.,.04])))
        self.assertTrue(s.sorter.verify_placement('recycling_bin',np.array([.2,2.,.06])))
        q=s.data.qpos.copy(); v=s.data.qvel.copy()
        director=CameraDirector(); cam=mujoco.MjvCamera()
        for _ in range(5): director.apply(cam,s); director.next()
        np.testing.assert_array_equal(q,s.data.qpos)
        np.testing.assert_array_equal(v,s.data.qvel)


if __name__=='__main__': unittest.main(verbosity=2)
