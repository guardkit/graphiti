---
id: TASK-FPA-003
title: Apply patches 001+002+003 (RediSearch drop-filter, sanitize backtick, MCP host binding) as commit 1
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T11:05:00+01:00
completed: 2026-05-04T11:05:00+01:00
previous_state: in_review
completed_location: tasks/completed/fork-patch-application/
patch_commit: 94a2e6d
test_results:
  status: passed
  baseline_diff: no_new_failures
  falkordb_summary: "5 failed, 24 passed, 1 skipped, 42 errors (identical to baseline)"
  mcp_summary: "32 failed, 11 passed, 2 errors (identical to baseline)"
  last_run: 2026-05-04T10:58:00+01:00
priority: high
task_type: feature
complexity: 3
estimated_minutes: 30
execution_location: promaxgb10-41b1
tags: [graphiti, fork, falkordb, redisearch, mcp]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 2
implementation_mode: direct
dependencies: [TASK-FPA-001, TASK-FPA-002]
workspace_name: fork-patch-application-wave2-1
---

# Apply patches 001+002+003 (RediSearch + sanitize + MCP host)

**WHY**: First of four patch-application commits. Bundles three orthogonal fixes that all act at boundary B3 (driver↔FalkorDB) or B5 (MCP transport). Per the addendum execution-flow trace, all three are independently safe to land and have no inter-dependencies.

**WHAT**: Apply patches 001/002/003 as a single commit on the `guardkit-fixes-0.29` branch, then re-run the AC-FORK-19 baseline diff.

## Bugs covered

- **#5 + #11 + #12** (patch 001): drop the `(@group_id:...)` fulltext filter; return `*` for empty post-stopword queries.
- **#10** (patch 002): strip backtick in `sanitize()`; matches upstream's strip set for slashes/pipes/backslashes.
- **#13** (patch 003): bind `MCP_SERVER_HOST` env var at FastMCP construction time so `transport_security` freezes against the right allow-list.

## Steps

```bash
cd ~/Projects/appmilla_github/graphiti

# 1. Verify clean tree on the fix branch
git status                                                  # expect: clean
git rev-parse --abbrev-ref HEAD                            # expect: guardkit-fixes-0.29

# 2. Pre-apply check
git apply --check patches/001-drop-fulltext-group-filter.patch \
                  patches/002-extend-sanitize-strip-backtick.patch \
                  patches/003-mcp-early-host-binding.patch

# 3. Apply
git apply patches/001-drop-fulltext-group-filter.patch \
          patches/002-extend-sanitize-strip-backtick.patch \
          patches/003-mcp-early-host-binding.patch

# 4. Stage and commit (use the suggested commit message from patches/README.md)
git add graphiti_core/driver/falkordb_driver.py \
        graphiti_core/driver/falkordb/operations/search_ops.py \
        mcp_server/src/graphiti_mcp_server.py
git commit -m "fix(falkordb,mcp): drop @group_id filter, strip backtick, bind FastMCP host

- patches/001: drop unreliable @group_id fulltext filter on FalkorDB;
  group isolation is enforced by multi-graph driver clone + Cypher
  WHERE clause. Fixes bugs #5/#11/#12.
- patches/002: strip backtick in sanitize() so markdown-style
  \`path/to/file.md\` references in episode bodies don't leak into
  RediSearch syntax. Fixes bug #10 partial (slashes/pipes/backslashes
  already in 0.29's strip list).
- patches/003: read MCP_SERVER_HOST at module load so FastMCP's
  transport_security freezes against the right allow-list. Default
  preserves upstream behaviour. Fixes bug #13.

Refs: study-tutor R-WAVE5-03; guardkit/knowledge/falkordb_workaround.py."

# 5. Re-run baseline diff (AC-FORK-19)
SHA=$(git rev-parse --short HEAD)
.venv/bin/pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/post-${SHA}-falkordb.txt
.venv/bin/pytest mcp_server/tests/ --tb=line 2>&1 | tee /tmp/post-${SHA}-mcp.txt
diff /tmp/baseline-falkordb.txt /tmp/post-${SHA}-falkordb.txt || echo "DIFF FOUND — investigate"
diff /tmp/baseline-mcp.txt /tmp/post-${SHA}-mcp.txt || echo "DIFF FOUND — investigate"
```

## Acceptance Criteria

- [ ] All three patches apply cleanly (`git apply --check` passes; `git apply` returns 0).
- [ ] Single commit landed on `guardkit-fixes-0.29` with the message above (or equivalent).
- [ ] Baseline diff for `falkordb` and `mcp` test suites shows **no new failures**. New passes are acceptable.
- [ ] If any new failure appears: revert this commit, file a blocker subtask, and pause Wave 2.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Mechanical plan" Step 2 commit 1; AC-FORK-02, AC-FORK-19.
- Addendum: [TASK-FORK-PATCH-review-addendum-execution-flow.md](../../../.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md) §"Diagrams 1-7" + §"Diagrams 10-11".
- Patches README: [patches/README.md](../../../patches/README.md).

## Regression risk (from addendum)

| Patch | Worst case if buggy | Detection |
|-------|---------------------|-----------|
| 001 | Single-group reads return wrong-graph data | Cypher WHERE clause is the safety net (verified at search_ops.py:142-144 etc.); in practice no regression because the WHERE always backstops |
| 002 | Search-miss against legacy backtick-tainted index | Theoretical only (guardkit pre-strips; production index doesn't have backtick tokens) |
| 003 | HTTP 421 if MCP_SERVER_HOST env unset → defaults to 127.0.0.1 = upstream | None (default behaviour preserved) |
