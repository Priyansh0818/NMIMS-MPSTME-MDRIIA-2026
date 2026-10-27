# Viva rehearsal notes

Use this as a study aid; explain the code and formulas in your own words.

| Question | Essential answer and evidence |
| --- | --- |
| What is simulated? | A Stretch mobile manipulator sorts 16 rigid proxy objects in a hospital scene. No soft-body slipper/paper deformation, patient interaction or clinical cleaning validation. |
| What runs at 500 Hz? | MuJoCo physics and raw measurement/contact observation at 0.002 s. FSM/actuation updates are 50 Hz; perception/status 10 Hz. These rates are distinct. |
| What controller is implemented? | Rate-limited actuator position/velocity servos, geometric top-down reach planning and a navigation lattice. Do not claim a full PID integral controller or DLS implementation merely because the starter lists those equations. |
| Why different friction/solref? | Floor, clutter and priority finger pads have separate modeled coefficients/compliance. These are design choices tested in simulation, not measured material calibration. Identify actual values in Section 2.1 and the compiled model. |
| What makes the slipper different? | Its long axis is estimated from observed depth geometry, enabling a short-axis grasp; it is a 120 g rigid proxy, not deformable footwear. |
| Is gripping equal to sorting success? | No. A verified lift can still be followed by carry drop, misclassification or incorrect destination. Final evaluator checks every full object footprint after withdrawal. |
| What if no safe delivery exists? | Bounded attempts and payload-retaining SAFE_STOP. Keep the unsuccessful outcome; do not relabel it success. |
| What is the baseline? | Frozen pre-reliability robot controller, not manual hospital cleaning. Both conditions share models, initial-condition rules and measurement definitions. |
| Why 50+50 independent seeds? | Frozen held-out comparison; seeds and distributions are recorded. Geometric acceptance biases the scenario set, which is disclosed. |
| What is the primary outcome? | Restricted full-room completion time: actual completion when all 16 are correct, otherwise the fixed 1800 s horizon. This retains autonomous failures in the comparison. |
| Why Welch? | Independent groups and no equal-variance assumption. Explain the signed mean difference, two-sided p-value and 95% interval; report actual values only after audit. |
| What does Cohen's d mean? | Mean difference divided by pooled sample SD. It expresses standardized separation, not probability that the robot works or proof of clinical benefit. |
| What is tracking RMSE? | Error against the logged commanded top-down reach/lift path in valid phases; not a globally preplanned 6D trajectory. |
| Is control effort energy? | No. Force-squared or torque-squared time integral per channel; unlike units cannot be added indiscriminately. Electrical energy is not measured. |
| Does staff time released mean cash saved? | Only if spending actually falls. The cash-realization fraction separates reallocation from expenditure reductions. |
| When is payback finite? | Only with positive annual cash savings: months=12×capital/annual saving; dimensionless P=payback years/assumed life. Nonpositive savings mean no finite payback. |
| Can NCRI be negative? | Yes: 1−assisted cash cost/baseline cost is negative when cost rises. Do not clamp unfavorable results. |
| What if queue utilization exceeds one? | No finite stationary waiting-time prediction; Poisson/exponential/FCFS assumptions are illustrative, not fitted hospital observations. |
| What does FMEA prove? | It organizes hazards and proposed controls. Scores are ordinal team judgments, not calibrated probabilities or safety certification. |
| Why were some attempts restarted? | Infrastructure interruptions were archived and identical seeds restarted. No autonomous failures were removed; full raw audits gate final statistics. |

Before the viva, each member must point to one relevant source function and one
actual raw/result record, reproduce one calculation and describe one limitation.
