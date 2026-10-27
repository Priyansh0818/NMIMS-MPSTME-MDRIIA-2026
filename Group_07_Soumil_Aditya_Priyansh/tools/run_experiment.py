"""Resumable coordinator; each scenario and trial gets its own Python process."""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
import os
import random
import subprocess
import sys
import time

from experiment_core import write_json,verify_bundle


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--study',required=True,type=Path)
    parser.add_argument('--workers',type=int,default=2,choices=[1,2])
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--limit',type=float,help='Pilot/smoke horizon only')
    args=parser.parse_args()
    study=args.study.resolve(); protocol=json.loads((study/'protocol.json').read_text())
    verify_bundle(study,protocol)
    if args.limit and not args.pilot: raise ValueError('Final horizon is frozen in protocol')
    if not args.pilot and not (protocol.get('validation_pilot') or {}).get('passed'):
        raise RuntimeError('Final batch requires a copied, audited, full 16-object pilot readiness record')
    role='pilot' if args.pilot else 'runs'
    lock=study/(role+'.lock')
    # OS process exit closes the exclusive lock on Windows, including interruption.
    lock.parent.mkdir(parents=True,exist_ok=True)
    import msvcrt
    lock_handle=lock.open('a+b'); lock_handle.seek(0); lock_handle.write(b'0'); lock_handle.flush(); lock_handle.seek(0)
    try: msvcrt.locking(lock_handle.fileno(),msvcrt.LK_NBLCK,1)
    except OSError: raise RuntimeError('Another coordinator is already running this phase')
    jobs=[(c,protocol['pilot_seed']) for c in ['baseline','proposed']] if args.pilot else [
        (c,seed) for c in ['baseline','proposed'] for seed in protocol['conditions'][c]['seeds']]
    random.Random(protocol['schedule_order_seed']).shuffle(jobs)
    log=study/(role+'_coordinator.json')
    state=dict(pid=os.getpid(),phase=role,status='running',planned=len(jobs),completed=0,errors=[],
               workers=args.workers,started_unix=time.time(),active=[],order=jobs)
    write_json(log,state)
    worker=study/'harness/experiment_worker.py'
    environment=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONIOENCODING='utf-8',PYTHONHASHSEED='0')

    def execute(condition,seed,generation=False):
        output=study/'scenarios'/f'seed{seed}' if generation else study/role/condition/f'seed{seed}'
        final=output/('scenario.json' if generation else 'result.json')
        if final.exists():
            if not generation and (output/'error.json').exists():
                return dict(condition=condition,seed=seed,returncode=-1,error='Existing worker error; inspect retained evidence')
            return dict(condition=condition,seed=seed,returncode=0,resumed=True)
        output.mkdir(parents=True,exist_ok=True)
        # Never append a restarted trial's measurements into an interrupted attempt.
        if not generation and any(output.glob('*real_trials.csv.gz')):
            return dict(condition=condition,seed=seed,returncode=-1,error='Interrupted raw evidence exists; review before resuming')
        command=[sys.executable,'-X','utf8','-B',str(worker),'--study',str(study),'--condition',condition,'--seed',str(seed)]
        if generation: command+=['--generate']
        if args.pilot: command+=['--pilot']
        if args.limit: command+=['--limit',str(args.limit)]
        with (output/'console.txt').open('w',encoding='utf-8') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=environment)
        return dict(condition=condition,seed=seed,returncode=result.returncode)

    try:
        unique=sorted(set(seed for _,seed in jobs))
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for future in as_completed([pool.submit(execute,'proposed',seed,True) for seed in unique]):
                result=future.result()
                if result['returncode']: state['errors'].append(result)
        if state['errors']: raise RuntimeError('Scenario generation failed; no seeds substituted')
        pending=[]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending={pool.submit(execute,c,seed):(c,seed) for c,seed in jobs}
            for future in as_completed(pending):
                result=future.result()
                if result['returncode']: state['errors'].append(result)
                else: state['completed']+=1
                state['last_result']=result
                write_json(log,state)
                print(json.dumps({k:state[k] for k in ['phase','completed','planned','last_result']}),flush=True)
        state['status']='needs_attention' if state['errors'] else 'completed'
    except BaseException as error:
        state['status']='needs_attention'; state['coordinator_error']=repr(error)
        raise
    finally:
        state['updated_unix']=time.time(); write_json(log,state)
        lock_handle.close()
    if state['status']=='completed':
        command=[sys.executable,'-X','utf8','-B',str(study/'harness/analyze_experiment.py'),'--study',str(study)]
        if args.pilot: command+=['--pilot']
        audited=subprocess.run(command,env=environment)
        if audited.returncode:
            state['status']='needs_attention'; state['analysis_error']=audited.returncode
            write_json(log,state); raise SystemExit(audited.returncode)
    else: raise SystemExit(1)


if __name__=='__main__': main()
