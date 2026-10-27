"""Dimensionless CSBS scenario model. Business assumptions are never simulation results."""
from dataclasses import dataclass,replace,asdict
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import statistics

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_INPUTS=Path(__file__).with_name('business_inputs.json')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class Inputs:
    daily_rooms:float
    operating_days:float
    operating_hours:float
    parallel_cells:int
    manual_clutter_elapsed_min:float
    manual_clutter_staff_min:float
    residual_elapsed_min:float
    residual_staff_min:float
    handling_elapsed_min:float
    handling_staff_min:float
    monitoring_fraction:float
    cash_realization_fraction:float
    pilot_success_probability:float
    pilot_failure_attempt_min:float
    capex_ratio_per_cell:float
    maintenance_ratio_per_cell_year:float
    energy_ratio_reference_year:float
    life_years:float


@dataclass(frozen=True)
class Measurements:
    mode:str
    label:str
    trial_count:int
    successful_cycle_min:float|None
    actual_mean_attempt_min:float|None
    observed_success_probability:float|None
    provenance:dict


def load_inputs(path=DEFAULT_INPUTS):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    parameters=Inputs(**{key:record['value'] for key,record in data['inputs'].items()})
    validate(parameters,data)
    return parameters,data


def validate(p,data):
    for name,value in asdict(p).items():
        if not isinstance(value,(int,float)) or not math.isfinite(value): raise ValueError('Nonfinite input: '+name)
        lo,hi=data['inputs'][name]['bounds']
        if not lo<=value<=hi: raise ValueError(f'{name} must be in [{lo}, {hi}]')
    if int(p.parallel_cells)!=p.parallel_cells: raise ValueError('parallel_cells must be an integer')


def load_measurements(mode='pilot',study=None):
    study=Path(study) if study else ROOT/'experiments'/('assessment_v1' if mode=='pilot' else 'assessment_final_v1')
    path=study/('pilot_analysis' if mode=='pilot' else 'analysis')/'analysis.json'
    report=json.loads(path.read_text(encoding='utf-8'))
    if mode=='final' and not report.get('inferential_ready'):
        raise ValueError('Final experiment is not complete and fully audited; use explicit pilot mode for provisional work')
    if not report.get('complete') or report.get('audit_errors'): raise ValueError('Telemetry report did not pass audit')
    records=[r for r in report['runs'] if r['condition']=='proposed']
    if not records or not all(r['raw_audit_passed'] for r in records): raise ValueError('No audited proposed trials')
    successful=[r['elapsed_s']/60 for r in records if r['completion_success']]
    if mode=='pilot' and len(successful)!=1: raise ValueError('Expected the single audited complete-room pilot')
    return Measurements(mode=mode,label='PROVISIONAL: one simulation pilot + illustrative business assumptions' if mode=='pilot' else
        'Final simulated performance + unvalidated business assumptions',trial_count=len(records),
        successful_cycle_min=statistics.mean(successful) if successful else None,
        actual_mean_attempt_min=statistics.mean(r['elapsed_s']/60 for r in records) if mode=='final' else None,
        observed_success_probability=sum(r['completion_success'] for r in records)/len(records) if mode=='final' else None,
        provenance=dict(report=str(path.resolve()),sha256=sha(path),seeds=[r['seed'] for r in records],
                        raw_audit_passed=True,time_basis='MuJoCo simulated elapsed seconds / 60, never PC wall time'))


def queue_mmc(arrivals_per_hour,service_minutes,c=1):
    if arrivals_per_hour<0 or service_minutes<=0 or int(c)!=c or c<1: raise ValueError('Invalid M/M/c inputs')
    c=int(c); mu=60/service_minutes; rho=arrivals_per_hour/(c*mu)
    common=dict(lambda_per_hour=arrivals_per_hour,mu_per_hour_per_cell=mu,c=c,rho=rho)
    if rho>=1: return dict(stable=False,wait_minutes=None,system_minutes=None,wait_probability=None,**common)
    if arrivals_per_hour==0: return dict(stable=True,wait_minutes=0.,system_minutes=service_minutes,wait_probability=0.,**common)
    a=arrivals_per_hour/mu
    term=1.; total=1.
    for k in range(1,c): term*=a/k; total+=term
    tail=term*a/c/(1-rho)
    erlang_c=tail/(total+tail)
    wait=erlang_c/(c*mu-arrivals_per_hour)*60
    return dict(stable=True,wait_minutes=wait,system_minutes=wait+service_minutes,wait_probability=erlang_c,**common)


