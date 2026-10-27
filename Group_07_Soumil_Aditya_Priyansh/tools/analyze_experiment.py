"""Audit measured physics rows before producing study statistics and plots."""
from pathlib import Path
import argparse
import csv
import gzip
import json
import math
import sys
import gc

import mujoco
import numpy as np
from scipy import stats

from experiment_core import sha,write_json,verify_bundle,half_extents,contained,restricted_time


def comparison(baseline,proposed):
    a=np.asarray(baseline,float); b=np.asarray(proposed,float)
    if len(a)<2 or len(b)<2: return dict(available=False,reason='At least two observations per condition needed')
    va=float(a.var(ddof=1)); vb=float(b.var(ddof=1)); na=len(a); nb=len(b)
    difference=float(a.mean()-b.mean()); se2=va/na+vb/nb
    pooled=math.sqrt(((na-1)*va+(nb-1)*vb)/(na+nb-2))
    common=dict(n_baseline=na,n_proposed=nb,mean_baseline=float(a.mean()),mean_proposed=float(b.mean()),
                sd_baseline=math.sqrt(va),sd_proposed=math.sqrt(vb),difference_baseline_minus_proposed=difference,
                cohen_d=difference/pooled if pooled>0 else None)
    if se2<=0: return dict(available=False,reason='Zero variance; inferential test undefined',**common)
    denominator=(va/na)**2/(na-1)+(vb/nb)**2/(nb-1)
    df=se2**2/denominator; t=difference/math.sqrt(se2)
    p=float(2*stats.t.sf(abs(t),df)); radius=float(stats.t.ppf(.975,df)*math.sqrt(se2))
    return dict(available=True,test='Independent two-sided Welch t-test',t=t,df=df,p=p,
                ci95=[difference-radius,difference+radius],**common)


def open_csv(path):
    return gzip.open(path,'rt',newline='',encoding='utf-8') if path.suffix=='.gz' else path.open(newline='',encoding='utf-8')


