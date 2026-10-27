"""Business formulas and provenance gates. Analytic fixtures are not project results."""
from dataclasses import replace
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analytics'))
from hospital_business import (load_inputs,load_measurements,calculate,queue_mmc,payback,validate)


class BusinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p,cls.data=load_inputs(); cls.m=load_measurements('pilot')

    def result(self,**changes):
        p=replace(self.p,**changes); validate(p,self.data)
        return calculate(p,self.data['normalization_reference'],self.m)

    def test_reallocated_time_is_not_automatic_payroll_saving(self):
        r=self.result(monitoring_fraction=0,pilot_success_probability=1,handling_staff_min=0,
                      cash_realization_fraction=0,maintenance_ratio_per_cell_year=0,energy_ratio_reference_year=0)
        self.assertGreater(r['H_reclaimed_staff_hours_day'],0)
        self.assertAlmostEqual(r['cash_saving_reference_units_year'],0)
        self.assertFalse(r['cash_payback']['finite'])
        self.assertGreater(r['assisted_room_ready_min'],r['manual_room_ready_min'])

    def test_full_attendance_can_consume_more_staff_time(self):
        r=self.result(monitoring_fraction=1)
        self.assertLess(r['H_reclaimed_staff_hours_day'],0)
        self.assertGreater(r['kappa_cash'],1)

    def test_payback_matches_direct_calculation(self):
        r=self.result(monitoring_fraction=0,pilot_success_probability=1,handling_staff_min=0,
                      cash_realization_fraction=1,maintenance_ratio_per_cell_year=0,energy_ratio_reference_year=0,
                      capex_ratio_per_cell=.5)
        saving=5.2/15.2
        self.assertAlmostEqual(r['cash_saving_reference_units_year'],saving)
        self.assertAlmostEqual(r['cash_payback']['months'],12*.5/saving)
        self.assertAlmostEqual(r['cash_payback']['P_payback'],.5/(saving*self.p.life_years))

    def test_fixed_reference_does_not_move_with_scenario_volume(self):
        a=self.result(); b=self.result(daily_rooms=2*self.p.daily_rooms)
        self.assertAlmostEqual(a['reference_annual_staff_hours'],b['reference_annual_staff_hours'])
        self.assertAlmostEqual(b['capital_reference_units'],a['capital_reference_units'])
        self.assertAlmostEqual(b['fixed_maintenance_reference_units'],a['fixed_maintenance_reference_units'])
        self.assertAlmostEqual(b['variable_energy_reference_units'],2*a['variable_energy_reference_units'])

    def test_realization_break_even_reproduces_zero_cash_saving(self):
        r=self.result()
        boundary=r['break_even']['cash_realization_for_positive_savings']
        self.assertIsNotNone(boundary)
        self.assertAlmostEqual(self.result(cash_realization_fraction=boundary)['cash_saving_reference_units_year'],0)

    def test_nonpositive_savings_do_not_create_negative_payback(self):
        for saving in [0,-.1]:
            result=payback(.5,saving,5)
            self.assertFalse(result['finite']); self.assertIsNone(result['P_payback'])
        self.assertEqual(payback(0,.1,5)['months'],0)

    def test_mmc_known_values_zero_arrivals_and_overload(self):
        self.assertAlmostEqual(queue_mmc(2,15,1)['wait_minutes'],15)
        self.assertAlmostEqual(queue_mmc(2,15,2)['wait_minutes'],1)
        self.assertEqual(queue_mmc(0,15,1)['wait_minutes'],0)
        self.assertFalse(queue_mmc(4,15,1)['stable'])
        self.assertIsNone(queue_mmc(4,15,1)['wait_minutes'])

    def test_unfinished_trials_cannot_be_used_as_final_business_data(self):
        temporary_root=ROOT/'docs'/'test_runs'
        temporary_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            target=Path(directory)/'analysis'; target.mkdir()
            (target/'analysis.json').write_text(json.dumps(dict(inferential_ready=False,complete=False)))
            with self.assertRaisesRegex(ValueError,'not complete'):
                load_measurements('final',directory)

    def test_invalid_assumptions_are_rejected(self):
        for changes in [dict(monitoring_fraction=1.1),dict(life_years=0),dict(daily_rooms=-1),dict(parallel_cells=1.5)]:
            with self.assertRaises(ValueError): validate(replace(self.p,**changes),self.data)


if __name__=='__main__': unittest.main(verbosity=2)