def payback(capital,annual_saving,life):
    if capital<0 or life<=0: raise ValueError('Invalid payback inputs')
    if annual_saving<=0: return dict(finite=False,years=None,months=None,P_payback=None,within_life=False)
    years=capital/annual_saving
    return dict(finite=True,years=years,months=12*years,P_payback=years/life,within_life=years<=life)


def calculate(p,reference,measurements):
    if measurements.mode=='final':
        success=measurements.observed_success_probability
        robot_min=measurements.actual_mean_attempt_min
    else:
        success=p.pilot_success_probability
        if measurements.successful_cycle_min is None: raise ValueError('Pilot success duration missing')
        robot_min=success*measurements.successful_cycle_min+(1-success)*p.pilot_failure_attempt_min
    failure=1-success
    # Staff minutes sum across workers. Elapsed time is a separate serial process.
    fallback_staff=failure*p.manual_clutter_staff_min
    fallback_elapsed=failure*p.manual_clutter_elapsed_min
    manual_staff=p.manual_clutter_staff_min+p.residual_staff_min
    assisted_staff=p.handling_staff_min+p.monitoring_fraction*robot_min+fallback_staff+p.residual_staff_min
    manual_elapsed=p.manual_clutter_elapsed_min+p.residual_elapsed_min
    assisted_elapsed=p.handling_elapsed_min+robot_min+fallback_elapsed+p.residual_elapsed_min
    annual_rooms=p.daily_rooms*p.operating_days
    reference_rooms=reference['daily_rooms']*reference['operating_days']
    reference_hours=reference_rooms*reference['staff_minutes_per_room']/60
    baseline_hours=annual_rooms*manual_staff/60
    assisted_hours=annual_rooms*assisted_staff/60
    released_hours=baseline_hours-assisted_hours
    baseline_cost=baseline_hours/reference_hours
    assisted_staff_value=assisted_hours/reference_hours
    labour_value_released=baseline_cost-assisted_staff_value
    fixed_cost=p.parallel_cells*p.maintenance_ratio_per_cell_year
    variable_cost=p.energy_ratio_reference_year*annual_rooms/reference_rooms
    nonstaff=fixed_cost+variable_cost
    capital=p.parallel_cells*p.capex_ratio_per_cell
    resource_cost=assisted_staff_value+nonstaff
    # Reallocation alone does not lower payroll. Extra required labour is costed;
    # only the chosen fraction of positive released labour is cash-releasing.
    cash_labor=baseline_cost-p.cash_realization_fraction*max(labour_value_released,0)+max(-labour_value_released,0)
    cash_cost=cash_labor+nonstaff
    cash_saving=baseline_cost-cash_cost
    resource_saving=baseline_cost-resource_cost
    operating_realization=nonstaff/labour_value_released if labour_value_released>0 else None
    lifetime_realization=(nonstaff+capital/p.life_years)/labour_value_released if labour_value_released>0 else None
    marginal_staff=(manual_staff-assisted_staff)/60/reference_hours
    marginal_cash=p.cash_realization_fraction*max(marginal_staff,0)+min(marginal_staff,0)-p.energy_ratio_reference_year/reference_rooms
    volume_break=fixed_cost/(p.operating_days*marginal_cash) if marginal_cash>0 else None
    volume_life=(fixed_cost+capital/p.life_years)/(p.operating_days*marginal_cash) if marginal_cash>0 else None
    monitoring_break=(p.manual_clutter_staff_min-p.handling_staff_min-fallback_staff)/robot_min if robot_min>0 else None
    arrival=p.daily_rooms/p.operating_hours
    return dict(
        scope='Illustrative ward scenario; simulated decluttering only; no clinical effectiveness or admission revenue claim',
        telemetry_role=measurements.label,trial_count=measurements.trial_count,
        success_probability=success,success_probability_kind='measured final trials' if measurements.mode=='final' else 'assumption, not estimated from one pilot',
        robot_attempt_min=robot_min,robot_success_cycle_min=measurements.successful_cycle_min,
        manual_staff_min=manual_staff,assisted_staff_min=assisted_staff,
        handling_staff_min=p.handling_staff_min,monitoring_staff_min=p.monitoring_fraction*robot_min,
        fallback_staff_min=fallback_staff,residual_staff_min=p.residual_staff_min,
        manual_room_ready_min=manual_elapsed,assisted_room_ready_min=assisted_elapsed,
        room_ready_change_min=manual_elapsed-assisted_elapsed,
        room_ready_reduction_fraction=(manual_elapsed-assisted_elapsed)/manual_elapsed,
        H_reclaimed_staff_hours_day=p.daily_rooms*(manual_staff-assisted_staff)/60,
        released_staff_hours_year=released_hours,
        annual_rooms=annual_rooms,reference_annual_staff_hours=reference_hours,
        baseline_annual_cost_reference_units=baseline_cost,
        capital_reference_units=capital,nonstaff_annual_cost_reference_units=nonstaff,
        fixed_maintenance_reference_units=fixed_cost,variable_energy_reference_units=variable_cost,
        assisted_staff_value_reference_units=assisted_staff_value,
        cash_annual_cost_reference_units=cash_cost,resource_annual_cost_reference_units=resource_cost,
        cash_saving_reference_units_year=cash_saving,
        kappa_cash=cash_cost/baseline_cost,NCRI_cash=1-cash_cost/baseline_cost,
        kappa_resource=resource_cost/baseline_cost,NCRI_resource=1-resource_cost/baseline_cost,
        cash_payback=payback(capital,cash_saving,p.life_years),
        resource_value_payback=payback(capital,resource_saving,p.life_years),
        break_even=dict(cash_realization_for_positive_savings=operating_realization,
                        cash_realization_for_payback_within_life=lifetime_realization,
                        daily_rooms_for_positive_cash_savings=volume_break,
                        daily_rooms_for_payback_within_life=volume_life,
                        maximum_monitoring_fraction_for_staff_time_release=monitoring_break),
        queue_manual=queue_mmc(arrival,manual_elapsed,p.parallel_cells),
        queue_assisted=queue_mmc(arrival,assisted_elapsed,p.parallel_cells),
        queue_assumptions='Poisson arrivals, exponential service, FCFS, identical combined robot/staff cells, infinite queue, no setup overlap; not a fitted hospital queue')


