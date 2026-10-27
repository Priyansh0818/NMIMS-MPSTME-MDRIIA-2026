"""The requested fourth assessment object is physical, sensed and returnable."""
from pathlib import Path
import gc
import sys
import unittest
import uuid
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from system import System
import config as C


class AssessmentTests(unittest.TestCase):
    def test_slipper_pick_carry_and_return_survives_withdrawal(self):
        for seed in [9010, 9011, 9012]:
            with self.subTest(seed=seed):
                output = ROOT / 'docs/test_runs' / ('slipper_' + uuid.uuid4().hex[:8])
                s = System(seed=seed, verbose=False, model_path=C.SCENE_MODELS['assessment'],
                           out_dir=str(output), only=['slipper_1'])
                try:
                    self.assertEqual(len(s.cl.names), 16)
                    self.assertEqual(s.spawn_unstable, [])
                    geom = s.cl.geom['slipper_1']
                    self.assertGreater(s.model.geom_contype[geom], 0)
                    self.assertAlmostEqual(float(s.model.body_mass[s.cl.body['slipper_1']]), .12)
                    np.testing.assert_allclose(s.model.geom_size[geom], [.115,.042,.03])
                    while s.ctrl.t < 220:
                        s.step_physics(10)
                        if s.tele.events and s.ctrl.state == 'SELECT': break
                    self.assertTrue(s.tele.events)
                    self.assertEqual(s.tele.events[-1]['result'], 'CLEANED')
                    half = s.cl.world_half_extents('slipper_1')
                    self.assertTrue(s.sorter.verify_placement('return_tray', s.cl.pos('slipper_1'),
                                                            half[2], half[:2]))
                    self.assertEqual(s.tele.carry_drops, 0)
                    self.assertEqual(s.tele.collision_events, 0)
                finally:
                    s.tele.close()
                    del s
                    gc.collect()


if __name__ == '__main__': unittest.main(verbosity=2)
