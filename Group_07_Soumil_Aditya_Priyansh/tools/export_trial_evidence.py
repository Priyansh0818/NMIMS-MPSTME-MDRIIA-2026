"""Project all audited trials to analysis-relevant 500 Hz CSV columns, losslessly.

No rows are dropped or rounded. Verbose robot joint channels remain in originals.
--verify-only reproduces metrics from the exported measurements and retained states.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,json,math,os,shutil,sys,time
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_STUDY=ROOT/'experiments/assessment_final_v1'
DEFAULT_EXPORT=ROOT/'analytics/submission_trials'
COLUMNS=['run_id','seed','condition','time_s','state','target','robot_collision','contact_count',
         'base_x','base_y','base_yaw','base_vx','base_vy','base_wz',
         'ee_x','ee_y','ee_z','ref_x','ref_y','ref_z','reference_valid',
         'error_x','error_y','error_z','reach_lift_tracking_valid',
         'nav_ref_x','nav_ref_y','nav_reference_valid','nav_path_error_m']

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def save(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
 temp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8');temp.replace(path)

def validate_trial(export,entry,model,task,core):
 rows=0;previous=0.;phase_ss=0.;phase_n=0;nav_ss=0.;nav_n=0;effort=np.zeros(model.nu)
 last=-math.inf;episodes=0;contacts=0;dt_error=0.
 forces=['force_'+model.actuator(i).name for i in range(model.nu)]
 for item in entry['files']:
  p=export/item['path']
  if sha(p)!=item['sha256']:raise ValueError('Export hash mismatch: '+str(p))
  with gzip.open(p,'rt',newline='',encoding='utf-8') as f:
   reader=csv.reader(f);header=next(reader);records=list(reader)
  if header!=entry['columns']:raise ValueError('Export header mismatch')
  indices=[i for i,n in enumerate(header) if n not in ['run_id','condition','state','target']]
  names=[header[i] for i in indices];idx={n:i for i,n in enumerate(names)}
  data=np.asarray([[float(r[i]) for i in indices] for r in records],dtype=float)
  if not np.isfinite(data).all():raise ValueError('Nonfinite exported values')
  if any(r[0]!=entry['run_id'] or r[2]!=entry['condition'] for r in records):raise ValueError('Run identity mismatch')
  if not np.all(data[:,idx['seed']]==entry['seed']):raise ValueError('Seed mismatch')
  t=data[:,idx['time_s']];dt_error=max(dt_error,float(np.max(np.abs(np.diff(t,prepend=previous)-.002))));previous=float(t[-1]);rows+=len(t)
  effort+=np.sum(data[:,[idx[n] for n in forces]]**2,axis=0)*.002
  phase=data[:,idx['reach_lift_tracking_valid']]>.5;errors=data[:,[idx[n] for n in ['error_x','error_y','error_z']]]
  phase_ss+=float(np.sum(errors[phase]**2));phase_n+=int(phase.sum())
  nav=data[:,idx['nav_reference_valid']]>.5;nav_ss+=float(np.sum(data[nav,idx['nav_path_error_m']]**2));nav_n+=int(nav.sum())
  hits=t[data[:,idx['robot_collision']]>.5]
  if len(hits):episodes+=int(np.sum(np.diff(hits,prepend=last)>1.));last=float(hits[-1]);contacts+=len(hits)
 expected=entry['audited_metrics']
 if rows!=expected['samples'] or dt_error>1e-9:raise ValueError('Rows/cadence mismatch')
 rmse=math.sqrt(phase_ss/phase_n) if phase_n else None
 nav_rmse=math.sqrt(nav_ss/nav_n) if nav_n else None
 for x,y in [(rmse,expected['reach_lift_rmse_m']),(nav_rmse,expected['navigation_path_rmse_m'])]:
  if (x is None)!=(y is None) or (x is not None and not math.isclose(x,y,rel_tol=5e-6,abs_tol=1e-7)):raise ValueError('RMSE mismatch')
 if not np.allclose(effort,expected['effort_by_actuator'],rtol=5e-6,atol=1e-6):raise ValueError('Effort mismatch')
 if contacts!=expected['unexpected_contact_samples'] or episodes!=expected['collision_events']:raise ValueError('Contact mismatch')
 support=export/entry['support'];raw_result=json.loads((support/'result.json').read_text())
 for name,digest in entry['support_sha256'].items():
  if sha(support/name)!=digest:raise ValueError('Retained state/event evidence changed')
 final=np.load(support/'final.npz');data_state=mujoco.MjData(model);data_state.qpos[:]=final['qpos'];data_state.qvel[:]=final['qvel'];mujoco.mj_forward(model,data_state)
 physical={}
 for body in range(model.nbody):
  name=model.body(body).name
  if not name.startswith('clutter_'):continue
  name=name[len('clutter_'):];kind=name.split('_')[0];zone_name=task['CATEGORY_TO_ZONE'][task['CATEGORY_OF_TYPE'][kind]]
  zone=dict(task['ZONES'][zone_name],center=data_state.xpos[model.body(zone_name).id][:2])
  physical[name]=core.contained(zone,data_state.xpos[body],core.half_extents(model,data_state,model.geom(name+'_geom').id))
 if physical!=expected['physical_placements']:raise ValueError('Physical placement mismatch')
 primary=core.restricted_time(raw_result['run_status'],previous,raw_result['horizon_s'],all(physical.values()))
 if not math.isclose(primary,expected['restricted_completion_time_s'],abs_tol=1e-7):raise ValueError('Primary outcome mismatch')
 starts={};cycles=[]
 with (support/'state_events.csv').open(newline='',encoding='utf-8') as f:
  for event in csv.DictReader(f):
   name=event['target'];t=float(event['time_s'])
   if event['new_state']=='PREGRASP':starts[name]=t
   if name in starts and event['new_state'] in ['STOW','RECOVER','SAFE_STOP']:
    cycles.append(dict(object=name,type=name.split('_')[0],duration_s=t-starts.pop(name),verified_lift=event['new_state']=='STOW'))
 if cycles!=expected['grasp_cycles']:raise ValueError('Grasp-cycle mismatch')
 return dict(condition=entry['condition'],seed=entry['seed'],samples=rows,physics_hz=500,
             reach_lift_rmse_m=rmse,navigation_path_rmse_m=nav_rmse,collision_events=episodes,
             restricted_completion_time_s=primary,final_correct_objects=sum(physical.values()),verified=True)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,default=DEFAULT_STUDY)
 parser.add_argument('--export-dir',type=Path,default=DEFAULT_EXPORT);parser.add_argument('--verify-only',action='store_true')
 args=parser.parse_args();study=args.study.resolve();export=args.export_dir.resolve()
 sys.path.insert(0,str(study/'harness'));import experiment_core as core
 protocol=json.loads((study/'protocol.json').read_text());core.verify_bundle(study,protocol)
 model=mujoco.MjModel.from_xml_path(str(study/'task/models/hospital_assessment.xml'));task=json.loads((study/'task.json').read_text())
 manifest=export/'EXPORT_MANIFEST.json'
 if args.verify_only:
  info=json.loads(manifest.read_text());verified=[]
  for entry in info['runs']:
   verified.append(validate_trial(export,entry,model,task,core));print('VERIFIED',entry['condition'],entry['seed'],flush=True)
  save(export/'VERIFICATION.json',dict(all_verified=True,runs=verified));return
 a=json.loads((study/'analysis/analysis.json').read_text())
 if not(a.get('complete') and a.get('inferential_ready') and not a.get('audit_errors') and len(a['runs'])==100):raise ValueError('Complete 100-run original audit required')
 export.mkdir(parents=True,exist_ok=True)
 lock=(export/'export.lock').open('a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
 if os.name=='nt':
  import msvcrt
  try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:raise RuntimeError('Another exporter owns this export; do not duplicate it')
 else:
  import fcntl
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 save(export/'EXPORT_STATUS.json',dict(status='starting',pid=os.getpid(),updated_unix=time.time()))
 info=json.loads(manifest.read_text()) if manifest.exists() else dict(analysis_sha256=sha(study/'analysis/analysis.json'),
       scope='All scheduled runs and rows, selected measured columns; no downsampling/rounding. Original joint-state diagnostics retained locally.',
       excludes='Verbose joint qpos/qvel, actuator commands and target-state diagnostic channels; retained poses/velocities/command reference/errors/forces/events support reported analyses.',runs=[])
 if info['analysis_sha256']!=sha(study/'analysis/analysis.json'):raise ValueError('Different audit report; use a new export folder')
 finished={(r['condition'],r['seed']) for r in info['runs']};verified=[]
 columns=COLUMNS+['force_'+model.actuator(i).name for i in range(model.nu)]
 for record in a['runs']:
  key=record['condition'],record['seed']
  if key in finished:
   entry=next(e for e in info['runs'] if (e['condition'],e['seed'])==key);verified.append(validate_trial(export,entry,model,task,core));continue
  folder=study/record['folder'];result=json.loads((folder/'result.json').read_text())
  relative=Path(record['condition'])/f"seed{record['seed']}";destination=export/relative;destination.mkdir(parents=True,exist_ok=True)
  support=destination/'support';support.mkdir(exist_ok=True);support_sha={}
  for source in folder.iterdir():
   if source.suffix in ['.json','.npz'] or source.name=='state_events.csv' or source.name.startswith('events_'):
    shutil.copy2(source,support/source.name);support_sha[source.name]=sha(support/source.name)
  entry=dict(condition=record['condition'],seed=record['seed'],run_id=record['run_id'],columns=columns,
             files=[],support=str((relative/'support').as_posix()),support_sha256=support_sha,audited_metrics=record)
  for i,item in enumerate(result['raw_files'],1):
   source=folder/item['path'];target=destination/f"{record['run_id']}_part{i:04d}_real_trials.csv.gz"
   temp=target.with_suffix(target.suffix+'.tmp')
   with gzip.open(source,'rt',newline='',encoding='utf-8') as inp,gzip.open(temp,'wt',newline='',encoding='utf-8',compresslevel=6) as out:
    reader=csv.reader(inp);header=next(reader);indices=[header.index(n) for n in columns];writer=csv.writer(out);writer.writerow(columns);rows=0
    for row in reader:writer.writerow([row[j] for j in indices]);rows+=1
   temp.replace(target)
   entry['files'].append(dict(path=str((relative/target.name).as_posix()),rows=rows,sha256=sha(target),bytes=target.stat().st_size,
                             source_file=item['path'],original_sha256_from_full_audit=item['sha256']))
  verified.append(validate_trial(export,entry,model,task,core))
  info['runs'].append(entry);save(manifest,info)
  save(export/'EXPORT_STATUS.json',dict(completed=len(info['runs']),planned=100,last_seed=record['seed'],status='exporting',pid=os.getpid(),updated_unix=time.time()))
  print('EXPORTED_AND_VERIFIED',record['condition'],record['seed'],flush=True)
 if len(verified)!=100:raise ValueError('Not every scheduled run was verified')
 save(export/'VERIFICATION.json',dict(all_verified=True,runs=verified))
 summary=dict(all_reported_metrics_reproduced=True,export_root=str(export),runs=100,physics_hz=500,
              analysis_sha256=info['analysis_sha256'],manifest_sha256=sha(manifest),
              csv_columns=columns,no_rows_removed=True,no_rounding=True,
              exported_bytes=sum(f['bytes'] for e in info['runs'] for f in e['files']),
              retained_originals=True,validation='Primary/final containment, cadence, effort channels, tracking/navigation RMSE, contacts and grasp-cycle durations recomputed. Original grasp-event/carry-drop records retained with provenance.')
 save(ROOT/'docs/final_evidence/SUBMISSION_CSV_EXPORT.json',summary)
 save(export/'EXPORT_STATUS.json',dict(completed=100,planned=100,status='verified',pid=os.getpid(),updated_unix=time.time()))
 print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