def sensitivity(p,data,measurements):
    rows=[]
    for field,record in data['inputs'].items():
        if measurements.mode=='final' and field in ['pilot_success_probability','pilot_failure_attempt_min']: continue
        value=getattr(p,field); lo,hi=record['bounds']
        low=max(lo,value*.7); high=min(hi,value*1.3)
        basis='one input at a time +/-30%, limited to physical bounds'
        if field=='cash_realization_fraction': low,high=0.,1.; basis='full feasible realization range [0,1]'
        if field=='parallel_cells': low,high=1,2; basis='integer capacity scenario, one vs two paired cells'
        for label,v in [('low',low),('high',high)]:
            case=replace(p,**{field:v}); validate(case,data)
            r=calculate(case,data['normalization_reference'],measurements)
            rows.append(dict(input=field,case=label,value=v,basis=basis,NCRI_cash=r['NCRI_cash'],NCRI_resource=r['NCRI_resource'],
                             P_payback_cash=r['cash_payback']['P_payback'],H_reclaimed=r['H_reclaimed_staff_hours_day']))
    return rows


def curves(p,data,m):
    realization=[]; attendance=[]; queue=[]
    for i in range(101):
        f=i/100
        r=calculate(replace(p,cash_realization_fraction=f),data['normalization_reference'],m)
        realization.append(dict(x=f,NCRI=r['NCRI_cash'],P=r['cash_payback']['P_payback']))
        a=calculate(replace(p,monitoring_fraction=f),data['normalization_reference'],m)
        attendance.append(dict(x=f,H=a['H_reclaimed_staff_hours_day'],NCRI_resource=a['NCRI_resource']))
    current=calculate(p,data['normalization_reference'],m)
    for i in range(1,101):
        arrival=i/100*p.parallel_cells*60/current['assisted_room_ready_min']*1.1
        manual=queue_mmc(arrival,current['manual_room_ready_min'],p.parallel_cells)
        assisted=queue_mmc(arrival,current['assisted_room_ready_min'],p.parallel_cells)
        queue.append(dict(arrival=arrival,manual_wait=manual['wait_minutes'],assisted_wait=assisted['wait_minutes'],
                          assisted_rho=assisted['rho']))
    return dict(realization=realization,attendance=attendance,queue=queue)


