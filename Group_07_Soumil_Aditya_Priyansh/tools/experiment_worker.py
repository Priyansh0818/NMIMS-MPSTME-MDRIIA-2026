"""One isolated scenario-generation or physics-trial process in a frozen study."""
from pathlib import Path
import argparse
import csv
import gzip
import importlib.util
import json
import os
import platform
import sys
import time
import traceback

import mujoco
import numpy as np
import scipy

from experiment_core import (sha, write_json, verify_bundle, evaluate,
                             restricted_time, ContactAudit, TRACKING_PHASES)


def load_file(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--study',required=True,type=Path)
    parser.add_argument('--condition',choices=['baseline','proposed'],default='proposed')
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--generate',action='store_true')
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--limit',type=float,help='Pilot/smoke horizon only; never overrides final horizon')
    args=parser.parse_args()
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    study=args.study.resolve(); protocol=json.loads((study/'protocol.json').read_text())
    verify_bundle(study,protocol)
    task=json.loads((study/'task.json').read_text())
    condition='proposed' if args.generate else args.condition
    source=study/'variants'/condition/'src'
    sys.path.insert(0,str(source))
    import config as C
    C.ROOT=str(study/'task')
    C.MODEL_PATH=str(study/'task/models/hospital_assessment.xml')
    C.SCENE_MODELS={key:str(study/'task/models'/Path(value).name) for key,value in C.SCENE_MODELS.items()}
    C.SCENE_MODELS['assessment']=C.MODEL_PATH
    for key,value in task.items(): setattr(C,key,value)
    import system as SYS
    import scene
    base=load_file('study_measurement_base',study/'shared/measurement_base.py')
    scenario=study/'scenarios'/f'seed{args.seed}'
    output=(scenario/'generation') if args.generate else study/('pilot' if args.pilot else 'runs')/condition/f'seed{args.seed}'
    output.mkdir(parents=True,exist_ok=True)
    if not args.generate and (output/'result.json').exists():
        raise RuntimeError('Refusing to overwrite an existing trial')
    horizon=float(args.limit if args.pilot and args.limit else protocol['horizon_s'])
    spec=int(mujoco.mjtState.mjSTATE_INTEGRATION)

    class StudyTelemetry(base.TelemetryManager):
        def __init__(self,**kwargs):
            self.condition=condition
            self.source_dir=source
            self.phase_squared=0.; self.phase_count=0
            self.nav_squared=0.; self.nav_count=0
            self.path_key=None; self.path_start=None
            self.grasps=[]; self.docking=[]; self.transitions=[]
            super().__init__(**kwargs)
            self.chunk_rows=10000

        def start_run(self,s,seed):
            self.system=s
            self.robot_q=[]; self.robot_v=[]
            for j in range(s.model.njnt):
                if int(s.model.jnt_bodyid[j]) not in s.rb.robot_bodies: continue
                q0=int(s.model.jnt_qposadr[j]); v0=int(s.model.jnt_dofadr[j])
                q1=int(s.model.jnt_qposadr[j+1]) if j+1<s.model.njnt else s.model.nq
                v1=int(s.model.jnt_dofadr[j+1]) if j+1<s.model.njnt else s.model.nv
                self.robot_q.extend(range(q0,q1)); self.robot_v.extend(range(v0,v1))
            self.extra_columns=([f'qpos_{i:03d}' for i in self.robot_q]+
                [f'qvel_{i:03d}' for i in self.robot_v]+
                ['reach_lift_tracking_valid','nav_ref_x','nav_ref_y','nav_reference_valid','nav_path_error_m',
                 'target_state_valid','target_x','target_y','target_z','target_vx','target_vy','target_vz'])
            super().start_run(s,seed)
            self._metadata.update(condition=condition,
                source_sha256={p.name:sha(p) for p in source.glob('*.py')},
                experiment_protocol_sha256=sha(study/'protocol.json'),
                role='scenario initialisation only' if args.generate else 'pilot; exclude from final study' if args.pilot else 'frozen final experiment',
                scenario_state_sha256=None if args.generate else sha(scenario/'state.npz'),
                runtime=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,mujoco=mujoco.__version__,
                             python_hash_seed=os.environ.get('PYTHONHASHSEED','not fixed'),executable=sys.executable),
                reference=protocol['tracking_reference'],
                phase_tracking_states=sorted(TRACKING_PHASES),
                raw_encoding='Lossless gzip CSV, 10,000 physics samples per part; 500 Hz; state before next control update',
                robot_qpos_indices=self.robot_q,robot_qvel_indices=self.robot_v,
                controller_instrumentation=protocol['shared_instrumentation'])
            write_json(self._manifest_path,self._metadata)

        def _open_chunk(self):
            if self._physics: self._physics.close()
            if self._physics_columns[-len(self.extra_columns):]!=self.extra_columns:
                self._physics_columns+=self.extra_columns
            path=self.dir+f'/{self.tag}_part{len(self.physics_paths)+1:03d}_real_trials.csv.gz'
            self.physics_paths.append(path)
            if len(self.physics_paths)==1: self.physics_path=path
            self._physics=gzip.open(path,'wt',newline='',compresslevel=1,encoding='utf-8')
            self._pw=csv.writer(self._physics); self._pw.writerow(self._physics_columns)

        def extra_values(self,s,valid):
            phase=bool(valid and s.ctrl.state in TRACKING_PHASES)
            # The reference is the commanded arm path in the instantaneous base frame.
            sp=s.ctrl.arm.sp; x,y,yaw=s.rb.base_pose(); co,si=np.cos(yaw),np.sin(yaw)
            local=np.array([s.rb.gc_x,s.rb.gc_y0-sp['ext']])
            ref=np.array([x+co*local[0]-si*local[1],y+si*local[0]+co*local[1],s.rb.gc_z0+sp['lift']])
            if phase:
                self.phase_squared+=float(np.sum((ref-s.rb.gc())**2)); self.phase_count+=1
            nav_valid=bool(s.ctrl.state.startswith('NAV') and len(s.nav.path_xy)>1)
            nearest=np.array([x,y]); error=0.
            if nav_valid:
                key=id(s.nav.path_xy)
                if key!=self.path_key:
                    points=np.array(s.nav.path_xy,float)
                    self.path_start=points[:-1]; self.path_delta=np.diff(points,axis=0)
                    self.path_norm=np.maximum(np.sum(self.path_delta**2,axis=1),1e-20)
                    self.path_key=key
                rel=np.array([x,y])-self.path_start
                fraction=np.clip(np.sum(rel*self.path_delta,axis=1)/self.path_norm,0,1)
                candidates=self.path_start+fraction[:,None]*self.path_delta
                squares=np.sum((candidates-[x,y])**2,axis=1); best=int(np.argmin(squares))
                nearest=candidates[best]; error=float(np.sqrt(squares[best]))
                self.nav_squared+=error**2; self.nav_count+=1
            target=s.ctrl.target.name if s.ctrl.target is not None else None
            if target is not None:
                position=s.cl.pos(target); v0=s.cl.vadr[target]; velocity=s.data.qvel[v0:v0+3]
            else: position=velocity=np.zeros(3)
            return [*s.data.qpos[self.robot_q],*s.data.qvel[self.robot_v],int(phase),*nearest,int(nav_valid),error,
                    int(target is not None),*position,*velocity]

        def grasp(self,success):
            super().grasp(success)
            target=self.system.ctrl.target
            self.grasps.append(dict(time_s=float(self.system.ctrl.t),object=target.name if target else None,
                                   type=self.system.cl.type_of[target.name] if target else None,success=bool(success)))

    SYS.TelemetryManager=lambda **kw:StudyTelemetry(**kw)
    if not args.generate:
        saved=np.load(scenario/'state.npz')
        record=json.loads((scenario/'scenario.json').read_text())
        if record['state_sha256']!=sha(scenario/'state.npz'): raise RuntimeError('Scenario hash mismatch')
        def initialise(clutter,*unused,**ignored):
            mujoco.mj_setState(clutter.rb.m,clutter.rb.d,saved['integration_state'],spec)
            mujoco.mj_forward(clutter.rb.m,clutter.rb.d)
            mujoco.mj_setState(clutter.rb.m,clutter.rb.d,saved['integration_state'],spec)
            clutter.spawn={name:clutter.pos(name) for name in clutter.names}
            return []
        scene.ClutterManager.randomize=initialise

    started=time.perf_counter(); s=None
    try:
        s=SYS.System(seed=args.seed,verbose=True,out_dir=str(output),tag=f'{condition}_seed{args.seed}',model_path=C.MODEL_PATH)
        if args.generate:
            if s.spawn_unstable: raise RuntimeError('Unstable scene generation: '+str(s.spawn_unstable))
            state=np.empty(mujoco.mj_stateSize(s.model,spec))
            mujoco.mj_getState(s.model,s.data,state,spec)
            np.savez_compressed(scenario/'state.npz',integration_state=state,qpos=s.data.qpos,qvel=s.data.qvel,
                                ctrl=s.data.ctrl,act=s.data.act,qacc_warmstart=s.data.qacc_warmstart,time=s.data.time)
            write_json(scenario/'scenario.json',dict(seed=args.seed,state_sha256=sha(scenario/'state.npz'),
                initial_positions={name:s.cl.pos(name).tolist() for name in s.cl.names},
                acceptance=protocol['scenario_distribution'],generator='frozen proposed geometry feasibility checker; same for both conditions'))
            return
        if abs(s.dt-.002)>1e-12 or s.ctrl_every!=10: raise RuntimeError('Unexpected physics/control rates')
        state=np.empty(mujoco.mj_stateSize(s.model,spec)); mujoco.mj_getState(s.model,s.data,state,spec)
        if not np.array_equal(state,saved['integration_state']): raise RuntimeError('Initial integration state mismatch')
        audit=ContactAudit(s)
        # Disable each version's historical counter, replacing it with the same 500 Hz observer.
        s.ctrl.monitor_collisions=lambda *a,**kw:None
        original_drop=s.ctrl.dropped
        def observed_drop():
            before=s.tele.carry_drops; original_drop()
            if s.tele.carry_drops==before: s.tele.carry_drops+=1
        s.ctrl.dropped=observed_drop
        steps=int(round(horizon/s.dt)); status='timed_out'; last_heartbeat=-30.
        for step in range(steps):
            mujoco.mj_step(s.model,s.data); s._n+=1
            elapsed=s.data.time-s.run_start
            audit.step(elapsed)
            # Log the reference actually applied over this step, before issuing the next command.
            s.tele.physics_sample(s)
            if s._n%s.ctrl_every==0:
                old_state=s.ctrl.state
                old_target=s.ctrl.target.name if s.ctrl.target is not None else ''
                s.ctrl.step(s.ctrl_every*s.dt)
                if s.ctrl.state!=old_state:
                    s.tele.transitions.append(dict(time_s=round(elapsed,6),old_state=old_state,new_state=s.ctrl.state,
                        target=s.ctrl.target.name if s.ctrl.target is not None else old_target))
                if old_state=='NAV_APPROACH' and s.ctrl.state=='PREGRASP' and s.nav.goal is not None:
                    xy=np.asarray(s.rb.base_pose()[:2]); goal=np.asarray(s.nav.goal[:2])
                    s.tele.docking.append(dict(time_s=elapsed,error_m=float(np.linalg.norm(xy-goal))))
            if elapsed-last_heartbeat>=30:
                last_heartbeat=elapsed
                if not np.isfinite(s.data.qpos).all() or not np.isfinite(s.data.qvel).all():
                    raise RuntimeError('Nonfinite simulator state')
                write_json(output/'status.json',dict(condition=condition,seed=args.seed,sim_time_s=round(elapsed,2),
                    state=s.ctrl.state,placement_events=len(s.ctrl.cleaned),collision_events=audit.episodes,
                    wall_s=round(time.perf_counter()-started,1)))
            if s.ctrl.state in ['DONE','SAFE_STOP']:
                status='safe_stop' if s.ctrl.state=='SAFE_STOP' else 'exhausted'
                break
        items=evaluate(s,task); cleaned=sum(item['contained'] for item in items.values())
        if cleaned==len(items) and status!='safe_stop': status='completed'
        elapsed=float(s.data.time-s.run_start)
        result=s.tele.summary(elapsed,len(items),len(s.world.votes),
            sum(int(min(set(v),key=lambda kind:(-v.count(kind),kind))==s.cl.type_of[n]) for n,v in s.world.votes.items()),
            cleaned,len(items)-cleaned,wall=time.perf_counter()-started,seed=args.seed)
        result.update(run_status=status,condition=condition,seed=args.seed,study_eligible=not args.pilot,
            elapsed_s=elapsed,horizon_s=horizon,restricted_completion_time_s=restricted_time(status,elapsed,horizon,cleaned==len(items)),
            physics_hz=1/s.dt,samples=s.tele.physics_rows,collision_events=audit.episodes,
            unexpected_contact_samples=audit.samples,effort_by_actuator=s.tele.effort.tolist(),
            reach_lift_rmse_m=float(np.sqrt(s.tele.phase_squared/s.tele.phase_count)) if s.tele.phase_count else None,
            reach_lift_samples=s.tele.phase_count,
            navigation_path_rmse_m=float(np.sqrt(s.tele.nav_squared/s.tele.nav_count)) if s.tele.nav_count else None,
            navigation_samples=s.tele.nav_count,docking=s.tele.docking,grasp_events=s.tele.grasps,items=items,
            protocol_sha256=sha(study/'protocol.json'),scenario_state_sha256=sha(scenario/'state.npz'),
            final_source_check=True)
        verify_bundle(study,protocol)
        np.savez_compressed(output/'final.npz',qpos=s.data.qpos,qvel=s.data.qvel,ctrl=s.data.ctrl,
                            act=s.data.act,qacc_warmstart=s.data.qacc_warmstart,time=s.data.time)
        s.tele.write_summary(result)
        s.tele.close()
        transition_path=output/'state_events.csv'
        with transition_path.open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=['time_s','old_state','new_state','target'])
            writer.writeheader(); writer.writerows(s.tele.transitions)
        result['state_events_sha256']=sha(transition_path)
        manifest=json.loads(Path(s.tele._manifest_path).read_text())
        result['manifest_file']=Path(s.tele._manifest_path).name
        result['raw_files']=[dict(path=name,sha256=sha(output/name),bytes=(output/name).stat().st_size)
                             for name in manifest['data_files']]
        write_json(output/'result.json',result)
        print('RESULT',json.dumps({k:result[k] for k in ['seed','condition','run_status','cleaned','samples','collision_events']}),flush=True)
    except BaseException as error:
        write_json(output/'error.json',dict(error=repr(error),traceback=traceback.format_exc(),
                   condition=condition,seed=args.seed,role='infrastructure/worker error; experiment incomplete'))
        raise
    finally:
        if s is not None: s.tele.close()


if __name__=='__main__': main()
