"""Freeze sources, physics/assets, instrumentation and protocol before held-out runs."""
from pathlib import Path
import argparse
from datetime import datetime, timezone, timedelta
import importlib.util
import shutil
import sys

from experiment_core import sha,write_json

ROOT=Path(__file__).resolve().parents[1]


def prepare(output,pilot_from=None):
    output=Path(output).resolve()
    if output.exists(): raise FileExistsError('Use a new study directory; existing evidence is preserved')
    baseline=ROOT/'analytics/reliability/baseline_seed0_v2/sources'
    if not baseline.is_dir(): raise FileNotFoundError('Historical baseline snapshot is missing')
    output.mkdir(parents=True)
    for condition,source in [('baseline',baseline),('proposed',ROOT/'src')]:
        destination=output/'variants'/condition/'src'; destination.mkdir(parents=True)
        for path in source.glob('*.py'): shutil.copyfile(path,destination/path.name)
    shutil.copytree(ROOT/'models',output/'task/models')
    # The logger's initial metadata reads this common source directory; it then
    # records the actual condition-specific source hashes before the first step.
    shutil.copytree(output/'variants/proposed/src',output/'task/src')
    spec=importlib.util.spec_from_file_location('study_task_config',ROOT/'src/config.py')
    config=importlib.util.module_from_spec(spec); spec.loader.exec_module(config)
    keys=['SPAWN','SPAWN_JITTER_YAW','CATEGORY_OF_TYPE','TYPE_PROTOTYPES','CATEGORY_TO_ZONE','ZONES']
    task={key:getattr(config,key) for key in keys}
    write_json(output/'task.json',task)
    shared=output/'shared'; shared.mkdir()
    template=(ROOT/'src/telemetry.py').read_text(encoding='utf-8')
    assert template.count("condition='proposed'")==2
    assert template.count("self.seed,'proposed'")==1
    assert template.count('*d.ctrl,*d.actuator_force]')==1
    template=template.replace("condition='proposed'","condition=self.condition")
    template=template.replace("self.seed,'proposed'","self.seed,self.condition")
    template=template.replace('*d.ctrl,*d.actuator_force]',
                              '*d.ctrl,*d.actuator_force]+self.extra_values(system,valid)')
    (shared/'measurement_base.py').write_text(template,encoding='utf-8')
    harness=output/'harness'; harness.mkdir()
    for name in ['experiment_core.py','experiment_worker.py','run_experiment.py','analyze_experiment.py']:
        shutil.copyfile(ROOT/'tools'/name,harness/name)
    validation=None
    if pilot_from is not None:
        import json
        pilot_from=Path(pilot_from).resolve()
        report_path=pilot_from/'pilot_analysis/analysis.json'
        report=json.loads(report_path.read_text())
        proposed=[r for r in report['runs'] if r['condition']=='proposed']
        if not report['complete'] or len(proposed)!=1 or proposed[0]['correct_placements']!=16 or proposed[0]['collision_events']!=0:
            raise ValueError('Pilot readiness gate failed; retain evidence and repair before final experiment')
        pilot_protocol=json.loads((pilot_from/'protocol.json').read_text())
        from experiment_core import verify_bundle
        verify_bundle(pilot_from,pilot_protocol)
        for path in (ROOT/'src').glob('*.py'):
            if sha(path)!=sha(pilot_from/'variants/proposed/src'/path.name):
                raise ValueError('Controller changed since the validated pilot: '+path.name)
        for path in (ROOT/'models').rglob('*'):
            if path.is_file() and sha(path)!=sha(pilot_from/'task/models'/path.relative_to(ROOT/'models')):
                raise ValueError('Physics/assets changed since pilot')
        write_json(output/'validation_pilot.json',report)
        validation=dict(passed=True,source_study=str(pilot_from),
                        source_report_sha256=sha(report_path),
                        copied_report='validation_pilot.json',
                        scope='Same controller/task physics; final instrumentation logs robot state plus target rather than all clutter state')
    protocol=dict(
        title='Group 07: pre-reliability vs revised autonomous hospital decluttering',
        prepared_at_ist=datetime.now(timezone(timedelta(hours=5,minutes=30))).isoformat(),
        requirement='Dossier N=50; guide minimum N>=30 each, two-sided Welch t-test, Cohen d and 95% CI',
        conditions={
            'baseline':dict(source='Historical baseline_seed0_v2 source, before reliability repairs',seeds=list(range(1000,1050))),
            'proposed':dict(source='Current revised controller plus shared slipper task extension',seeds=list(range(2000,2050)))},
        pilot_seed=9010,
        design='Independent seed sets, 50 trials per condition; no seeds used in development; equal scene distribution',
        horizon_s=1800.,alpha=.05,
        primary_metric='restricted_completion_time_s: mission termination time when all 16 physical placements are correct; otherwise 1800 s',
        primary_direction='Lower is better; failures at early exhaustion/safe stop/horizon remain in the primary outcome',
        secondary_metrics=['correct placement fraction','complete-room success','reach/lift tracking RMSE',
                           'per-actuator force-squared effort','unexpected contact episodes','grasp success by physical type',
                           'navigation cross-track RMSE','pickup docking error'],
        tracking_reference='Controller-generated rate-limited lift/extension setpoint path transformed by calibrated top-down kinematics into the current base frame; logged command is the one applied over the sampled physics step. RMSE only PREGRASP/DESCEND/LIFT with top-down wrist validity; not a globally preplanned six-dimensional trajectory.',
        scenario_distribution=dict(spawn=task['SPAWN'],yaw='Uniform[-pi,pi]',
            acceptance='Shared frozen revised geometric reachability/support/overlap validator, minimum two approach candidates and 1.5 s settling; no runtime task outcomes used to accept/reject scenarios',
            friction='Fixed MJCF values for both conditions; no random friction or mass changes',
            base_pose=list(config.START_POSE),objects=16,
            caveat='The acceptance rule is based on the revised geometric checker, not an unbiased sample of arbitrary hospital layouts'),
        object_scope='16 rigid objects including cups, bottles, box proxies for crumpled paper, and a 230 x 84 x 60 mm, 120 g rigid slipper box with noncolliding visual sole/upper. No cloth or footwear deformation model.',
        shared_instrumentation=[
            'Same immutable MJCF/assets, 500 Hz physics, 50 Hz controller and task/category knowledge',
            'Initial full integration state generated once per seed with revised geometric feasibility checker, restored only before time zero',
            'Same orientation-aware final containment evaluator, 5 mm compliance tolerance',
            'Same contact observer at 500 Hz; only floor/intended finger-target/support handling excluded; one-second episode gap',
            'Historical contact counters disabled; no autonomy motion method modified by the measurement harness',
            'Carry-drop calls counted once consistently; archived source remains unchanged',
            '500 Hz lossless gzip CSV includes all robot qpos/qvel, current target position/velocity, arm reference/errors, actuator commands/forces and state/event linkage; full scene states saved before and after trials',
            'PYTHONHASHSEED=0 and one native BLAS thread per worker; classification-vote ties resolved alphabetically'],
        analysis=dict(test='Independent two-sided Welch t-test, baseline minus proposed',
                      effect='Cohen d using pooled sample SD; positive favours proposed for completion time',
                      ci='Welch-Satterthwaite 95% CI for mean baseline-minus-proposed difference',
                      missing='Infrastructure errors/incomplete runs block final inferential reporting; never silently discard or substitute seeds',
                      autonomous_failures='Kept with primary value 1800 s; success and failure states reported separately',
                      zero_variance='Undefined t/CI/effect sizes reported explicitly, not replaced with invented values'),
        limitations=['Simulation-instance/ray perception, known catalogue, simulator pose and final-state verification',
                     'Runtime-derived commanded arm path; no six-dimensional global trajectory accuracy claim',
                     'Force and torque squared integrals stay per channel, with units; not electrical energy',
                     'Development and pilot runs excluded; no significance promised; broadened room may fail'],
        schedule_order_seed=73921,
        validation_pilot=validation,
        frozen_sha256={})
    protocol['frozen_sha256']={p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output/'protocol.json',protocol)
    print(output)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--pilot-from',type=Path)
    args=parser.parse_args(); prepare(args.output,args.pilot_from)
