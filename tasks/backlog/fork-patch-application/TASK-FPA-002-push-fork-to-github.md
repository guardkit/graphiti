---
id: TASK-FPA-002
title: Push graphiti fork to GitHub (appmilla/graphiti, public) on branch appmilla-fixes-0.29
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 2
estimated_minutes: 30
execution_location: promaxgb10-41b1
tags: [graphiti, fork, github, infra]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 1
implementation_mode: manual
dependencies: []
workspace_name: fork-patch-application-wave1-2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Push graphiti fork to GitHub

**WHY**: Decisions 2 and 3 in TASK-FORK-PATCH are locked to **public fork on the `appmilla` org** (or personal account if the org doesn't exist). Decision 4 is locked to **branch + tag** (active dev on `appmilla-fixes-0.29` branch; cut tags at shipping moments). This task creates the remote and pushes the current `work/falkordb-fixes` content as `appmilla-fixes-0.29`.

**WHAT**: Manual GH/git operations to create the remote repo, rename the local branch, set up tracking, and push.

## Steps

```bash
# 1. Confirm whether `appmilla` org exists
gh repo view appmilla/graphiti 2>&1 || echo "Org or repo doesn't exist yet"

# 2. If org exists: create the fork repo under appmilla
#    If org doesn't exist: substitute personal account (rwoollcott or similar)
gh repo create appmilla/graphiti --public \
  --description "appmilla fork of getzep/graphiti with FalkorDB/RediSearch and MCP fixes (TASK-FORK-PATCH)" \
  --homepage "https://github.com/getzep/graphiti"

# 3. Add the new remote (preserve `origin` as the upstream getzep/graphiti)
cd ~/Projects/appmilla_github/graphiti
git remote -v   # should show origin → getzep/graphiti
git remote add appmilla git@github.com:appmilla/graphiti.git

# 4. Rename local branch to the fork's main dev branch name
git branch -m work/falkordb-fixes appmilla-fixes-0.29

# 5. Push branch with upstream tracking
git push -u appmilla appmilla-fixes-0.29
```

## Acceptance Criteria

- [ ] `gh repo view appmilla/graphiti` returns repo metadata (or, if `appmilla` org doesn't exist, equivalent under the substituted personal account — capture the chosen URL).
- [ ] Remote `appmilla` is added in the local clone alongside `origin` (which still points at `getzep/graphiti`).
- [ ] Branch `appmilla-fixes-0.29` is pushed with upstream tracking on the `appmilla` remote.
- [ ] The pushed tip equals the current local head `db0d0bd` (the lock-decisions + patches-004/005 commit).
- [ ] Repo description on GitHub includes a link to the parent task or a one-line summary of the fork's purpose.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Decisions" 2-4 + §"Mechanical plan" Step 1.

## Notes

- Visibility is public per Decision 2 (DDD South West talk + simpler `pip install git+https://...`).
- Branch protection rules (require PR for merges) are out of scope for this task — file as a follow-up if desired.
- The local clone keeps `origin` pointing at `getzep/graphiti` to make periodic upstream merges straightforward.
