"""Build reviewable delivery evidence only after the complete frozen raw audit."""
from pathlib import Path
import argparse,csv,hashlib,json,shutil,statistics

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'experiments/assessment_final_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 p=STUDY/'analysis/analysis.json'
 if not p.exists():raise SystemExit('NOT READY: final analysis is absent')
 a=json.loads(p.read_text())
 if not a.get('complete') or not a.get('inferential_ready') or a.get('audit_errors'):
  raise SystemExit('NOT READY: all 100 raw audits must pass')
 groups={c:[r for r in a['runs'] if r['condition']==c] for c in ['baseline','proposed']}
 if any(len(v)!=50 for v in groups.values()):raise ValueError('Expected exactly 50 audited runs per condition')
 bpath=ROOT/'docs/business_final/business_results.json'
 b=json.loads(bpath.read_text())
 if b['measurements']['mode']!='final':raise ValueError('Business results are not final-telemetry mode')
 output=ROOT/'docs/final_evidence';output.mkdir(exist_ok=True)
 fields=['restricted_completion_time_s','reach_lift_rmse_m','collision_events','carry_drops','elapsed_s']
 summary={}
 def describe(values):
  values=[v for v in values if v is not None]
  return dict(mean=statistics.mean(values) if values else None,sd=statistics.stdev(values) if len(values)>1 else None,n=len(values))
 for c,records in groups.items():
  summary[c]={name:describe([r[name] for r in records]) for name in fields}
  summary[c]['lift_effort_N2s']=dict(mean=statistics.mean(r['effort_by_actuator'][2] for r in records),
                                    sd=statistics.stdev(r['effort_by_actuator'][2] for r in records))
  summary[c]['successful_rooms']=sum(r['completion_success'] for r in records)
  summary[c]['correct_objects']=sum(r['correct_placements'] for r in records)
  summary[c]['samples']=sum(r['samples'] for r in records)
 result=dict(complete=True,role='100-run audited simulated evidence; not clinical effectiveness',
             analysis_sha256=sha(p),business_sha256=sha(bpath),conditions=summary,
             primary_comparison=a['primary_comparison'],business=b['outputs'])
 (output/'FINAL_RESULTS.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
 lines=['# Final audited simulation results','','50 independent baseline seeds and 50 independent proposed seeds; the separate pilot is excluded.',
        '', '| Measure | Baseline mean ± SD | Proposed mean ± SD | Unit |','| --- | --- | --- | --- |']
 for name,unit in [('restricted_completion_time_s','s'),('reach_lift_rmse_m','m'),('lift_effort_N2s','N²·s; lift actuator only'),('collision_events','episodes/run'),('carry_drops','drops/run')]:
  values=[f"{summary[c][name]['mean']:.5g} ± {summary[c][name]['sd']:.5g}" if summary[c][name]['mean'] is not None and summary[c][name]['sd'] is not None else 'Not estimable; see valid n' for c in groups]
  lines.append(f'| {name} | {values[0]} | {values[1]} | {unit} |')
 for c,s in summary.items():lines+=['',f"{c}: {s['successful_rooms']}/50 rooms fully cleared; {s['correct_objects']}/800 correct final object placements; {s['samples']:,} raw physics samples."]
 lines+=['','## Primary inference','','```json',json.dumps(a['primary_comparison'],indent=2),'```',
         '', '## Interpretation and scope',
         '', 'Failures remain at the prespecified 1800 s restricted completion time. Infrastructure-interrupted attempts are archived and the identical seeds were restarted; no autonomous task failures were discarded.',
         '', 'Tracking uses valid commanded top-down reach/lift reference samples, not a global six-dimensional planned path. Force/torque-squared integrals are reported per channel; they are not electrical energy. Cups/bottles/slipper/paper and all 16 object outcomes are retained.',
         '', 'The acceptance validator restricts layouts to the frozen geometric feasibility rule. Perception uses simulator ray/instance observations and a known catalogue. No real hospital performance, infection or admission-revenue claim follows.',
         '', '## Business interpretation','', b['measurements']['label'],
         '',f"H={b['outputs']['H_reclaimed_staff_hours_day']:.5g} staff-hours/day; cash NCRI={b['outputs']['NCRI_cash']:.5g}. Cash payback: "+(f"{b['outputs']['cash_payback']['months']:.3g} months" if b['outputs']['cash_payback']['finite'] else 'no finite payback')+'.',
         '', 'Operational and financial inputs remain unvalidated assumptions. Positive released staff capacity is not automatically reduced cash expenditure. Residual cleaning is unchanged.']
 (output/'FINAL_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 # The repository packet is deliberately explicit about the full raw-data size.
 manifest=[]
 for r in a['runs']:
  folder=STUDY/r['folder'];record=json.loads((folder/'result.json').read_text())
  for raw in record['raw_files']:
   manifest.append(dict(condition=r['condition'],seed=r['seed'],relative_path=str((folder/raw['path']).relative_to(ROOT.parent)),
                        bytes=(folder/raw['path']).stat().st_size,sha256=raw['sha256'],audit_passed=True))
 with (output/'RAW_DATA_MANIFEST.csv').open('w',newline='',encoding='utf-8') as f:
  writer=csv.DictWriter(f,fieldnames=list(manifest[0]));writer.writeheader();writer.writerows(manifest)
 for file in ['run_metrics.csv','actuator_effort.csv','object_geometry_results.csv','REPORT.md']:
  shutil.copy2(STUDY/'analysis'/file,output/file)
 for file in (STUDY/'analysis').glob('*.png'):shutil.copy2(file,output/file.name)
 print(json.dumps(dict(ready=True,output=str(output),raw_files=len(manifest),raw_bytes=sum(r['bytes'] for r in manifest))))

if __name__=='__main__':main()
