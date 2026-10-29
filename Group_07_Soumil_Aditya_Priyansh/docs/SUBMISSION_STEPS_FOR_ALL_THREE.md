# Current submission update

GitHub upload and course pull request are complete; faculty merge is pending.
The historical setup commands below need not be rerun. See
GITHUB_SUBMISSION_RECEIPT.json for links and the verified evidence commit.

# Submission steps for Group 07

Checked 27 October 2026. Team: Priyansh — Lead Robotics Systems Architect;
Soumil — Business Analyst; Aditya — Navigation/Vision and Telemetry QA.
No fork, invitations, commits, push, pull request or Teams submission was performed
by preparing these instructions.

## Finish the shared dossier first

The saved Word/PDF contain all three supplied signatures. The final local video is verified at 03:23.73, and the three video-content checks
are Yes. The previous LinkedIn post was deleted; the replacement upload and its URL are pending. Maximum peer scores
are provisional user-requested ratings; actual video assessment/timestamps remain
pending. Personal figures are explicitly provisional placeholders for member
editing; originality/viva/consent confirmations remain pending.
Complete the required actual entries, then export/review one final PDF and replace
BOTH dossier files in the prepared folder's docs/. Every member uses the exact
same final PDF. No consent, rating, hour or review score should be invented.

## What goes to Teams

Each of Priyansh, Soumil and Aditya uses their OWN college Teams account:
1. Open the MDRIIA class, Assignments, then the capstone assignment.
2. Choose Add work / Upload and attach MDRIIA_Group_07_Technical_Dossier.pdf.
3. Open the attachment to check it is the same final PDF, including all signatures.
4. Click Turn in and check submission status/confirmation. Attaching alone is not
   submission. All three must do this personally under the course's explicit rule.

Faculty subsequently requested the project on Teams as well. Attach the smaller
Teams project ZIP, the final PDF and the video; the complete measured CSV export
is now delivered through GitHub. Each member must personally click Turn in.
See GITHUB_SUBMISSION_RECEIPT.json for the actual completed GitHub upload.
The published assignment deadline was 26 October 2026, 23:59 IST. If Teams offers
Turn in late, use it. If submissions are closed, faculty must reopen the assignment.
Official UI instructions:
https://support.microsoft.com/en-au/education/assignments/turn-in-an-assignment-in-microsoft-teams

## GitHub contributors and access

Contributors are identified from actual commits; adding a collaborator grants
access but does not itself create contribution credit. A commit's email must be
associated with that person's GitHub account; default-branch contributor displays
may wait until the pull request is merged.

The connected account is Priyansh0818. Its current course-repository permissions
report pull=true, push=false and admin=false. The repository belongs to
sunny-nanade. With that reported access, use a fork and pull request. Only the
course-repository owner can invite collaborators to that personally owned repo.

1. Sign into GitHub as Priyansh0818.
2. Open https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026 and click Fork.
3. Select Priyansh0818 as owner, keep the repository name and create the fork.
4. In YOUR FORK: Settings → Collaborators → Add people.
5. Invite soumilpatro and adityashah0705-svg. Each accepts using their own account.

This prepares shared write access on your fork. Do not create an unrelated empty
repository as the course destination; your pull request must target the assigned
Group_07_Soumil_Aditya_Priyansh folder in the faculty repository.

Official instructions:
https://docs.github.com/en/pull-requests/how-tos/work-with-forks/fork-a-repo
https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository
https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors

## Clone the fork into a fresh folder

Do this after creating the fork with the same repository name. Choose a NEW
local folder, separate from the existing 45 GB working project. GitHub Desktop's
Clone repository / URL flow is also suitable. In PowerShell, from that new location:

```powershell
git clone https://github.com/Priyansh0818/NMIMS-MPSTME-MDRIIA-2026.git
cd NMIMS-MPSTME-MDRIIA-2026
git switch -c feat/e066-capstone-submission
git var GIT_AUTHOR_IDENT
```

Check that the author identity is YOUR identity and uses an email connected to
YOUR GitHub account. Each teammate commits as themselves, never by changing the
local author to impersonate another person.

In this FRESH clone, replace only its Group_07_Soumil_Aditya_Priyansh folder with
the prepared clean Group_07_Soumil_Aditya_Priyansh folder. Source on this computer:

D:\P\NMIMS-MPSTME-MDRIIA-2026\Group_07_Soumil_Aditya_Priyansh\delivery\Group_07_Soumil_Aditya_Priyansh

The clone should directly contain Group_07_Soumil_Aditya_Priyansh/models/,
src/, analytics/ and docs/. Do not nest delivery/ or a second capstone/ folder.
Copy .gitignore and .gitattributes too. Preserve the other eleven groups and
course root files. The original 45 GB project and verbose archive stay local.

## Commit and push the core first

From the CLONED REPOSITORY ROOT, review all changes, then run:

```powershell
git status --short
git add -- Group_07_Soumil_Aditya_Priyansh ':(exclude)Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/**' ':(exclude)Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/**'
git diff --cached --stat
git commit -m "feat(group07): add audited capstone implementation and dossier"
git push -u origin feat/e066-capstone-submission
```

