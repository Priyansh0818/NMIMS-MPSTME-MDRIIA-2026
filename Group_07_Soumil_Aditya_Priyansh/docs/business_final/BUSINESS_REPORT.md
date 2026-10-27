# CSBS business model

Final simulated performance + unvalidated business assumptions

| Quantity | Scenario output |
| --- | --- |
| Staff hours reallocated/day | 0.150 |
| Cash cost ratio kappa | 1.100 |
| Cash NCRI | -0.100 |
| Cash payback months | No finite payback |
| Cash P_payback | No finite payback |
| Resource-value NCRI (not cash savings) | -0.021 |
| Manual / assisted elapsed minutes | 15.20 / 27.49 |

These are scenario calculations, not measured hospital savings. Positive staff reallocation is not automatically a payroll reduction. Negative NCRI means increased cost; it is not clamped to zero.

Residual cleaning/disinfection time is unchanged. No infection reduction, extra admissions or bed-revenue benefit is inferred from decluttering.

## Effective telemetry

- Report: `D:\P\NMIMS-MPSTME-MDRIIA-2026\Group_07_Soumil_Aditya_Priyansh\delivery\Group_07_Soumil_Aditya_Priyansh\experiments\assessment_final_v1\analysis\analysis.json`
- SHA-256: `7d688373b352da33646c623785383ad5af182af259acfb0a39d2afde3b1d7f79`
- Cycle basis: 14.200 minutes expected per attempt; success probability 0.560 (measured final trials).

## Inputs and provenance

| Input | Value | Unit | Status / basis |
| --- | --- | --- | --- |
| daily_rooms | 7.5 | rooms/day | assumption: Legacy ward throughput, unverified; not the separate 30-discharge hospital case. |
| operating_days | 365 | days/year | assumption: Illustrative year-round ward operation. |
| operating_hours | 8 | hours/day | assumption: Arrivals spread across an assumed eight-hour dispatch window; not observed hospital arrivals. |
| parallel_cells | 1 | paired robot/staff workcells | assumption: One dedicated robot per housekeeping service cell; c also scales capital and fixed maintenance. |
| manual_clutter_elapsed_min | 5.2 | elapsed minutes/room | assumption: Legacy starter value; no matching manual decluttering time study is available. |
| manual_clutter_staff_min | 5.2 | staff-minutes/room | assumption: Assumes one worker actively clears clutter throughout the 5.2-minute manual stage. |
| residual_elapsed_min | 10 | elapsed minutes/room | assumption: Unverified residual cleaning duration; held identical in manual and assisted cases. CDC-PROC supports retaining cleaning/disinfection scope, not this numeric duration. |
| residual_staff_min | 10 | staff-minutes/room | assumption: Unverified residual staff requirement; unchanged between cases. |
| handling_elapsed_min | 1 | elapsed minutes/room | assumption: Illustrative setup/release time outside the robot cycle. |
| handling_staff_min | 1 | staff-minutes/room | assumption: Illustrative active setup/release labour, additional to monitoring and residual work. |
| monitoring_fraction | 0.05 | fraction of robot elapsed time attended | assumption: Unvalidated 5% attendance scenario; full attendance remains available in sensitivity. Not demonstrated by MuJoCo autonomy. |
| cash_realization_fraction | 0 | fraction of released labour value converted to reduced expenditure | assumption: Conservative default: reallocated staff remain employed, so time released does not automatically reduce payroll. EFFICIENCY distinguishes cash and non-cash benefits. |
| pilot_success_probability | 0.9 | probability per robot attempt | assumption: Illustrative failure allowance while final trials run. Explicitly NOT estimated as 100% from one successful pilot. Ignored in final-data mode. |
| pilot_failure_attempt_min | 30 | elapsed minutes per failed attempt | assumption: Uses the experiment's 1800-second horizon as an illustrative upper-bound failed-cycle scenario, not a measured failed-cycle mean. Ignored in final-data mode. |
| capex_ratio_per_cell | 0.58 | reference annual labour-cost units per robot | assumption: Legacy illustrative capital ratio; not a supplier quote. No currency or validated purchase cost is claimed. |
| maintenance_ratio_per_cell_year | 0.08 | reference annual labour-cost units per robot-year | assumption: Illustrative maintenance ratio for sensitivity, not measured maintenance or a vendor estimate. |
| energy_ratio_reference_year | 0.02 | reference annual labour-cost units at reference annual throughput | assumption: Illustrative energy/consumables allowance scales with room count. MuJoCo squared actuator effort is NOT electrical energy. |
| life_years | 5 | years | assumption: Illustrative service life; not a warranty or measured robot life. |

The fixed reference cost year is {"daily_rooms": 7.5, "operating_days": 365, "staff_minutes_per_room": 15.2, "basis": "Fixed reference case inherited from the starter: 5.2 assumed clutter staff-minutes plus 10 assumed residual staff-minutes. One cost unit is that reference year's productive staff labour cost; no wage or procurement quote is asserted. Reference values stay fixed when active scenarios change."}.

## Queue interpretation

Poisson arrivals, exponential service, FCFS, identical combined robot/staff cells, infinite queue, no setup overlap; not a fitted hospital queue.
Manual rho=0.237; assisted rho=0.429. An unstable queue returns no finite steady-state wait.

## Sources checked on 21 October 2026

- **PILOT**: [Audited 16-object MuJoCo pilot, seed 9010](capstone/experiments/assessment_v1/pilot_analysis/analysis.json). One measured simulated successful clearing duration only. No human labour, clinical effect, reliability population estimate or procurement cost.
- **CDC-PROC**: [CDC Environmental Cleaning Procedures, section 4.2.3](https://www.cdc.gov/healthcare-associated-infections/hcp/cleaning-global/procedures.html). Terminal cleaning after discharge includes cleaning/disinfection beyond decluttering; those tasks remain in the model. Does not validate the 10-minute assumption.
- **EFFICIENCY**: [UK Government Efficiency Framework, sections 4.1-4.5](https://www.gov.uk/government/publications/the-government-efficiency-framework/the-government-efficiency-framework--2). Separates direct spending reductions from time/productivity benefits without a reduced budget. No UK financial rate is imported into this Indian academic scenario.
- **BARTS**: [Barts Health: How co-bots are creating a cleaner future, 29 April 2026](https://www.bartshealth.nhs.uk/news/how-cobots-are-creating-a-cleaner-future-at-barts-health-18557/). Qualitative example of cleaning staff time reallocation. Different robots/tasks; no numeric transfer to our manipulator.
- **QUEUE**: [Larson and Odoni, Urban Operations Research, section 4.6.2 (MIT-hosted text)](https://web.mit.edu/urban_or_book/www/book/chapter4/4.6.2.html). Identical exponential servers, Poisson arrivals, FCFS and infinite waiting capacity for M/M/c. These assumptions are illustrative here, not fitted to hospital data.

## What remains before final dossier use

Replace or validate assumptions with the team; confirm FMEA judgments; switch to --mode final only after all trial audits finish. A complete simulation experiment still does not measure wages, supervision, procurement cost or clinical cleaning effectiveness.

Payback is simple, undiscounted and excludes financing, tax, residual value and replacement costs. Labour value and cash-budget effects are shown separately.