def audit_run(study,folder,protocol,model,task):
    result=json.loads((folder/'result.json').read_text())
    manifest=json.loads((folder/result['manifest_file']).read_text())
    numeric_names=None; rows=0; previous=None; collision_last=-math.inf; episodes=0; hits=0
    max_dt_error=0.; effort=np.zeros(model.nu); phase_ss=0.; phase_n=0; nav_ss=0.; nav_n=0
    force_names=['force_'+model.actuator(i).name for i in range(model.nu)]
    trace=[]
    for file in result['raw_files']:
        path=folder/file['path']
        if sha(path)!=file['sha256']: raise ValueError('Raw file hash mismatch: '+str(path))
        with open_csv(path) as stream:
            header=next(csv.reader(stream))
            indices=[i for i,name in enumerate(header) if name not in ['run_id','condition','state','target']]
            names=[header[i] for i in indices]; index={name:i for i,name in enumerate(names)}
            data=np.loadtxt(stream,delimiter=',',usecols=indices,ndmin=2)
        if data.shape[0]==0: raise ValueError('Empty physics part')
        if not np.isfinite(data).all(): raise ValueError('Nonfinite physics values')
        if header!=manifest['sample_columns']: raise ValueError('Header/manifest mismatch')
        with open_csv(path) as stream:
            next(stream)
            identities=np.loadtxt(stream,delimiter=',',usecols=[0,2],dtype=str,ndmin=2)
        if not np.all(identities[:,0]==result['run_id']) or not np.all(identities[:,1]==result['condition']):
            raise ValueError('Raw trial identity mismatch')
        if not np.all(data[:,index['seed']]==result['seed']): raise ValueError('Seed mismatch')
        times=data[:,index['time_s']]
        differences=np.diff(times,prepend=previous if previous is not None else 0.)
        max_dt_error=max(max_dt_error,float(np.max(np.abs(differences-.002))))
        previous=float(times[-1]); rows+=len(data)
        forces=data[:,[index[name] for name in force_names]]
        effort+=np.sum(forces**2,axis=0)*.002
        errors=data[:,[index['error_x'],index['error_y'],index['error_z']]]
        phase=data[:,index['reach_lift_tracking_valid']]>0.5
        phase_ss+=float(np.sum(errors[phase]**2)); phase_n+=int(phase.sum())
        nav=data[:,index['nav_reference_valid']]>0.5
        nav_ss+=float(np.sum(data[nav,index['nav_path_error_m']]**2)); nav_n+=int(nav.sum())
        contact_times=times[data[:,index['robot_collision']]>0.5]
        if len(contact_times):
            gaps=np.diff(contact_times,prepend=collision_last)
            episodes+=int(np.sum(gaps>1.)); collision_last=float(contact_times[-1]); hits+=len(contact_times)
        # Display a fixed 5 Hz downsample, preserving gaps in the reach/lift reference.
        trace.extend(data[::100,[index[n] for n in ['time_s','ee_x','ee_y','ee_z','ref_x','ref_y','ref_z','reach_lift_tracking_valid']]].tolist())
        del data,identities
    if rows!=result['samples'] or rows!=manifest['sample_count'] or max_dt_error>1e-9:
        raise ValueError('Sample count/cadence mismatch')
    if not np.allclose(effort,result['effort_by_actuator'],rtol=5e-6,atol=1e-6):
        raise ValueError('Effort integral mismatch')
    if episodes!=result['collision_events'] or hits!=result['unexpected_contact_samples']:
        raise ValueError('Contact count mismatch')
    for name,expected in manifest['source_sha256'].items():
        if sha(study/'variants'/result['condition']/'src'/name)!=expected: raise ValueError('Source mismatch')
    if result['protocol_sha256']!=sha(study/'protocol.json'): raise ValueError('Protocol mismatch')
    initial=study/'scenarios'/f"seed{result['seed']}"/'state.npz'
    if sha(initial)!=result['scenario_state_sha256']: raise ValueError('Initial state mismatch')
    final=np.load(folder/'final.npz'); d=mujoco.MjData(model)
    d.qpos[:]=final['qpos']; d.qvel[:]=final['qvel']; mujoco.mj_forward(model,d)
    item_results={}
    for body_id in range(model.nbody):
        body_name=model.body(body_id).name
        if not body_name.startswith('clutter_'): continue
        name=body_name[len('clutter_'):]; kind=name.split('_')[0]
        zone_name=task['CATEGORY_TO_ZONE'][task['CATEGORY_OF_TYPE'][kind]]
        zone=dict(task['ZONES'][zone_name],center=d.xpos[model.body(zone_name).id][:2])
        half=half_extents(model,d,model.geom(name+'_geom').id)
        item_results[name]=contained(zone,d.xpos[body_id],half)
    cleaned=sum(item_results.values()); total=len(item_results)
    if cleaned!=result['cleaned'] or total!=16: raise ValueError('Final physical containment mismatch')
    transition_path=folder/'state_events.csv'
    if sha(transition_path)!=result['state_events_sha256']: raise ValueError('State-event hash mismatch')
    starts={}; cycles=[]
    with transition_path.open(newline='',encoding='utf-8') as stream:
        for event in csv.DictReader(stream):
            name=event['target']; t=float(event['time_s'])
            if event['new_state']=='PREGRASP': starts[name]=t
            if name in starts and event['new_state'] in ['STOW','RECOVER','SAFE_STOP']:
                cycles.append(dict(object=name,type=name.split('_')[0],duration_s=t-starts.pop(name),
                                   verified_lift=event['new_state']=='STOW'))
    phase_rmse=math.sqrt(phase_ss/phase_n) if phase_n else None
    if phase_n!=result['reach_lift_samples'] or (phase_n and not math.isclose(phase_rmse,result['reach_lift_rmse_m'],rel_tol=5e-6,abs_tol=1e-7)):
        raise ValueError('Tracking integral mismatch')
    record=dict(condition=result['condition'],seed=result['seed'],run_id=result['run_id'],run_status=result['run_status'],
        correct_placements=cleaned,objects_total=total,completion_success=int(cleaned==total and result['run_status']=='completed'),
        elapsed_s=previous,horizon_s=result['horizon_s'],restricted_completion_time_s=restricted_time(result['run_status'],previous,result['horizon_s'],cleaned==total),
        reach_lift_rmse_m=phase_rmse,navigation_path_rmse_m=math.sqrt(nav_ss/nav_n) if nav_n else None,
        collision_events=episodes,unexpected_contact_samples=hits,carry_drops=result['carry_drops'],
        samples=rows,max_sample_interval_error_s=max_dt_error,effort_by_actuator=effort.tolist(),
        raw_audit_passed=True,folder=folder.relative_to(study).as_posix(),
        physical_placements=item_results,grasp_events=result['grasp_events'],docking=result['docking'],grasp_cycles=cycles)
    return record,trace


