# Controlled experiment protocol - 21 October 2026

The supplied guide requires at least 30 runs per condition. The Group 07 dossier
specifies N=50 and cups, bottles, slippers and crumpled paper, so the target is
**50 baseline + 50 proposed trials**. Development and pilot runs do not count.

## Task extension before freezing

The preserved Nova scene contains 15 objects. The new, separate
`models/hospital_assessment.xml` adds `slipper_1`, for **16 total**. Its
authoritative rigid collision box is 230 x 84 x 60 mm, mass 120 g, friction
1.0 / 0.01 / 0.001. Noncolliding sole, upper and footbed geoms give it a slipper
appearance. This is a rigid grasping proxy, not a deformable footwear model.
Cups/bottles are rigid cylinders; existing paper is a rigid box proxy for
crumpled paper. These simplifications must be disclosed in the dossier.

The slipper is sensed/classified by the existing simulated depth/instance and
colour pipeline and returned to the personal-item tray. Its floor position is
uniform in x=[0.72,0.95], y=[-0.65,-0.43] m, with random yaw. A depth-point PCA
estimates its long axis. The revised planner chooses grasps across its short
axis, and a wrist observation can reject a misaligned approach. It does not
read the simulator's slipper orientation for this planning decision.

Initial component tests exposed a rotated-slipper grasp failure. The revised
axis-aware handling passed all three component seeds, including retained
containment after tool withdrawal. These fixtures are development tests and
are excluded from the final experiment. Full-room interactions are checked in
the pilot; isolated success alone does not validate a full 16-object clean.

The old 15-object models and checkpoint fixtures remain available for historical
reliability evidence. Their old source hash does not validate this new task.

## Comparison and reproducibility

`tools/prepare_experiment.py` freezes two source trees:

- Baseline: the actual pre-reliability source retained with `baseline_seed0_v2`.
- Proposed: the current revised controller, including the slipper extension.

Both receive the same slipper catalogue knowledge, scene geometry, physical
settings, 500 Hz physics and 50 Hz controller timing. Their motion controllers,
planning and recovery policies retain their respective frozen implementations.
All MJCF files and visual assets are copied into the study so subsequent active
project edits cannot silently change its physics. Sources, models, harness and
task inputs have SHA-256 hashes; changed frozen files stop execution.

Independent final seed sets: baseline 1000-1049 and proposed 2000-2049. Neither
set was used in the development checks. Scheduling order is shuffled with seed
73921. Seed 9010 is a matched pilot only. Scenario positions/yaw come from the
same declared distributions. Fixed friction/mass are shared; they are not
randomised. Each accepted full integration state is saved before time zero.

The common scene generator uses the frozen revised geometric feasibility,
support and overlap checker, with 1.5 s settling. This conditions the scenario
distribution on that checker; it is not an unbiased sample of arbitrary hospital
layouts. Unstable/generation-error seeds are retained as errors and block a
complete study; no seed is silently substituted. No runtime task outcome is
used to accept a scene. Loading a saved state occurs only during initialisation;
trial object motion is actuator-driven physics.

## Common measurement layer

Historical collision counters differ, so a common observer replaces both
counters at 500 Hz. Expected floor and intended finger/handled-object/support
contacts are excluded. Payload/base and other unexpected contacts count, with
a one-second contact-free gap between episodes. The observer does not issue
motion commands. Final placement is independently evaluated using the entire
orientation-aware footprint, bin floor/rim and 5 mm compliance tolerance.

Per-step CSV includes run identity, condition, seed, time, FSM state, target,
contacts, all robot qpos/qvel, current target position/velocity, end-effector position/reference/error, actuator command
and scalar force, plus reference-validity masks. The arm reference is the
controller-generated rate-limited lift/extension command path, transformed by
calibrated top-down kinematics; only PREGRASP/DESCEND/LIFT with a valid top-down
wrist contribute to tracking RMSE. The sample is logged after physics and before
the next control update, so it uses the command that was actually applied.
This measures command tracking in reach/lift phases; it is not accuracy against
a globally preplanned six-dimensional trajectory. Navigation cross-track RMSE
and successful pickup-docking errors are separate measures.

