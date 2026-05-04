---
id: TASK-FPA-006
title: Apply patch 005 (edge search startNode/endNode) as commit 4
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 3
estimated_minutes: 30
execution_location: promaxgb10-41b1
tags: [graphiti, fork, search, falkordb, performance]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 2
implementation_mode: direct
dependencies: [TASK-FPA-005]
workspace_name: fork-patch-application-wave2-4
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Apply patch 005 (edge search startNode/endNode reshape)

**WHY**: Bug #9 — `edge_fulltext_search` and `edge_bfs_search` re-MATCH every yielded relationship by uuid to re-find its endpoints. With ~1500 fulltext yields × ~5000 edges that's 7.5M comparisons per query (26-118s observed). Plus a latent bug in `edge_bfs_search` where the undirected MATCH double-counts each edge with swapped source/target. Patch 005 replaces both with O(n) `startNode(rel)`/`endNode(rel)` access (matching the Neptune branch) and emits each edge exactly once in directed form.

**WHAT**: Apply [patches/005-edge-search-direct-endpoints.patch](../../../patches/005-edge-search-direct-endpoints.patch) on top of commit 3 (decorator), commit, and re-run the baseline diff.

## Steps

```bash
cd ~/Projects/appmilla_github/graphiti
git checkout guardkit-fixes-0.29
git apply --check patches/005-edge-search-direct-endpoints.patch
git apply patches/005-edge-search-direct-endpoints.patch

git add graphiti_core/search/search_utils.py
git commit -m "fix(search): direct endpoint access via startNode/endNode (TASK-FORK-PATCH bug #9)

edge_fulltext_search and edge_bfs_search re-MATCH every yielded
relationship by uuid to re-find its endpoints. With ~1500 fulltext
yields × ~5000 edges that's 7.5M comparisons per query (26-118s
observed). Use startNode(rel)/endNode(rel) for O(n) direct access. The
Neptune branch already does this; the default branch now matches. Also
fixes a latent double-count in edge_bfs_search where an undirected
MATCH was emitting each edge twice with swapped source/target.

Refs: upstream issue #1272;
guardkit/knowledge/falkordb_workaround.py:380-635 (consumer-side patch)."

# Baseline diff (AC-FORK-19)
SHA=$(git rev-parse --short HEAD)
.venv/bin/pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/post-${SHA}-falkordb.txt
diff /tmp/baseline-falkordb.txt /tmp/post-${SHA}-falkordb.txt || echo "DIFF FOUND — investigate"

# ALSO: run guardkit's workaround test suite — its `test_edge_fulltext_search`
# and `test_edge_bfs_search` cover the same fix shape. Expect new passes.
cd ~/Projects/appmilla_github/guardkit
.venv/bin/pytest tests/knowledge/test_falkordb_workaround.py -v 2>&1 | tee /tmp/post-${SHA}-workaround.txt
diff /tmp/baseline-workaround.txt /tmp/post-${SHA}-workaround.txt || echo "DIFF FOUND — investigate"
```

## Acceptance Criteria

- [ ] `git apply --check patches/005-edge-search-direct-endpoints.patch` passes.
- [ ] Patch landed as a single commit on `guardkit-fixes-0.29`.
- [ ] Baseline diff for graphiti-core falkordb suite shows no new failures.
- [ ] Baseline diff for guardkit `test_falkordb_workaround.py` may show **new passes** (tests previously requiring `apply_falkordb_workaround()` runtime monkey-patch may now pass against the unwrapped fork). New failures are unacceptable; new passes are expected per AC-FORK-11.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Mechanical plan" Step 2 commit 4; AC-FORK-11, AC-FORK-19.
- Addendum: [TASK-FORK-PATCH-review-addendum-execution-flow.md](../../../.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md) §"Diagrams 8-9".
- Patch: [patches/005-edge-search-direct-endpoints.patch](../../../patches/005-edge-search-direct-endpoints.patch).

## Regression risk

Per addendum: **low**, but with one **explicit semantic change** worth flagging in FORK-NOTES.md (TASK-FPA-008):

- **edge_fulltext_search**: pure perf fix; result set identical. Zero risk.
- **edge_bfs_search**: original undirected MATCH emitted each RELATES_TO twice with swapped source/target. New code emits each edge once in directed (source → target) form. **Result count drops by ~2× for that call**; this is a latent bug fix, not a regression, but consumers iterating the result list may see fewer rows than before.

## Notes

- This is the **last** patch-application commit in Wave 2. After this lands, the working tree is in the desired post-patch state and ready for tagging (TASK-FPA-007).
- If guardkit's workaround test suite shows new passes after this commit, that confirms the fork eliminates the need for the runtime monkey-patch for bugs #8/#9. Removing `apply_falkordb_workaround()` from guardkit is a follow-up task — file separately, do NOT include in this fork-patch sweep.
