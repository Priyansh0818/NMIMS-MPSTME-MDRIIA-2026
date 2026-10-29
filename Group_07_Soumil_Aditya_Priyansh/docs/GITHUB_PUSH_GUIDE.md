# Video revision 29 October 2026

At the team's request, the corrected 03:23.73 showcase MP4 is included at the
project root. This supersedes the older instructions below that excluded video
files. The deleted LinkedIn post URL has been removed; replacement upload is
pending. Do not report the showcase as published until the team supplies its new URL.

# GitHub submission status

The complete project and all eight data batches have been pushed to:
https://github.com/Priyansh0818/NMIMS-MPSTME-MDRIIA-2026/tree/feat/e066-capstone-submission/Group_07_Soumil_Aditya_Priyansh

Faculty pull request: https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026/pull/6

The PR is open for faculty review. See GITHUB_SUBMISSION_RECEIPT.json for
the verified data counts and evidence commit. Both teammates were invited;
Soumil's write access was confirmed. Each teammate must make their own genuine
commits. No colleague's author identity or contribution history was fabricated.

The manual upload instructions below are retained for reference. Statements
about not having created a fork or pushed were preparation-time notes and are
superseded by this status and the receipt. Do not repeat the eight data imports.

---

# GitHub upload guide

## Current account access checked 27 October

The connected Priyansh0818 account reports no push/admin access to the faculty
repository. Use a fork, invite teammates as collaborators to your fork, and open
a PR to the faculty main branch. SUBMISSION_STEPS_FOR_ALL_THREE.md contains the
complete current instructions and exact eight batch commands. No fork, invitations,
commits or push have been executed by preparing these files.

## Destination and current status

Course repository: https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026
Assigned folder: Group_07_Soumil_Aditya_Priyansh/

Copy the CONTENTS of this prepared group folder into the assigned folder of a
fresh working clone. Keep .gitignore and .gitattributes. Preserve course history
and unrelated groups; compare the existing group folder before replacing old
beta files. Do not upload the messy working tree, local archive or a nested
delivery/ directory. This packet itself is not a separate initialized repository.

No push or personal commit has been made by preparing it. Follow the course's
CONTRIBUTING.md / BRANCHING_GUIDE.md and use a feature branch and pull request.
Each member reviews and commits genuine work using their own account; do not
manufacture authorship or set another person's author identity.

## Upload in stages

The complete packet is about 5.5 GB because it retains the measured 500 Hz rows.
All individual files are below 50 MB. Use Git rather than dragging thousands of
files into the website. GitHub enforces a 2 GiB limit per push. The prepared data
batches are below 750 MB each, leaving headroom; commit and PUSH EACH batch
before adding the next. Several small commits followed by one giant first push
can still exceed the limit.

1. Copy/review the folder in a fresh course clone and create the course branch.
2. First stage the code, models, documentation, frozen bundle and export manifests,
   excluding the two measurement directories below. Review the staged files,
   commit and push that core.
3. Add the seed directories for evidence batch 1 below; review, commit and push.
   Repeat for each batch. Do not omit failed runs or any listed seed directory.
4. Before final submission, update BOTH dossier files after actual team entries, video URL,
   peer reviews and signatures, then commit/push the final documentation update.
5. Open/review the course pull request and check a fresh checkout can run the robot
   and business model. Every member still turns in the signed PDF on Teams.

Core staging example, from the COURSE REPOSITORY root, after reviewing the copy:

```powershell
git add -- Group_07_Soumil_Aditya_Priyansh ':(exclude)Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/**' ':(exclude)Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/**'
git diff --cached --stat
```

Then commit and push to your feature branch. For a data batch, use `git add --`
with only the batch's listed directories, review the staged changes, commit and
push. GITHUB_UPLOAD_BATCHES.json supplies the exact machine-readable paths.
Do not use force push or rewrite the faculty's history.

Official references:
- https://docs.github.com/en/get-started/using-git/troubleshooting-the-2-gb-push-limit
- https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository

## Evidence batches

### Batch 1 — 744.4 MB

- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1000/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1001/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1002/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1003/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1004/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1005/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1006/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1007/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1008/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1009/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1010/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1011/`

### Batch 2 — 732.5 MB

- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1012/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1013/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1014/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1015/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1016/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1017/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1018/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1019/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1020/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1021/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1022/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1023/`

### Batch 3 — 727.1 MB

- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1024/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1025/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1026/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1027/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1028/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1029/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1030/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1031/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1032/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1033/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1034/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1035/`

### Batch 4 — 728.7 MB

- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1036/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1037/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1038/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1039/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1040/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1041/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1042/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1043/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1044/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1045/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1046/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1047/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1048/`

### Batch 5 — 745.8 MB

- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/baseline/seed1049/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2000/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2001/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2002/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2003/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2004/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2005/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2006/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2007/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2008/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2009/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2010/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2011/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2012/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2013/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2014/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2015/`

### Batch 6 — 723.3 MB

- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2016/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2017/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2018/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2019/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2020/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2021/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2022/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2023/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2024/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2025/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2026/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2027/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2028/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2029/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2030/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2031/`

### Batch 7 — 727.0 MB

- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2032/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2033/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2034/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2035/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2036/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2037/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2038/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2039/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2040/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2041/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2042/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2043/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2044/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2045/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2046/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2047/`

### Batch 8 — 110.9 MB

- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2048/`
- `Group_07_Soumil_Aditya_Priyansh/analytics/submission_trials/proposed/seed2049/`

