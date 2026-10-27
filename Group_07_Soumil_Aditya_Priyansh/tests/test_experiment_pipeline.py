"""Analytic fixtures only: these arrays are unit tests, never study data."""
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy import stats

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from experiment_core import contained,restricted_time
from analyze_experiment import comparison


class ExperimentPipelineTests(unittest.TestCase):
    def test_incomplete_early_stop_is_not_a_fast_completion(self):
        self.assertEqual(restricted_time('exhausted',100,1800,False),1800)
        self.assertEqual(restricted_time('safe_stop',100,1800,True),1800)
        self.assertEqual(restricted_time('completed',900,1800,True),900)

    def test_common_evaluator_checks_orientation_footprint_and_floor(self):
        z=dict(center=[0,0],ix=.17,iy=.13,floor_z=.61,rim_z=.71)
        self.assertTrue(contained(z,np.array([0,0,.64]),np.array([.115,.042,.03])))
        self.assertFalse(contained(z,np.array([.12,0,.64]),np.array([.115,.042,.03])))
        self.assertFalse(contained(z,np.array([0,0,.60]),np.array([.115,.042,.03])))

    def test_welch_matches_scipy_and_direction_is_explicit(self):
        baseline=[10,11,13,15,14]; proposed=[5,6,8,7,6,9]
        observed=comparison(baseline,proposed)
        expected=stats.ttest_ind(baseline,proposed,equal_var=False)
        self.assertAlmostEqual(observed['t'],expected.statistic)
        self.assertAlmostEqual(observed['p'],expected.pvalue)
        ci=expected.confidence_interval()
        np.testing.assert_allclose(observed['ci95'],[ci.low,ci.high])
        self.assertGreater(observed['cohen_d'],0)

    def test_zero_variance_or_single_trial_cannot_invent_significance(self):
        self.assertFalse(comparison([1],[2])['available'])
        result=comparison([1,1,1],[2,2,2])
        self.assertFalse(result['available'])
        self.assertIsNone(result['cohen_d'])


if __name__=='__main__': unittest.main(verbosity=2)
