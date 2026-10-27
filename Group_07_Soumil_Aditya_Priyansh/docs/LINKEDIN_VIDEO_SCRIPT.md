# Group 07 LinkedIn video script

Target 3 minutes 45 seconds, leaving 15 seconds of headroom. Rehearse with a
timer; the final recording must be 3–4 minutes. Only read the SAY paragraphs.
SHOW and DO are instructions for the person operating the shared screen.
All three members remain visible in webcam picture-in-picture during screen
sharing. No slides. Agree on one screen operator so speakers do not compete
to switch windows.

Team roles updated 27 October 2026: Priyansh — robotics systems; Aditya — navigation/vision and
telemetry QA; Soumil — CSBS business analysis. Speaking allocation is not proof
of historical code authorship. The closing uses three verified errors in the
preserved early economics draft. Its exact AI-tool/conversation attribution is
unconfirmed, so the spoken text calls it "the draft". Do not name an AI tool or
claim personal discovery without checking the original conversation.

## Prepare the screens

Use this prepared group folder, not the 45 GB working directory:

`D:\P\NMIMS-MPSTME-MDRIIA-2026\Group_07_Soumil_Aditya_Priyansh\delivery\Group_07_Soumil_Aditya_Priyansh`

All paths below are relative to that prepared folder. Open these windows BEFORE
recording; do not spend video time finding files:

1. START_CAPSTONE.cmd — normal live 16-object assessment scene. Choose a wide
   view with C, turn orbit off with O if it is moving, then pause with Space.
   During rehearsal, learn which C view clearly shows the arm and object.
2. START_FAILURE_DEMO.cmd — separate seed-2011 demonstration. Let it reach
   SAFE_STOP and keep it open. Introduce it explicitly as a separate failure case.
3. Open docs/final_evidence/task_results.png in one image-viewer window and
   docs/final_evidence/proposed_tracking.png in another. Fit each whole image
   to the window while keeping labels readable.
4. START_BUSINESS.cmd — final business dashboard. Use its Reset button before
   stating the default numbers. Practise the attendance slider and queue graph.

Record a 15-second test to check voices, readable screens and all webcams.
Hide private windows and notifications; do not show SAP IDs or the dossier roster.
The live segment need not clean all 16 objects during this short recording.

Keep a small webcam strip visible without covering the robot's FSM status,
graph labels or dashboard values. Practise switching between the prepared
windows with Alt+Tab. Check the chosen screen-sharing mode captures each window
switch; sharing only one application can leave viewers on the wrong screen.

### Screen operator's quick sequence


| Time | Shared screen | Operator action |
| --- | --- | --- |
| 0:00–0:20 | All three webcams | Priyansh introduces himself/robotics role, then Soumil/business, then Aditya/navigation and telemetry |
| 0:20–0:40 | Normal MuJoCo viewer, wide room view | Resume with Space; show room and moving robot |
| 0:40–1:00 | Same live viewer, closer robot view | Use C to show the base/arm; leave the FSM status readable |
| 1:00–1:22 | Normal live viewer, arm/object view | Show whatever handling is actually occurring; avoid rapid camera changes |
| 1:22–1:40 | Separate failure-demo viewer | Show SAFE_STOP and the retained payload; identify this as another case |
| 1:40–1:50 | task_results.png | Point to baseline/proposed success bars, 0 versus 0.56 |
| 1:50–2:00 | proposed_tracking.png | Point to Command reference and Measured lines |
| 2:00–2:20 | task_results.png | Point to the left completion-time distributions while Soumil explains inference |
| 2:20–2:32 | Business dashboard, top cards and upper graphs | Show default 0.150 staff-hours/day, -10.0% NCRI and No finite payback |
| 2:32–2:42 | Dashboard attendance control and staff-capacity graph | Move Robot time attended from 5% to around 20%; let the results update |
| 2:42–2:50 | Dashboard, Illustrative queue delay graph | Point to the manual grey and assisted teal curves |
| 2:50–3:00 | Dashboard, Failure modes and controls table | Scroll to Payload slips during lift or carry and its proposed controls |
| 3:00–3:15 | All three webcams | Priyansh speaks |
| 3:15–3:30 | All three webcams | Aditya speaks |
| 3:30–3:45 | All three webcams | Soumil speaks; end recording after his sentence |

