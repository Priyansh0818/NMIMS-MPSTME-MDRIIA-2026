# Record the capstone video step by step

You are recording a short screen demonstration with all three members speaking
on webcam. You do not need a slide deck, animation or the entire cleaning run.
Target 3 minutes 45 seconds; the permitted length is 3–4 minutes.

## 1 Prepare before recording

1. Open the group project folder. Double-click **START_CAPSTONE.cmd**. This is
   the active capstone robot, not an old beta. Press **C** to choose a clear
   camera and **Space** to pause while you organize the recording.
2. Double-click **START_BUSINESS.cmd**. Check its banner says final simulated
   performance plus assumptions. This is your business screen.
3. Open `capstone/docs/final_evidence/task_results.png` and
   `capstone/docs/final_evidence/proposed_tracking.png`. These are the final
   audited results, not starter plots.
4. Double-click **START_FAILURE_DEMO.cmd** in a second viewer. Let it reach
   SAFE_STOP, then keep that window open for the failure explanation. The
   seed-2011 case was separately reproduced headlessly: it stops around 69.08
   simulated seconds instead of pretending the task succeeded. This extra demo
   does not add another trial to the 50+50 experiment.
5. Close private windows and hide notifications. Never show the dossier roster,
   SAP IDs, phone numbers or passwords in the public video.

## 2 Start a meeting and test the recording

Use a Teams meeting if your college account allows recording. Join with all
three members, turn cameras/microphones on and share the demonstration screen.
In Teams, use More actions → Record and transcribe → Start recording. The
recording captures audio, video and screen sharing; availability depends on the
account's permissions. Save a 15-second test first and replay it: confirm the
simulation, webcam faces and every speaker's voice are actually captured.

Official instructions:
https://support.microsoft.com/en-us/teams/meetings/start-stop-and-find-meeting-recordings-in-microsoft-teams

If the recording option is unavailable, use a recording tool/account already
available to the team or ask for help before the final take. Do not spend the
whole session troubleshooting an unsupported account. The supplied guide allows
Teams, Zoom or Meet recordings with screen share and webcams.

For the exact opening dialogue and SHOW/DO/SAY cues, use LINKEDIN_VIDEO_SCRIPT.md.

## 3 Record these screens in this order

| Time | Who speaks | What the audience sees | What to explain |
| --- | --- | --- | --- |
| 0:00–0:20 | All three | Webcams | Priyansh: Lead Robotics Systems Architect; Soumil: Business Analyst; Aditya: Navigation/Vision and Telemetry QA |
| 0:20–1:00 | Priyansh | Normal live MuJoCo viewer + webcams | Resume with Space; show navigation, changing FSM state and interaction with an object. Mention 0.002 s physics timestep. |
| 1:00–1:40 | Aditya | Grasping viewer, then separate SAFE_STOP viewer + webcams | Explain grip, lift, sorting checks and the failure stop. SAFE_STOP retains the payload when no safe delivery exists; it does not mean the room is complete. |
| 1:40–2:00 | Aditya | Actual task-results and tracking plots + webcams | 50 runs per condition; complete rooms 0/50 baseline and 28/50 proposed; unsuccessful rooms remain in the analysis |
| 2:00–2:20 | Soumil | Task-results plot + webcams | Restricted-time difference 457.19 s; 95% CI 339.96–574.42 s; Welch p≈3.39e−10. This is a failure-penalized simulation score, not measured hospital time saved. |
| 2:20–3:00 | Soumil | Business dashboard + webcams | Move attendance/cash-realization sliders. Default staff reallocation≈0.150 h/day; cash NCRI=−0.10 and no finite payback. Explain assumed queue and one FMEA risk. |
| 3:00–3:15 | Priyansh | Webcams | Actual contribution, one learning and one verified AI error |
| 3:15–3:30 | Aditya | Webcams | Actual contribution, one learning and one verified AI error |
| 3:30–3:45 | Soumil | Webcams | Actual contribution, one learning and one verified AI error |

You do not have to wait for all 16 objects to be cleaned during the recording.
The short live segment explains the mechanism; the audited plots demonstrate
the experiment. Rehearse camera switching/window changes once before recording.
If your separate failure demo differs from the tested case, stop and inspect it;
do not claim a prerecorded result is occurring live.

## 4 Simple narration to adapt

Priyansh: “We built a mobile manipulator in MuJoCo to identify and sort hospital-room
clutter. The room contains 16 rigid object proxies. This live viewer shows our
robot's state machine coordinating navigation and handling.”

Aditya: “The robot observes an object's geometry, approaches it, grips and lifts
it, and checks placement after withdrawing. The slipper needs orientation-aware
grasp planning. In this separate failure case, the controller stops with the
payload held instead of forcing an unsafe delivery. We count unsuccessful trials.”

Soumil: “Across 50 independent runs per condition, the proposed controller
fully cleared 28 rooms; the baseline cleared none. The restricted completion
score improves, but the robot is still imperfect. The business model separates
staff capacity, elapsed room readiness and cash spending. Under our current
assumptions it releases about nine staff-minutes daily but does not pay back.”

Use each person's own truthful learning/contribution statement for the ending.
The above is a rehearsal script, not proof of who authored a file.

## 5 Check and publish tomorrow

- Replay the saved file: 3–4 minutes, no slides, every member visible and speaking,
  readable simulation/results/business graph, audible voices and honest numbers.
- Upload the video itself natively to LinkedIn, one post for the group. Do not
  substitute a YouTube link or commit the video to GitHub.
- Tag teammates, MPSTME and Dr Sunny Nanade; include the course group-folder link.
- Record the actual duration and published LinkedIn URL in dossier Section 5.
- Complete the two real peer reviews, personal declarations and signatures, then
  export the final signed PDF. Every member turns in the same file on Teams.