def plots(output,runs,traces,pilot):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels=['Baseline','Proposed']; conditions=['baseline','proposed']
    colour=['#6c7a89','#008c95']
    arrays=[[r['restricted_completion_time_s'] for r in runs if r['condition']==c] for c in conditions]
    if all(arrays):
        fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
        axes[0].boxplot(arrays,tick_labels=labels,showmeans=True)
        for i,values in enumerate(arrays):
            jitter=np.linspace(-.12,.12,len(values))
            axes[0].scatter(i+1+jitter,values,s=18,color=colour[i],alpha=.7)
        horizons=sorted(set(r['horizon_s'] for r in runs))
        axes[0].set(ylabel='Restricted completion time (s)',title='Failure horizon: '+', '.join(f'{h:g} s' for h in horizons))
        rates=[sum(r['completion_success'] for r in runs if r['condition']==c)/len(v) for c,v in zip(conditions,arrays)]
        axes[1].bar(labels,rates,color=colour); axes[1].set(ylim=(0,1.05),ylabel='Complete-room success fraction',title='All 16 objects correctly contained')
        fig.suptitle(('PILOT - excluded from final study' if pilot else 'Held-out physics experiment')+
                     f' | N = {len(arrays[0])}, {len(arrays[1])}')
        fig.savefig(output/'task_results.png',dpi=180); plt.close(fig)
    for c,trace in traces.items():
        a=np.array(trace)
        if not len(a): continue
        fig,axes=plt.subplots(3,1,figsize=(11,7),sharex=True,layout='constrained')
        for i,ax in enumerate(axes):
            actual=a[:,1+i].copy(); ref=a[:,4+i].copy()
            actual[a[:,7]<.5]=np.nan; ref[a[:,7]<.5]=np.nan
            ax.plot(a[:,0],ref,label='Command reference',color='#e79a33',linewidth=1.2)
            ax.plot(a[:,0],actual,label='Measured',color='#008c95',linewidth=.8)
            ax.set_ylabel('XYZ'[i]+' (m)')
        axes[0].legend(); axes[-1].set_xlabel('Simulation time (s)')
        fig.suptitle(c.title()+': first seed in scheduled condition set; reach/lift phases, 5 Hz display')
        fig.savefig(output/(c+'_tracking.png'),dpi=180); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--study',required=True,type=Path)
    parser.add_argument('--pilot',action='store_true'); args=parser.parse_args()
    study=args.study.resolve(); protocol=json.loads((study/'protocol.json').read_text()); verify_bundle(study,protocol)
    task=json.loads((study/'task.json').read_text())
    output=study/('pilot_analysis' if args.pilot else 'analysis'); output.mkdir(exist_ok=True)
    model=mujoco.MjModel.from_xml_path(str(study/'task/models/hospital_assessment.xml'))
    runs=[]; missing=[]; errors=[]; traces={}
    for condition in ['baseline','proposed']:
        seeds=[protocol['pilot_seed']] if args.pilot else protocol['conditions'][condition]['seeds']
        for seed in seeds:
            folder=study/('pilot' if args.pilot else 'runs')/condition/f'seed{seed}'
            if not (folder/'result.json').exists(): missing.append(dict(condition=condition,seed=seed)); continue
            try:
                if (folder/'error.json').exists(): raise ValueError('Worker error retained')
                record,trace=audit_run(study,folder,protocol,model,task)
                runs.append(record)
                if seed==seeds[0]: traces[condition]=trace
            except Exception as error: errors.append(dict(condition=condition,seed=seed,error=repr(error)))
            gc.collect()
            print('AUDITED',condition,seed,flush=True)
    complete=not missing and not errors
    inferential=(complete and not args.pilot and len(runs)==100)
    statistical=comparison([r['restricted_completion_time_s'] for r in runs if r['condition']=='baseline'],
                           [r['restricted_completion_time_s'] for r in runs if r['condition']=='proposed']) if inferential else dict(available=False,reason='Pilot or incomplete/unverified experiment')
    report=dict(role='pilot; exclude from final claims' if args.pilot else 'frozen held-out experiment',
                protocol_sha256=sha(study/'protocol.json'),complete=complete,inferential_ready=inferential,
                required_per_condition=50,runs=runs,missing=missing,audit_errors=errors,primary_comparison=statistical,
                limitations=protocol['limitations'])
    write_json(output/'analysis.json',report)
    fields=['condition','seed','run_id','run_status','correct_placements','objects_total','completion_success',
            'elapsed_s','restricted_completion_time_s','reach_lift_rmse_m','navigation_path_rmse_m',
            'collision_events','carry_drops','samples','raw_audit_passed']
    with (output/'run_metrics.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in runs)
    with (output/'actuator_effort.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream); writer.writerow(['condition','seed','actuator','squared_effort_integral','units'])
        for r in runs:
            for i,value in enumerate(r['effort_by_actuator']):
                joint=int(model.actuator_trnid[i,0])
                unit='N^2 s' if int(model.jnt_type[joint])==2 else '(N m)^2 s'
                writer.writerow([r['condition'],r['seed'],model.actuator(i).name,value,unit])
    with (output/'object_geometry_results.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream)
        writer.writerow(['condition','object_type','scheduled_objects','correct_final_placements','grasp_attempts',
                         'verified_lifts','completed_grasp_cycles','mean_completed_grasp_cycle_s'])
        for condition in ['baseline','proposed']:
            records=[r for r in runs if r['condition']==condition]
            for kind in ['cup','bottle','slipper','paper']:
                opportunities=[(n,v) for r in records for n,v in r['physical_placements'].items() if n.split('_')[0]==kind]
                grasps=[e for r in records for e in r['grasp_events'] if e['type']==kind]
                cycles=[e['duration_s'] for r in records for e in r['grasp_cycles'] if e['type']==kind and e['verified_lift']]
                writer.writerow([condition,kind,len(opportunities),sum(v for _,v in opportunities),len(grasps),
                                 sum(e['success'] for e in grasps),len(cycles),float(np.mean(cycles)) if cycles else ''])
    plots(output,runs,traces,args.pilot)
    lines=['# Experiment analysis','',report['role'],'',f'Audited runs: {len(runs)}. Missing: {len(missing)}. Audit errors: {len(errors)}.',
           '',f'Inferential reporting ready: {inferential}.','',
           'Primary measure: '+protocol['primary_metric'],'',
           'The raw files are measured 500 Hz physics samples, compressed as lossless CSV.','',
           'See analysis.json for source-linked metrics, audit failures and test definitions.']
    if inferential: lines+=['','```json',json.dumps(statistical,indent=2),'```']
    (output/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(complete=complete,inferential_ready=inferential,audited=len(runs),errors=errors)),flush=True)
    if errors: raise SystemExit(1)


if __name__=='__main__': main()
