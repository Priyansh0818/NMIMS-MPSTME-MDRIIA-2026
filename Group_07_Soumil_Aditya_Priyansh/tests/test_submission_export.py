"""Export guards exercised on actual recorded rows, not invented project results."""
from pathlib import Path
import csv,gzip,importlib.util,json,sys,tempfile,unittest
import mujoco

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('submission_export',ROOT/'tools/export_trial_evidence.py')
exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)

class ExportGuards(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.study=ROOT/'experiments/assessment_final_v1'
  cls.model=mujoco.MjModel.from_xml_path(str(cls.study/'task/models/hospital_assessment.xml'))
  cls.columns=exporter.COLUMNS+['force_'+cls.model.actuator(i).name for i in range(cls.model.nu)]
  result=next((cls.study/'runs/baseline').glob('seed*/result.json'));cls.result=json.loads(result.read_text())
  cls.source=result.parent/cls.result['raw_files'][0]['path']
  if not cls.source.exists():
   # The delivery packet uses the validated selected-column export, not verbose diagnostics.
   exported=ROOT/'analytics/submission_trials'/cls.result['condition']/f"seed{cls.result['seed']}"
   cls.source=sorted(exported.glob('*_real_trials.csv.gz'))[0]
  with gzip.open(cls.source,'rt',newline='',encoding='utf-8') as f:
   reader=csv.DictReader(f);cls.original=[next(reader) for _ in range(100)]

 def test_projection_keeps_original_measured_strings_and_required_channels(self):
  self.assertEqual(len(self.columns),39)
  for name in ['time_s','seed','base_x','base_vx','ref_z','error_z','force_lift','reach_lift_tracking_valid','robot_collision']:
   self.assertIn(name,self.columns)
  for row in self.original:
   projected={n:row[n] for n in self.columns}
   self.assertEqual(projected['time_s'],row['time_s'])
   self.assertEqual(projected['force_lift'],row['force_lift'])

 def test_truncated_preview_cannot_pass_as_complete_trial(self):
  temporary=ROOT.parent/'tmp/export_guard';temporary.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(dir=temporary) as directory:
   folder=Path(directory);p=folder/'preview_real_trials.csv.gz'
   with gzip.open(p,'wt',encoding='utf-8',newline='') as f:
    writer=csv.writer(f);writer.writerow(self.columns);writer.writerows([[r[n] for n in self.columns] for r in self.original])
   entry=dict(run_id=self.result['run_id'],condition=self.result['condition'],seed=self.result['seed'],columns=self.columns,
              files=[dict(path=p.name,sha256=exporter.sha(p))],audited_metrics=dict(samples=self.result['samples']))
   with self.assertRaisesRegex(ValueError,'Rows/cadence mismatch'):
    exporter.validate_trial(folder,entry,self.model,{},None)

if __name__=='__main__':unittest.main(verbosity=2)
