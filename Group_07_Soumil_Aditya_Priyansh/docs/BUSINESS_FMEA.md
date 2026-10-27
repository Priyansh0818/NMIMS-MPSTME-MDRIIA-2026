# Failure modes and effects analysis

Simulation engineering and illustrative operational risk assessment, not a clinical deployment safety case.

Proposed ordinal engineering judgments; team review/sign-off pending. Scores are not measured probabilities and do not establish certification.

S/O/D each 1-10. Higher severity, occurrence and poorer detection increase RPN. Severity is held unchanged; code existence alone does not prove an occurrence reduction.

| Failure mode | Pre S/O/D; RPN | Proposed post S/O/D; RPN |
| --- | --- | --- |
| Payload slips during lift or carry | 7/6/7; 294 | 7/4/3; 84 |
| Arm/payload contacts furniture or robot base | 8/5/7; 280 | 8/4/3; 96 |
| No safe delivery pose or blocked receptacle | 5/6/6; 180 | 5/4/2; 40 |
| Misplacement is incorrectly reported as success | 7/5/7; 245 | 7/4/3; 84 |
| Room arrivals exceed service capacity | 5/4/6; 120 | 5/4/2; 40 |

## Payload slips during lift or carry

Object remains uncleared, rework and possible equipment impact.

Modest retained grip force, lift clearance, held-load checks and bounded recovery. Residual O remains nonzero; few development seeds do not establish a failure rate.

Evidence: src/controller.py: grip_force, s_nav_drop, dropped; tests/test_controller_reliability.py: lower-pressure carry regression; audited pilot reports zero carry drops.

## Arm/payload contacts furniture or robot base

Interrupted mission and potential equipment damage in the simulated task.

Check approach/drop clearances and payload height, preserve safe navigation turns, record contacts every physics step. Collision counting is detection, not proof of avoidance or an emergency-stop certification.

Evidence: src/grasp.py: candidates; src/sorting.py: plan_drop; tools/experiment_core.py: ContactAudit; payload/base contact regression.

## No safe delivery pose or blocked receptacle

Item cannot be delivered; staff intervention and delayed room readiness.

Try alternative receiving points, account for occupied zones, bound retries and retain the payload in SAFE_STOP if no safe route is available.

Evidence: src/controller.py: drop_fail; src/sorting.py: plan_drop; tests/test_controller_reliability.py: failed delivery retains payload, occupied shallow tray test.

## Misplacement is incorrectly reported as success

False room-clear status and uncompleted sorting work.

Check full object bounds, floor/rim and post-withdrawal placement. Independent final evaluation checks destinations against known simulator types. That final check uses simulator state and is not a real-world classifier safeguard.

Evidence: src/controller.py: check_withdrawal; tools/experiment_core.py: evaluate; tests/test_controller_reliability.py: footprint and misplaced-item tests.

## Room arrivals exceed service capacity

Growing queue; no finite steady-state waiting-time prediction.

Expose utilisation and reject finite M/M/c predictions when rho >= 1. Occurrence is unchanged until staffing/capacity is actually altered; no automatic service improvement is claimed.

Evidence: analytics/hospital_business.py: queue_mmc; queue stability and zero-arrival unit tests.

## Team review before submission

Agree ordinal severity/occurrence/detection anchors and review every proposed score. Reductions are engineering judgments, not measured risk reductions. Preserve severity unless the effect itself changes. Reconcile residual occurrence with the completed experiment; retain untested hazards and the need for human intervention. No clinical safety certification is claimed.