Grasp state transitions and attempts are retained, including failed attempts.
Completed grasp-cycle duration runs from PREGRASP to verified STOW; its mean is
explicitly conditional on a verified lift. Final placements per object type
include unattempted/failed objects in their denominator. Cups, bottles, slippers
and paper have their own summary rows. Squared effort is integrated separately
for every actuator with its force/torque units; channels are not added into an
unsupported energy claim.

Full scene integration state is preserved at initialisation and final state.
Per-step logging covers the entire robot rather than every unhandled object's
quaternion/velocity, avoiding unnecessary dataset growth. Raw CSV is written
with lossless gzip compression in 10,000-row parts. These remain actual CSV measurements and can be
decompressed for the course repository's `analytics/*_real_trials.csv` delivery.
Do not commit the whole model/source snapshot repeatedly or publish large raw
archives accidentally. Final curated exports, manifests and regeneration
instructions will be packaged after validation.

## Primary outcome and statistics

Horizon H=1800 simulated seconds. The primary outcome is mission termination
time if all 16 physical placements are correct; otherwise it is H. Exhausted,
safe-stop and timed-out missions remain in the comparison at H. A failed run
that stops early is not credited as a fast clean. Report physical completion
rates separately. This is a bounded, failure-penalised completion measure, not
an uncensored mean of successful cycle times or total clinical turnaround.

Use independent, two-sided Welch's t-test at alpha=.05, Cohen's d with pooled
sample SD, and Welch-Satterthwaite 95% CI for mean baseline minus proposed.
Positive time difference favours the proposed controller. Tests use trial-level
observations, never millions of physics rows as independent trials. No
significance is promised; zero-variance/undefined results are labelled explicitly.

`analyze_experiment.py` independently reads raw rows, checks finite values,
identities, cadence, hashes, force-squared integrals, contact counts and tracking
RMSE, then reloads final physical states to verify placement. All 100 scheduled
runs must be present and pass data checks before final inferential reporting.
Infrastructure errors remain visible and block reporting, rather than being
silently dropped. Genuine autonomy failures are valid measured outcomes.

## Execution

Freeze a fresh study directory only after checking the controller changes:

```powershell
python -X utf8 -B capstone/tools/prepare_experiment.py --output capstone/experiments/assessment_v1
python -X utf8 -B capstone/experiments/assessment_v1/harness/run_experiment.py --study capstone/experiments/assessment_v1 --pilot --workers 2
```

After the full pilot passes its audit, freeze the final study with that evidence,
check the final logging schema with a short pilot-only run, then launch the batch:

```powershell
python -X utf8 -B capstone/tools/prepare_experiment.py --output capstone/experiments/assessment_final_v1 --pilot-from capstone/experiments/assessment_v1
python -X utf8 -B capstone/experiments/assessment_final_v1/harness/run_experiment.py --study capstone/experiments/assessment_final_v1 --pilot --limit 2 --workers 1
python -X utf8 -B capstone/experiments/assessment_final_v1/harness/run_experiment.py --study capstone/experiments/assessment_final_v1 --workers 2
```

The coordinator uses fresh subprocesses to release native model memory. It
preserves completed runs, rejects overwrite of interrupted raw evidence and
prevents concurrent duplicate coordinators. A pilot-only shorter horizon is
available for pipeline smoke tests; those results never enter the final study.

Monitor `runs_coordinator.json`, per-run `status.json` and `console.txt`.
The already-started `advance_experiment.py` continuation performs this handoff;
do not launch duplicate coordinators. `docs/EXPERIMENT_STATUS.json` records it.
When the batch finishes, its frozen analyser audits raw logs and produces
`analysis/analysis.json`, `run_metrics.csv`, `actuator_effort.csv`,
`object_geometry_results.csv`, task box plots and first-seed tracking plots.
Incomplete results must be labelled as such. Keep this computer running while
the batch is active; processing is local, not a cloud job.
