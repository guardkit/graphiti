---
id: TASK-FPA-002
title: Rename branch to guardkit-fixes-0.29 and push to origin (guardkit/graphiti)
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 1
estimated_minutes: 10
execution_location: promaxgb10-41b1
tags: [graphiti, fork, github]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 1
implementation_mode: direct
dependencies: []
workspace_name: fork-patch-application-wave1-2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Rename branch and push to origin

**WHY**: The fork already exists at `https://github.com/guardkit/graphiti` (origin), forked from upstream `getzep/graphiti`. The current local branch `work/falkordb-fixes` carries two unpushed commits (`db0d0bd` lock-decisions + `4ef2534` subtask structure). This task renames the branch to match the existing `guardkit-*` naming convention (peer of `guardkit-tooling` already on origin) and pushes it.

**WHAT**: Rename `work/falkordb-fixes` → `guardkit-fixes-0.29` locally and on origin; push with upstream tracking.

## Pre-flight check

```bash
cd ~/Projects/appmilla_github/graphiti
git remote -v                                       # expect: origin → https://github.com/guardkit/graphiti.git
git branch -avv                                     # expect: * work/falkordb-fixes [no upstream tracking]
git log --oneline -3                                # expect: 4ef2534, db0d0bd, d0913fe (or later)
git ls-remote --heads origin | grep guardkit        # expect: guardkit-tooling already exists
```

## Steps

```bash
# 1. Rename local branch
git branch -m work/falkordb-fixes guardkit-fixes-0.29

# 2. Push with upstream tracking
git push -u origin guardkit-fixes-0.29

# 3. Verify
git branch -avv | grep guardkit-fixes-0.29
gh api repos/guardkit/graphiti/branches/guardkit-fixes-0.29 --jq '.commit.sha'
# Expect: SHA of local HEAD (currently 4ef2534 or later if guardkit-rename commit landed)
```

## Acceptance Criteria

- [ ] Local branch is named `guardkit-fixes-0.29` (no longer `work/falkordb-fixes`).
- [ ] Branch pushed to `origin` with upstream tracking (`git branch -avv` shows `[origin/guardkit-fixes-0.29]`).
- [ ] `gh api repos/guardkit/graphiti/branches/guardkit-fixes-0.29` returns 200 with `commit.sha` matching local HEAD.
- [ ] Existing `guardkit-tooling` branch on origin is **not** touched.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Decisions" 2-4 + §"Mechanical plan" Step 1.

## Notes

- The fork was created at `guardkit/graphiti` before this task started, so steps to "create the fork repo" are not needed.
- Branch convention chosen to match the existing `guardkit-tooling` branch already on origin (per `git ls-remote --heads origin`).
- This task is parallel-safe with TASK-FPA-001 (baseline capture); they touch different things.