The dashboard shows NCRI as -10.0%; the spoken ratio -0.10 is the same value.
The tracking picture is one preselected example run, displayed at 5 Hz for
readability; the underlying measured data were recorded at 500 Hz. The reported
mean RMSE comes from all 50 proposed runs, not just the pictured trace.
The task-results plot shows distributions and success fractions; the spoken
confidence interval, p-value and Cohen's d are verified in FINAL_RESULTS.md.

## 0:00–0:20 All three members — introductions and roles

**SHOW:** All three webcams. Do not share files yet.

**DO:** Speak in this order: Priyansh, Soumil, then Aditya. Each member looks at
the camera. Keep names and roles brief so the live demo begins at 0:20.

**SAY — Priyansh, approximately 0:00–0:08:**

Hi, I'm Priyansh, our Lead Robotics Systems Architect, responsible for robot
integration and control.

**SAY — Soumil, approximately 0:08–0:14:**

I'm Soumil, the Business Analyst, covering costs, payback and operational impact.

**SAY — Aditya, approximately 0:14–0:20:**

I'm Aditya, responsible for navigation, vision checks and telemetry validation.

## 0:20–1:00 Priyansh — live viewer with webcams

**SHOW:** The NORMAL MuJoCo viewer with all webcams visible.

**DO:** Resume with Space. Start wide, then switch once to a clear robot/arm
view with C. Keep the FSM text visible. If the robot is still navigating,
describe the handling process generally rather than claiming a grasp is happening.

**SAY:**

Our Group Seven project asks: can a simulated mobile manipulator help hospital
staff clear patient-room clutter? This room contains sixteen rigid task objects,
including cups, bottles, a slipper and paper proxies. Here, the base approaches
an object and the arm attempts to grasp, lift and sort it. The state machine
coordinates these stages. Physics runs every two milliseconds, with measurements
at five hundred hertz. Decorative meshes and physical collision shapes are
separate. Real hospital performance still needs testing.

## 1:00–1:40 Aditya — handling, then separate failure viewer

**SHOW:** Normal robot handling until about 1:22; then the SEPARATE failure viewer.

**DO:** Choose an arm/object view. Switch to the failure window exactly when
Aditya says "Now we are switching to a separate failure case." Leave SAFE_STOP
and the held object visible. Do not wait for a specific object to be grasped
on cue or pretend this stopped case is the continuation of the successful run.

**SAY:**

For grasping, the robot estimates an approach and checks the result through
closed-loop observations. The slipper also needs an orientation-aware grasp.
After release, placement is checked again once the tool withdraws. Now we are
switching to a separate failure case. When safe delivery cannot be completed, the
controller enters SAFE_STOP and retains the payload. This run is unsuccessful.
We keep autonomous failures in our evaluation
instead of counting only successful demonstrations.

## 1:40–2:00 Aditya — result and tracking plots

**SHOW:** task_results.png first, then proposed_tracking.png.

**DO:** Point at the right success-rate panel while saying zero and twenty-eight.
Switch to the tracking plot when saying "tracking error"; point to its legend.
Use the actual image files, not screenshots of spreadsheet cells or dossier pages.

**SAY:**

We tested fifty independent runs for each controller version. The baseline
completely cleared zero rooms; the revised controller cleared twenty-eight.
Revised reach-and-lift tracking error was about five-point-one-five centimetres.
Unsuccessful rooms receive the prespecified eighteen-hundred-second completion
penalty, so they remain represented in this comparison.

## 2:00–2:20 Soumil — primary result plot

**SHOW:** Return to task_results.png with webcams visible.

**DO:** Point to the LEFT panel: baseline and proposed restricted completion
times. Keep the entire plot readable. No extra window is required for the
p-value; Soumil states the verified inference aloud.

**SAY:**

The mean restricted completion score improved by four hundred fifty-seven
seconds. The ninety-five-percent confidence interval is approximately three
hundred forty to five hundred seventy-four seconds. Welch's p-value is about
three-point-three-nine times ten to minus ten, with Cohen's d of one-point-five-seven.
This measures simulation performance.

## 2:20–3:00 Soumil — business dashboard and sensitivity graphs

