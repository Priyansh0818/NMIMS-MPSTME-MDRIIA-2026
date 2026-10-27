# Final audited simulation results

50 independent baseline seeds and 50 independent proposed seeds; the separate pilot is excluded.

| Measure | Baseline mean ± SD | Proposed mean ± SD | Unit |
| --- | --- | --- | --- |
| restricted_completion_time_s | 1800 ± 0 | 1342.8 ± 412.49 | s |
| reach_lift_rmse_m | 0.051762 ± 0.0080588 | 0.051541 ± 0.0030074 | m |
| lift_effort_N2s | 64610 ± 22321 | 34042 ± 13165 | N²·s; lift actuator only |
| collision_events | 16.96 ± 6.318 | 0.9 ± 1.2164 | episodes/run |
| carry_drops | 0.78 ± 1.016 | 0.2 ± 0.45175 | drops/run |

baseline: 0/50 rooms fully cleared; 606/800 correct final object placements; 27,639,270 raw physics samples.

proposed: 28/50 rooms fully cleared; 663/800 correct final object placements; 21,299,720 raw physics samples.

## Primary inference

```json
{
  "available": true,
  "test": "Independent two-sided Welch t-test",
  "t": 7.837251099623215,
  "df": 49.0,
  "p": 3.391003307116647e-10,
  "ci95": [
    339.95892671474905,
    574.4170732852507
  ],
  "n_baseline": 50,
  "n_proposed": 50,
  "mean_baseline": 1800.0,
  "mean_proposed": 1342.8120000000001,
  "sd_baseline": 0.0,
  "sd_proposed": 412.4925065788147,
  "difference_baseline_minus_proposed": 457.1879999999999,
  "cohen_d": 1.5674502199246432
}
```

## Interpretation and scope

Failures remain at the prespecified 1800 s restricted completion time. Infrastructure-interrupted attempts are archived and the identical seeds were restarted; no autonomous task failures were discarded.

Tracking uses valid commanded top-down reach/lift reference samples, not a global six-dimensional planned path. Force/torque-squared integrals are reported per channel; they are not electrical energy. Cups/bottles/slipper/paper and all 16 object outcomes are retained.

The acceptance validator restricts layouts to the frozen geometric feasibility rule. Perception uses simulator ray/instance observations and a known catalogue. No real hospital performance, infection or admission-revenue claim follows.

## Business interpretation

Final simulated performance + unvalidated business assumptions

H=0.15025 staff-hours/day; cash NCRI=-0.1. Cash payback: no finite payback.

Operational and financial inputs remain unvalidated assumptions. Positive released staff capacity is not automatically reduced cash expenditure. Residual cleaning is unchanged.
