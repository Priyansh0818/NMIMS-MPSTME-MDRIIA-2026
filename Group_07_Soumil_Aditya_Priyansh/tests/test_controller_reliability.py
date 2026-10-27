"""Regressions against actual simulator failure checkpoints, not reference data."""
from pathlib import Path
import sys
import unittest
import uuid
import gc

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from replay_snapshot import restore
import config as C
from sorting import SortingManager


class ReliabilityTests(unittest.TestCase):
    def tearDown(self):
        self.doCleanups()
        gc.collect()

    def replay(self, name):
        s, record = restore(ROOT / 'tests/fixtures/reliability' / name,
                            ROOT / 'docs/test_runs' / ('reliability_' + uuid.uuid4().hex[:8]))
        self.addCleanup(s.tele.close)
        return s

    def test_clutter_exclusion_honours_real_overlapping_contact(self):
        s = self.replay('paper_carry')
        posture = dict(lift=s.rb.lift(), ext=s.rb.arm_ext(), gripper=s.rb.gripper(),
                       wrist_pitch=C.TRAVEL_PITCH, wrist_yaw=0, wrist_roll=0)
        included = s.rb.collisions(s.rb.base_pose(), posture, margin=0, include_clutter=True)
        excluded = s.rb.collisions(s.rb.base_pose(), posture, margin=0, include_clutter=False)
        self.assertIn('clutter_paper_2', included)
        self.assertFalse(any(n.startswith('clutter_') for n in excluded))

    def test_original_bin_failures_have_safe_reachable_alternatives(self):
        for fixture in ['glove_drop', 'bottle_drop']:
            with self.subTest(fixture=fixture):
                s = self.replay(fixture); tr = s.ctrl.target
                zone = s.sorter.zone_for(tr.category)
                hold = s.ctrl.measure_hold_offset(); offset = s.sorter.next_offset(zone)
                q = s.data.qpos.copy()
                drop = s.sorter.plan_drop(zone, tr.height, hold, offset)
                self.assertIsNotNone(drop, s.sorter.last_reason)
                self.assertGreaterEqual(s.sorter.last_offset_attempts, 1)
                np.testing.assert_array_equal(q, s.data.qpos)
                post = dict(lift=drop.lift_drop, ext=drop.ext, gripper=C.GRIPPER_OPEN,
                            wrist_pitch=C.TRAVEL_PITCH, wrist_yaw=0, wrist_roll=0)
                self.assertEqual(s.rb.collisions(drop.pose, post, margin=.02, include_clutter=False), {})

    def test_bed_estimate_permits_observation_without_authorising_collision(self):
        s = self.replay('towel_observation'); tr = s.world.tracks['towel_2']
        before = s.data.qpos.copy()
        exact, stats = s.grasp.candidates(tr, 'clutter_towel_2', s.cl.body['towel_2'])
        observation, stats = s.grasp.candidates(tr, 'clutter_towel_2', s.cl.body['towel_2'], allow_refinement=True)
        self.assertEqual(exact, [])
        self.assertGreater(len(observation), 0)
        self.assertTrue(all(c.refine_only for c in observation))
        np.testing.assert_array_equal(before, s.data.qpos)

    def test_payload_base_contact_is_counted_and_failed_items_remain_obstacles(self):
        s = self.replay('paper_carry')
        s.ctrl.t = 10; s.ctrl.monitor_collisions()
        self.assertTrue(s.ctrl.collision_active)
        self.assertEqual(s.tele.collision_events, 1)
        tr = s.ctrl.target; tr.status = 'FAILED'
        self.assertIn(tuple(tr.xy), s.ctrl.clutter_obstacles())

    def test_collision_is_detected_before_the_next_controller_update(self):
        s = self.replay('paper_carry'); before=s.ctrl.t
        s.step_physics(1)
        self.assertEqual(s.ctrl.t, before)
        self.assertEqual(s.tele.physics_rows, 1)
        self.assertTrue(s.ctrl.collision_active)
        self.assertEqual(s.tele.collision_events, 1)

    def test_failed_delivery_stops_without_releasing_payload(self):
        s = self.replay('paper_carry')
        goal=s.ctrl.arm.goal['gripper']
        s.ctrl.drop_fail('TEST_NO_SAFE_ROUTE')
        self.assertEqual(s.ctrl.state,'SAFE_STOP')
        self.assertEqual(s.ctrl.arm.goal['gripper'],goal)
        self.assertTrue(s.done)
        self.assertEqual(s.ground_truth_summary()['run_status'],'safe_stop')

    def test_paper_release_inside_bin_survives_arm_withdrawal(self):
        s = self.replay('paper_release'); started = s.ctrl.t
        while s.ctrl.t-started < 60 and s.ctrl.state not in ['SELECT', 'RECOVER', 'DONE']:
            s.step_physics(10)
        self.assertEqual(s.ctrl.state, 'SELECT')
        self.assertEqual(s.tele.events[-1]['result'], 'CLEANED')
        half = s.cl.world_half_extents('paper_2')
        self.assertTrue(s.sorter.verify_placement('recycling_bin', s.cl.pos('paper_2'), half[2], half[:2]))
        self.assertEqual(s.tele.collision_events, 0)

    def test_small_plastic_release_survives_arm_withdrawal(self):
        s = self.replay('plastic_release'); started = s.ctrl.t
        while s.ctrl.t-started < 60 and s.ctrl.state not in ['SELECT', 'RECOVER', 'DONE']:
            s.step_physics(10)
        self.assertEqual(s.ctrl.state, 'SELECT')
        self.assertEqual(s.tele.events[-1]['result'], 'CLEANED')
        half = s.cl.world_half_extents('plasticpack_1')
        self.assertTrue(s.sorter.verify_placement('trash_bin', s.cl.pos('plasticpack_1'), half[2], half[:2]))
        self.assertEqual(s.tele.collision_events, 0)

    def test_lower_pressure_carry_handles_recorded_rotation_failure(self):
        s=self.replay('paper_transport')
        hold=s.rb.gripper()-C.HOLD_SQUEEZE
        s.ctrl.arm.sp['gripper']=s.ctrl.arm.goal['gripper']=hold
        s.data.ctrl[s.rb.act['gripper']]=hold
        s.ctrl.state='STOW'; s.ctrl.sub=1; s.ctrl.t_state=0
        started=s.ctrl.t
        while s.ctrl.t-started<90 and s.ctrl.state not in ['SELECT','RECOVER','SAFE_STOP','DONE']:
            s.step_physics(10)
        self.assertEqual(s.ctrl.state,'SELECT')
        self.assertEqual(s.tele.carry_drops,0)
        self.assertEqual(s.tele.events[-1]['result'],'CLEANED')
        self.assertEqual(s.tele.collision_events,0)

    def test_occupied_shallow_tray_remains_deliverable(self):
        s=self.replay('return_tray')
        hold=s.rb.gripper()-C.HOLD_SQUEEZE
        s.ctrl.arm.sp['gripper']=s.ctrl.arm.goal['gripper']=hold
        s.data.ctrl[s.rb.act['gripper']]=hold
        started=s.ctrl.t
        while s.ctrl.t-started<90 and s.ctrl.state not in ['SELECT','RECOVER','SAFE_STOP','DONE']:
            s.step_physics(10)
        self.assertEqual(s.ctrl.state,'SELECT')
        self.assertEqual(s.tele.events[-1]['result'],'CLEANED')
        self.assertEqual(s.tele.collision_events,0)

    def test_misplaced_light_item_is_reported_and_retained_for_recovery(self):
        s=self.replay('plastic_variation'); started=s.ctrl.t
        while s.ctrl.t-started<90 and s.ctrl.state not in ['SELECT','RECOVER','SAFE_STOP','DONE']:
            s.step_physics(10)
        self.assertEqual(s.ctrl.state,'SELECT')
        self.assertEqual(s.tele.events[-1]['result'],'MISPLACED')
        tr=s.world.tracks['plasticpack_1']
        self.assertEqual(tr.status,'FAILED')
        self.assertNotIn(tr.name,s.ctrl.cleaned)
        self.assertIn(tr.name,s.ctrl.failed)
        self.assertIn(tuple(tr.xy),s.ctrl.clutter_obstacles())
        self.assertEqual(s.tele.collision_events,0)

    def test_point_inside_is_insufficient_for_physical_containment(self):
        sorter = SortingManager.__new__(SortingManager)
        sorter.zone = {'bin':dict(center=(0,0), ix=.15, iy=.15, floor_z=.02, rim_z=.4)}
        self.assertTrue(sorter.verify_placement('bin', (.0,.0,.06), .04, (.04,.04)))
        # A centre-only test would accept an overhanging box or an object that
        # is below the floor. Neither is a verified physical placement.
        self.assertFalse(sorter.verify_placement('bin', (.14,0,.06), .04, (.04,.04)))
        self.assertFalse(sorter.verify_placement('bin', (0,0,.03), .04, (.04,.04)))
        self.assertFalse(sorter.verify_placement('bin', (0,0,.44), .04, (.04,.04)))


if __name__ == '__main__': unittest.main(verbosity=2)
