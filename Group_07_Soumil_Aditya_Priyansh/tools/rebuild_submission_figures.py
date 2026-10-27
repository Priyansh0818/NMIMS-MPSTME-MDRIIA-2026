"""Rebuild figures from the validated submitted CSV evidence and its audit.

Use --verify to recalculate the complete 500 Hz export first. Without it, reuse
the saved all-run verification, check its metrics against the audited report,
and read the actual measured CSVs for the two plotted example traces.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,json,subprocess,sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from analyze_experiment import plots,comparison

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/rebuilt_figures')
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    export=ROOT/'analytics/submission_trials'
    if args.verify:
        verifier=ROOT/'analytics/reproduce_submission_metrics.py'
        if not verifier.exists():verifier=ROOT/'tools/export_trial_evidence.py'
        subprocess.run([sys.executable,'-B',str(verifier),'--verify-only','--export-dir',str(export)],check=True)
    info=json.loads((export/'EXPORT_MANIFEST.json').read_text())
    gate=json.loads((ROOT/'docs/final_evidence/SUBMISSION_CSV_EXPORT.json').read_text())
    if sha(export/'EXPORT_MANIFEST.json')!=gate['manifest_sha256']:raise ValueError('Export manifest changed')
    study=ROOT/'experiments/assessment_final_v1'
    if sha(study/'analysis/analysis.json')!=info['analysis_sha256']:raise ValueError('Audit report changed')
    verified=json.loads((export/'VERIFICATION.json').read_text())
    if not verified.get('all_verified') or len(verified['runs'])!=100:raise ValueError('All-run CSV verification required')
    records={(r['condition'],r['seed']):r for r in verified['runs']}
    entries={(r['condition'],r['seed']):r for r in info['runs']}
    audit=json.loads((study/'analysis/analysis.json').read_text())
    runs=[]
    for source in audit['runs']:
        key=(source['condition'],source['seed']);r=records[key];entry=entries[key]
        if not r['verified'] or r['samples']!=source['samples']:raise ValueError('Verification/sample mismatch')
        if r['restricted_completion_time_s']!=source['restricted_completion_time_s'] or r['final_correct_objects']!=source['correct_placements']:raise ValueError('Primary metric mismatch')
        runs.append(dict(r,horizon_s=source['horizon_s'],completion_success=source['completion_success']))
    traces={}
    names=['time_s','ee_x','ee_y','ee_z','ref_x','ref_y','ref_z','reach_lift_tracking_valid']
    for condition in ['baseline','proposed']:
        seed=min(k[1] for k in entries if k[0]==condition);entry=entries[condition,seed];trace=[]
        for part in entry['files']:
            p=export/part['path']
            if sha(p)!=part['sha256']:raise ValueError('Trace CSV hash mismatch')
            with gzip.open(p,'rt',encoding='utf-8',newline='') as f:
                header=next(csv.reader(f));values=np.loadtxt(f,delimiter=',',usecols=[header.index(n) for n in names],ndmin=2)
            trace.extend(values[::100].tolist())
        traces[condition]=trace
    args.output.mkdir(parents=True,exist_ok=True)
    plots(args.output,runs,traces,False)
    result=comparison([r['restricted_completion_time_s'] for r in runs if r['condition']=='baseline'],[r['restricted_completion_time_s'] for r in runs if r['condition']=='proposed'])
    report=dict(runs=100,saved_all_run_csv_verification_used=True,full_csv_verification_repeated=args.verify,
                source_manifest_sha256=sha(export/'EXPORT_MANIFEST.json'),primary_comparison=result,
                plotted_trace_seeds={'baseline':1000,'proposed':2000})
    (args.output/'REBUILD_PROVENANCE.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