**SHOW:** The live business dashboard, not its HTML source or a terminal.

**DO:** Start with defaults: click Reset assumptions BEFORE the quoted default
numbers. Show the three cards and cash-sensitivity plots. At "attendance slider",
move Robot time attended from 5% to about 20% and point to Attendance and staff
capacity. At "queue graph", show Illustrative queue delay. At "FMEA risk", scroll
to Failure modes and controls and point to the payload-slip row. After the
segment, reset assumptions off camera. The graph is a scenario, not a measured
hospital forecast. Keep the visibly labelled assumptions in the recording.

**SAY:**

Our business model combines measured robot performance with labelled workflow
and cost assumptions. At the defaults, it reallocates about nine staff-minutes
daily, but cash NCRI is minus zero-point-one, with no finite payback. Moving the
attendance slider shows how supervision changes the result. The queue graph
also shows that automation can increase waiting. Our highest initial FMEA risk
is payload slipping; proposed controls include retained grip and load checks.
Time released does not automatically reduce payroll.

## 3:00–3:15 Priyansh — webcams

**SHOW:** Return to the all-member webcam layout; stop sharing if needed.

**DO:** Priyansh looks at the camera. Keep the other members visible.

**SAY:**

My role covers robot integration. The draft assumed a two-point-one-minute
clearing time; we checked recorded trial timings and replaced it. My takeaway
is to measure performance before making claims.

## 3:15–3:30 Aditya — webcams

**SHOW:** Keep the same webcam layout; no window changes.

**DO:** Aditya speaks. Do not show the old business source or personal IDs.

**SAY:**

My role covers sensing and telemetry checks. The draft assumed thirty-five
percent less disinfection time. Our simulation only tests decluttering, so we
removed that reduction. Simulation scope limits what we can claim.

## 3:30–3:45 Soumil — webcams

**SHOW:** Keep all three webcams visible through the final sentence.

**DO:** Soumil speaks, pause briefly, then stop the recording. No extra
outro slide or long music segment is needed.

**SAY:**

My role covers business analysis. The draft omitted remaining staff costs when
predicting payback. Our corrected default scenario has no finite payback.
Staff time released does not automatically become cash savings.

## Evidence for the closing statements

- Timing: preserved capstone/reference/legacy_nosocomial_turnover_economics.py.txt,
  line 20, sets t_clutter_clearing_robot=2.1 without telemetry. The current final
  business report reads audited measured timing and success probability. Its
  expected attempt time is 14.200 minutes, including failures, not a measured
  full-room clearing time for every run. Keep these quantities distinct.
- Cleaning scope: the same draft, line 22, multiplies residual disinfection time
  by 0.65. A rigid-body decluttering simulation does not measure that clinical
  process. The corrected model keeps the assumed residual cleaning unchanged.
- Costs: draft lines 37–45 compare robot maintenance/energy alone against the
  complete manual baseline and predict about 9.7 months' payback. The corrected
  model retains residual staff work and separates reallocation from cash savings.
  Its default cash cost ratio is 1.10, NCRI is -0.10 and payback is not finite.
- The above checks establish technical errors in a real preserved draft. They
  do not establish which AI tool wrote it or who personally caught each error.
  Confirm the original AI attribution before presenting these as AI-generated
  errors for the guide's AI-use requirement and dossier Section 5.1.

## After recording

- Contribution lines describe the team's assigned responsibilities, retaining
  the team roles assigned on 27 October. Each member should review the corresponding files before
  recording. Actual hours, past authorship and personal experiences are not inferred.
- Review the three technical corrections and their evidence. Confirm the original
  AI-tool attribution separately; it remains pending in the dossier.
- Replay and confirm 3:00–4:00, every member visible and speaking, readable
  simulation/results/business sensitivity graphs, audible voices and no slides.
- Upload the video natively to LinkedIn, one post per group. Tag teammates,
  MPSTME and Dr Sunny Nanade and link the course Group 07 folder.
- Enter the actual published URL and duration in dossier Section 5. Update the
  Word document and exported PDF before the final documentation commit.

Source: supplied MDRIIA LinkedIn & GitHub Showcase Guide, Sections 6–8, and
docs/final_evidence/FINAL_RESULTS.md plus docs/business_final/BUSINESS_REPORT.md.