def payload(p,data,m):
    return dict(inputs=asdict(p),metadata=data,measurements=asdict(m),outputs=calculate(p,data['normalization_reference'],m),
                sensitivity=sensitivity(p,data,m),curves=curves(p,data,m))


def exports(p,data,m,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    contents=payload(p,data,m)
    (output/'business_results.json').write_text(json.dumps(contents,indent=2,allow_nan=False),encoding='utf-8')
    rows=contents['sensitivity']
    with (output/'sensitivity.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    make_figures(contents,output)
    write_report(contents,output)
    print(json.dumps(dict(role=m.label,H_reclaimed=contents['outputs']['H_reclaimed_staff_hours_day'],
                         NCRI_cash=contents['outputs']['NCRI_cash'],cash_payback=contents['outputs']['cash_payback']),indent=2))
    return contents


def make_figures(contents,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    r=contents['outputs']; c=contents['curves']; p=contents['inputs']
    banner='PROVISIONAL SCENARIO' if contents['measurements']['mode']=='pilot' else 'SIMULATION + ASSUMPTIONS'
    colour='#008c95'; orange='#ce8129'
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),layout='constrained')
    x=[v['x'] for v in c['realization']]
    axes[0].plot(x,[v['P'] if v['P'] is not None else math.nan for v in c['realization']],color=colour)
    axes[0].axhline(1,color=orange,ls='--',label='Payback within assumed life')
    paybacks=[v['P'] for v in c['realization'] if v['P'] is not None]
    if paybacks and all(value>0 for value in paybacks): axes[0].set_yscale('log')
    axes[0].set(xlabel='Fraction of released labour value becoming cash savings',ylabel='P_payback (dimensionless)',title='Cash payback; blank = no finite payback')
    axes[0].legend(fontsize=8)
    axes[1].plot(x,[v['NCRI'] for v in c['realization']],color=colour)
    axes[1].axhline(0,color=orange,ls='--'); axes[1].axvline(p['cash_realization_fraction'],color='#667b83',ls=':')
    axes[1].set(xlabel='Fraction becoming cash savings',ylabel='NCRI (negative = increased cost)',title='Cash cost sensitivity')
    fig.suptitle(banner+' | Costs and staffing assumptions are unverified')
    fig.savefig(output/'payback_sensitivity.png',dpi=170); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),layout='constrained')
    axes[0].bar(['Manual','Assisted'],[r['manual_staff_min'],r['assisted_staff_min']],color=['#7b8b93',colour])
    axes[0].set(ylabel='Active staff-minutes per room',title=f"Potential reallocation: {r['H_reclaimed_staff_hours_day']:.3f} staff-hours/day")
    axes[1].bar(['Manual','Assisted'],[r['manual_room_ready_min'],r['assisted_room_ready_min']],color=['#7b8b93',orange])
    axes[1].set(ylabel='Elapsed minutes per room',title='Sequential room-ready scenario')
    fig.suptitle(banner+' | Staff time and elapsed time are different')
    fig.savefig(output/'labour_and_elapsed.png',dpi=170); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    ax.plot([v['arrival'] for v in c['queue']],[v['manual_wait'] for v in c['queue']],label='Manual cell',color='#7b8b93')
    ax.plot([v['arrival'] for v in c['queue']],[v['assisted_wait'] if v['assisted_wait'] is not None else math.nan for v in c['queue']],label='Robot/staff cell',color=colour)
    boundary=p['parallel_cells']*60/r['assisted_room_ready_min']
    ax.axvline(boundary,color=orange,ls='--',label='Assisted stability boundary')
    ax.set(xlabel='Room arrivals per hour',ylabel='Expected queue wait (minutes)',title=banner+' | Illustrative M/M/c; no finite steady state beyond capacity')
    ax.set_yscale('log'); ax.legend(); fig.savefig(output/'queue_delay.png',dpi=170); plt.close(fig)


