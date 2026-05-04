---
id: TASK-FPA-005
title: Apply patch 004 (handle_multiple_group_ids decorator >=1) as commit 3
status: in_review
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T12:10:00+01:00
previous_state: backlog
patch_commit: 7a914ec
test_results:
  status: passed
  baseline_diff: no_new_failures
  falkordb_summary: "5 failed, 24 passed, 1 skipped, 42 errors (identical to baseline)"
  last_run: 2026-05-04T12:10:00+01:00
priority: high
task_type: feature
complexity: 2
estimated_minutes: 20
execution_location: promaxgb10-41b1
tags: [graphiti, fork, decorator, falkordb]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 2
implementation_mode: direct
dependencies: [TASK-FPA-004]
workspace_name: fork-patch-application-wave2-3
---

# Apply patch 004 (handle_multiple_group_ids decorator)

**WHY**: Bug #8 — `handle_multiple_group_ids` skips the FalkorDB driver-clone path for single-group calls because of the `len > 1` check. Per the addendum execution-flow trace (Diagrams 1-3), this is the second half of the single-group correctness fix; patch 001 alone is non-regressive but produces the same `[]` empty-result outcome that upstream produced. Together with patch 001, single-group searches against dashed group_ids are restored.

**WHAT**: Apply [patches/004-handle-multiple-group-ids-decorator.patch](../../../patches/004-handle-multiple-group-ids-decorator.patch) on top of commit 2 (factories.py), commit, and re-run the baseline diff.

## Steps

```bash
cd ~/Projects/appmilla_github/graphiti
git checkout guardkit-fixes-0.29
git apply --check patches/004-handle-multiple-group-ids-decorator.patch
git apply patches/004-handle-multiple-group-ids-decorator.patch

git add graphiti_core/decorators.py
git commit -m "fix(decorator): handle single-group FalkorDB calls (TASK-FORK-PATCH bug #8)

handle_multiple_group_ids previously skipped its driver-clone path when
group_ids has exactly one element (\`len > 1\` check). Single-group
searches ran on whatever named graph the shared driver was last on —
wrong graph, empty results. Drop the \`len > 1\` check so single-group
calls also fan out via \`driver.clone(database=gid)\`.

Refs: upstream PR #1170 / issue #1161;
guardkit/knowledge/falkordb_workaround.py:97-176 (consumer-side patch)."

# Baseline diff (AC-FORK-19)
SHA=$(git rev-parse --short HEAD)
.venv/bin/pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/post-${SHA}-falkordb.txt
diff /tmp/baseline-falkordb.txt /tmp/post-${SHA}-falkordb.txt || echo "DIFF FOUND — investigate"
```

## Acceptance Criteria

- [ ] `git apply --check patches/004-handle-multiple-group-ids-decorator.patch` passes.
- [ ] Patch landed as a single commit on `guardkit-fixes-0.29`.
- [ ] Baseline diff for graphiti-core falkordb suite shows no new failures.
- [ ] Manual sanity check: with the patches landed, a single-group search through `Graphiti.search()` against a dashed group_id (`['proj-foo']`) is no longer returning `[]` for known-populated graphs. Defer the full smoke test to TASK-FPA-009.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Mechanical plan" Step 2 commit 3; AC-FORK-10, AC-FORK-19.
- Addendum: [TASK-FORK-PATCH-review-addendum-execution-flow.md](../../../.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md) §"Diagrams 1-3", §"Critical interaction analysis".
- Patch: [patches/004-handle-multiple-group-ids-decorator.patch](../../../patches/004-handle-multiple-group-ids-decorator.patch).

## Regression risk

Per addendum: **none.** Per-group `driver.clone()` overhead is cheap (lazy). No semantic change for already-working multi-group calls (`len > 1` and `len == 1` now both take the clone path; clone-then-execute-once is equivalent to direct-execute for the single case). Commutatively safe with patch 001.
