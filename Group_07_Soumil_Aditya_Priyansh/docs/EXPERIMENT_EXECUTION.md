# Experiment execution - 21 October 2026

SAP status: the user confirmed the IDs are correct. Use the team's verified
records when filling the final dossier.

Completed preparation:

- Added a separate 16-object assessment scene including the requested slipper.
- Fixed rotated-slipper grasp selection using the observed depth-point long axis.
- Passed 25 regression tests, including the three isolated slipper rotations.
  Transcript: `assessment_regression_results.txt`.
- Ran a measured two-second pipeline smoke test for both frozen conditions.
  Both 500 Hz raw logs passed audit. These are smoke tests, not outcome results.
- Froze the full pilot in `../experiments/assessment_v1/` and launched both
  baseline/proposed on the same saved scene (seed 9010).
- Started the finite local continuation job `tools/advance_experiment.py`.

Current machine-readable stage: **`EXPERIMENT_STATUS.json`**. Check it rather
than assuming the final trials have started or completed. Detailed live pilot
progress is in `../experiments/assessment_v1/pilot/{baseline,proposed}/seed9010/status.json`.

The continuation job waits for the complete full-pilot raw audit. It requires
the proposed pilot to end with 16 correct physical placements and zero recorded
unexpected contacts. If the pilot fails or any source/physics files change,
it stops with `needs_attention`; it preserves the failure for investigation.

After this gate, it freezes `../experiments/assessment_final_v1/`, retaining a
hash-linked copy of the audited full-pilot evidence. The final logging schema
keeps all robot joint state plus target state at 500 Hz, rather than logging
every unhandled object's tiny velocity fluctuations. Full initial/final scene
states remain saved. This reduces storage without thinning time samples or
discarding force/reference data. A second actual-physics smoke test checks the
final schema before starting the final trials.

The final batch schedules **50 baseline seeds 1000-1049 and 50 proposed seeds
2000-2049**, with independent seed sets and two local workers. It retains
unsuccessful missions and automatically runs the raw-data audit/statistical
analysis after all scheduled processes finish. A failed or interrupted worker
blocks final inferential reporting. Pilot/development seeds never count toward N.

The final batch has not been completed just because these scripts exist.
`EXPERIMENT_STATUS.json` must say `complete`, and the final
`analysis/analysis.json` must say `inferential_ready: true`, before using its
statistics in the dossier or business model. Worker/coordinator console logs are
preserved, and every run has its own status file and measurement manifest.

This is local computation. Keep the computer awake and the project drive
available while it runs.

## Manual commands if a process stops

Inspect the recorded error before retrying; preserve partial raw logs.
Completed final runs can be reused by the frozen coordinator:

```powershell
python -X utf8 -B capstone/experiments/assessment_final_v1/harness/run_experiment.py --study capstone/experiments/assessment_final_v1 --workers 2
```

If no final folder exists yet, resolve the pilot/source issue before using a new
final study folder. `prepare_experiment.py --pilot-from` enforces the readiness
record and source/asset identity. Preserve frozen studies when making corrections.

The matched full pilot and its raw audit have now passed. The proposed controller
placed 16/16 objects, with zero carry drops or recorded unexpected contacts in
922.68 simulated seconds. The baseline ended with 9/16 physically placed objects
and seven contact episodes. These are one-pilot results, not final N=50 evidence.

The root launcher now opens the validated 16-object assessment scene.
`START_CAPSTONE.cmd --scene nova` selects the preserved 15-object room; its
earlier reliability report remains historical evidence.