STOP on any failed command and fix it before continuing. Do not use force push.
Review the staged diff before committing. These instructions do not fabricate
file authorship; the initial uploader is the real author of the upload commit.

## Push the eight evidence batches

GitHub limits one push to 2 GiB. The data batches below are each under 750 MB.
Commit AND PUSH each batch before staging the next; making all commits first
and doing one final giant push can still exceed the limit. Do not add the entire
dataset to the first commit. All individual packet files were checked below 50 MB.
Official reference:
https://docs.github.com/en/get-started/using-git/troubleshooting-the-2-gb-push-limit

### Evidence batch 1: 744.4 MB

```powershell
git add -- 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1000' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1001' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1002' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1003' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1004' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1005' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1006' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1007' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1008' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1009' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1010' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1011'
git diff --cached --stat
git commit -m "test(group07): add measured trial evidence batch 1 of 8"
git push origin feat/e066-capstone-submission
```

### Evidence batch 2: 732.5 MB

```powershell
git add -- 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1012' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1013' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1014' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1015' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1016' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1017' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1018' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1019' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1020' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1021' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1022' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1023'
git diff --cached --stat
git commit -m "test(group07): add measured trial evidence batch 2 of 8"
git push origin feat/e066-capstone-submission
```

### Evidence batch 3: 727.1 MB

```powershell
git add -- 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1024' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1025' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1026' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1027' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1028' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1029' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1030' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1031' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1032' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1033' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1034' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1035'
git diff --cached --stat
git commit -m "test(group07): add measured trial evidence batch 3 of 8"
git push origin feat/e066-capstone-submission
```

### Evidence batch 4: 728.7 MB

```powershell
git add -- 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1036' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1037' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1038' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1039' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1040' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1041' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1042' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1043' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1044' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1045' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1046' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1047' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1048'
git diff --cached --stat
git commit -m "test(group07): add measured trial evidence batch 4 of 8"
git push origin feat/e066-capstone-submission
```

### Evidence batch 5: 745.8 MB

```powershell
git add -- 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1049' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2000' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2001' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2002' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2003' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2004' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2005' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2006' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2007' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2008' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2009' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2010' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2011' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2012' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2013' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2014' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2015'
git diff --cached --stat
git commit -m "test(group07): add measured trial evidence batch 5 of 8"
git push origin feat/e066-capstone-submission
```

### Evidence batch 6: 723.3 MB

```powershell
git add -- 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2016' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2017' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2018' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2019' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2020' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2021' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2022' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2023' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2024' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2025' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2026' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2027' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2028' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2029' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2030' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2031'
git diff --cached --stat
git commit -m "test(group07): add measured trial evidence batch 6 of 8"
git push origin feat/e066-capstone-submission
```

### Evidence batch 7: 727.0 MB

```powershell
git add -- 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2032' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2033' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2034' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2035' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2036' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2037' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2038' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2039' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2040' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2041' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2042' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2043' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2044' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2045' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2046' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2047'
git diff --cached --stat
git commit -m "test(group07): add measured trial evidence batch 7 of 8"
git push origin feat/e066-capstone-submission
```

### Evidence batch 8: 110.9 MB

```powershell
git add -- 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2048' 'Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2049'
git diff --cached --stat
git commit -m "test(group07): add measured trial evidence batch 8 of 8"
git push origin feat/e066-capstone-submission
```

## Each teammate contributes using their own account

After accepting the fork invitation, each member reviews the relevant actual
files and makes a genuine contribution: code corrections, source checks,
calculations, tests, documented validation or their own learning/declaration
answers. Empty commits or adding a name alone do not establish project work.

- Priyansh: robot integration, controller/model review, assembled project and PR.
- Soumil: economic inputs/formulas, cash vs capacity, queue/FMEA and business notes.
- Aditya: navigation/grasp checks, trial evidence, telemetry/statistics and QA notes.

They may edit an appropriate text file on the shared fork's submission branch
through GitHub while signed into their own accounts, or use a local clone.
Local contributors pull before pushing and review/resolve actual differences.
A single person uploading all files does not satisfy the course requirement
that each member commits their own genuine work.

## Open the course pull request

After all batches and member contributions are pushed:
1. Open your fork and select Compare & pull request / Contribute.
2. Base repository: sunny-nanade/NMIMS-MPSTME-MDRIIA-2026; base branch: main.
3. Head repository: Priyansh0818/NMIMS-MPSTME-MDRIIA-2026;
   compare branch: feat/e066-capstone-submission.
4. Review the changed-file list: only Group 07 should change. Confirm both final
   dossier files are included and the real video URL is entered.
5. Create the pull request. Faculty controls review/merge into the course main.
   Keep each member's genuine commits identifiable for the contribution check.

The GitHub destination is the faculty course folder through this PR, not merely
a personal repository link. Nothing in this guide merges automatically.

## What every member still does

All three: confirm their own factual entries/declarations/consent, verify the
shared signed PDF, commit genuine work from their own account, participate in
the video and peer reviews, personally click Turn in on Teams, and prepare for
the live 31 October expo/viva. One group LinkedIn post is sufficient; record its
actual URL and duration in the dossier. The video file stays out of GitHub.
