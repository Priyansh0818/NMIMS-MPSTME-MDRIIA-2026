# Group 07 hospital care support robot

A MuJoCo mobile manipulator sorts 16 rigid clutter objects in a hospital-room
scene. The accompanying CSBS model separates staff capacity, elapsed room time
and cash expenditure. This repository contains simulated evidence, not a clinical
deployment or measured hospital benefit.

## Install and run

From this group folder, create a fresh environment and install the tested packages:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then open START_CAPSTONE.cmd for the robot, START_BUSINESS.cmd for the final
business dashboard, or START_FAILURE_DEMO.cmd for the separately reproduced
seed-2011 SAFE_STOP example. Launchers prefer this folder's .venv when present.
The failure demonstration is separate from the 100 reported trials.

Viewer controls: C changes camera, O toggles cinematic movement, D toggles
diagnostics, Space pauses/resumes, and 1/2/3 select half/normal/double speed.
New live-demo logs are kept outside the submitted frozen evidence and ignored by Git.

## Files

| Folder | Contents |
| --- | --- |
| src/ and models/ | Runnable controller, robot, physical room and imported visual meshes |
| analytics/ | Business scripts/dashboard, summary tables and complete measured CSV export |
| experiments/assessment_final_v1/ | Frozen protocol, baseline/proposed sources, scenarios, audit report and run support records |
| docs/final_evidence/ | Final statistical report, plots and provenance |
| docs/business_final/ | Final business assumptions, calculations and sensitivity plots |
| docs/ | Word/PDF dossier, recording guide, work allocation and viva notes |
| tests/ and tools/ | Calculation, export, geometry and development checks/helpers |

## Actual results

50 baseline and 50 proposed runs were audited. Fully cleared rooms: 0/50 and
28/50 respectively. Failures remain in the analysis under the prespecified
1800-second restricted-time rule. See docs/final_evidence/FINAL_RESULTS.md.
Business revision, 30 October 2026: the conditional partial-cleanup case releases
0.525 staff-hours/day, with 7.81% cash NCRI and 44.54-month simple payback. This
assumes 15 rooms/day, a 12-hour dispatch window, inspection and equal manual effort
per unresolved object, and 100% of released labour value actually avoiding spending.
These are unvalidated deployment assumptions, not measured profit. Elapsed room
readiness remains slower (26.59 versus 15.20 minutes). At 75% cash realization,
payback is 79.83 months; at 0%, there is no finite payback. The original conservative
7.5-room/day, full-redo, no-cash-realization case is retained in
analytics/business_inputs_conservative.json and docs/business_conservative/.
See docs/BUSINESS_REVISION_VIVA.md for the unchanged-video explanation.

## Measured data and reproduction

analytics/submission_trials/ includes every recorded 500 Hz row for all 100
reported runs, with selected original measured columns and lossless gzip CSV
compression. No rows were removed, rounded or downsampled. Force, pose/reference,
contact and state/event evidence reproduces the reported metrics. The manifest
maps shards to source hashes; support records retain final states and events.
Verbose joint diagnostics and interrupted attempts remain in the local archive.
Their omission is documented; the reduced export does not support every possible
future diagnostic analysis.

The export was independently verified for every run. To repeat that substantial
data check (it reads the whole dataset), run from this folder:

```powershell
.\.venv\Scripts\python.exe -B analytics/reproduce_submission_metrics.py --verify-only --export-dir analytics/submission_trials
```

The frozen bundle must retain its bytes; .gitattributes prevents Git from changing
line endings. Keep that file when copying into the course repository.
Historical integration notes and the small pilot fixture describe development;
they do not replace the final 100-run report.

To re-verify every submitted CSV run and rebuild the comparison/tracking figures:

```powershell
.\.venv\Scripts\python.exe -B tools/rebuild_submission_figures.py --verify
```

Omitting --verify reuses the saved all-run CSV verification, checks its primary
metrics against the audited report and reads the actual two example-run CSVs.
That quick rebuild was checked against the reported statistics. It does not
repeat a full audit of every measurement file. Output is docs/rebuilt_figures/.

## Dossier and submission status

The team's supplied Word dossier and its matching eight-page PDF are in docs/.
All three supplied signatures are present. The corrected local showcase is
03:23.73 (203.73 seconds). Its MP4 is included at the project root as
Group_07_Hospital_Decluttering_Final.mp4. The team supplied the replacement
LinkedIn post: https://lnkd.in/p/diSXTY-2. The dossier records this URL. The video
retains the original conservative business case; the later conditional scenario
is documented separately for the live demo/viva.

The supplied dossier still labels personal and peer-review entries provisional;
Group 01's timestamp is 01:15, as supplied by the team. Individual historical authorship,
original AI-tool attribution and proposed FMEA ratings still request confirmation.
Preserve those qualifications when assessing this submission. The team's entered
commit-share values are declarations, not independently verified Git statistics.

Each member must make genuine commits from their own account and turn in the
required files personally on Teams. Faculty requested the full project there as
well; a smaller Teams package excludes the large CSVs, which are included here.

This is the contents of the assigned course group folder. Do not nest a second
capstone/ or delivery/ folder inside it. See docs/GITHUB_PUSH_GUIDE.md for the
upload sequence and docs/ASSET_PROVENANCE.md for asset origins.