def write_report(contents,output):
    r=contents['outputs']; fmt=lambda x:'No finite payback' if x is None else f'{x:.3f}'
    lines=['# CSBS business model', '',contents['measurements']['label'],'',
           '| Quantity | Scenario output |','| --- | --- |',
           f"| Staff hours reallocated/day | {r['H_reclaimed_staff_hours_day']:.3f} |",
           f"| Cash cost ratio kappa | {r['kappa_cash']:.3f} |",f"| Cash NCRI | {r['NCRI_cash']:.3f} |",
           f"| Cash payback months | {fmt(r['cash_payback']['months'])} |",
           f"| Cash P_payback | {fmt(r['cash_payback']['P_payback'])} |",
           f"| Resource-value NCRI (not cash savings) | {r['NCRI_resource']:.3f} |",
           f"| Manual / assisted elapsed minutes | {r['manual_room_ready_min']:.2f} / {r['assisted_room_ready_min']:.2f} |",'',
           'These are scenario calculations, not measured hospital savings. Positive staff reallocation is not automatically a payroll reduction. Negative NCRI means increased cost; it is not clamped to zero.',
           '', 'Residual cleaning/disinfection time is unchanged. No infection reduction, extra admissions or bed-revenue benefit is inferred from decluttering.',
           '', '## Effective telemetry', '',f"- Report: `{contents['measurements']['provenance']['report']}`",
           f"- SHA-256: `{contents['measurements']['provenance']['sha256']}`",
           f"- Cycle basis: {r['robot_attempt_min']:.3f} minutes expected per attempt; success probability {r['success_probability']:.3f} ({r['success_probability_kind']}).",
           '', '## Inputs and provenance', '', '| Input | Value | Unit | Status / basis |','| --- | --- | --- | --- |']
    for name,record in contents['metadata']['inputs'].items():
        lines.append(f"| {name} | {contents['inputs'][name]} | {record['unit']} | {record['kind']}: {record['basis']} |")
    lines+=['','The fixed reference cost year is '+json.dumps(contents['metadata']['normalization_reference'])+'.',
            '', '## Queue interpretation','',r['queue_assumptions']+'.',
            f"Manual rho={r['queue_manual']['rho']:.3f}; assisted rho={r['queue_assisted']['rho']:.3f}. An unstable queue returns no finite steady-state wait.",
            '', '## Sources checked on 21 October 2026','']
    for source in contents['metadata']['sources']:
        link=source.get('url',source.get('location'))
        lines.append(f"- **{source['id']}**: [{source['title']}]({link}). {source['supports']}")
    lines+=['','## What remains before final dossier use','',
            'Replace or validate assumptions with the team; confirm FMEA judgments; switch to --mode final only after all trial audits finish. A complete simulation experiment still does not measure wages, supervision, procurement cost or clinical cleaning effectiveness.',
            '', 'Payback is simple, undiscounted and excludes financing, tax, residual value and replacement costs. Labour value and cash-budget effects are shown separately.']
    (output/'BUSINESS_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['pilot','final'],default='pilot')
    parser.add_argument('--inputs',type=Path,default=DEFAULT_INPUTS)
    parser.add_argument('--study',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/business_provisional')
    parser.add_argument('--serve',action='store_true'); parser.add_argument('--open',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args(); p,data=load_inputs(args.inputs); m=load_measurements(args.mode,args.study)
    exports(p,data,m,args.output)
    if args.serve:
        from business_server import serve
        serve(p,data,m,args.port,args.open)


if __name__=='__main__': main()
