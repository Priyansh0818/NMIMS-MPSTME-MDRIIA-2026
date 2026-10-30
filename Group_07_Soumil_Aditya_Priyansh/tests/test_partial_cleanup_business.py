"""Check prospective accounting against audited placements and negative cases."""
import sys,unittest
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analytics'))
import hospital_business as b

class PartialCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p,cls.data=b.load_inputs();cls.m=b.load_measurements('final')
    def result(self,**updates):return b.payload(replace(self.p,**updates),self.data,self.m)['outputs']
    def test_measured_placement_credit_is_not_a_new_success_rate(self):
        r=self.result()
        self.assertAlmostEqual(r['success_probability'],28/50)
        self.assertAlmostEqual(r['fallback_work_fraction'],137/800)
        self.assertAlmostEqual(r['fallback_staff_min'],5.2*137/800)
    def test_independent_accounting_includes_inspection_and_costs(self):
        r=self.result();staff=1+.05*self.m.actual_mean_attempt_min+5.2*137/800+10+.5
        released=15*365*(15.2-staff)/60/693.5
        net=released-(.08+.02*2)
        self.assertAlmostEqual(r['assisted_staff_min'],staff)
        self.assertAlmostEqual(r['cash_payback']['months'],12*.58/net)
        self.assertAlmostEqual(r['NCRI_cash'],net/2)
        self.assertGreater(r['assisted_room_ready_min'],r['manual_room_ready_min'])
    def test_realization_risk_remains_visible(self):
        self.assertFalse(self.result(cash_realization_fraction=0)['cash_payback']['finite'])
        self.assertFalse(self.result(cash_realization_fraction=.75)['cash_payback']['within_life'])
    def test_conservative_result_is_retained(self):
        old=b.payload(self.p,self.data,self.m)['conservative_comparison']
        self.assertAlmostEqual(old['H_reclaimed_staff_hours_day'],.1502511666666666)
        self.assertAlmostEqual(old['NCRI_cash'],-.1)
        self.assertFalse(old['cash_payback']['finite'])
    def test_partial_work_cannot_be_sourced_from_single_pilot(self):
        with self.assertRaisesRegex(ValueError,'audited final'):
            b.deployment_measurements(b.load_measurements('pilot'),self.data)
    def test_inspection_bounds_are_enforced(self):
        data={**self.data,'deployment_scenario':{**self.data['deployment_scenario'],'inspection_staff_min':-1}}
        with self.assertRaises(ValueError):b.deployment_measurements(self.m,data)

if __name__=='__main__':unittest.main()
