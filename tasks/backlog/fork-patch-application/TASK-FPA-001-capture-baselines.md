---
id: TASK-FPA-001
title: Capture pre-application test baselines (graphiti-core, mcp_server, guardkit workaround suite)
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 2
estimated_minutes: 15
execution_location: promaxgb10-41b1
tags: [graphiti, fork, baseline, verification]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 1
implementation_mode: direct
dependencies: []
workspace_name: fork-patch-application-wave1-1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Capture pre-application test baselines

**WHY**: This task implements **Step 0** of TASK-FORK-PATCH's mechanical plan and is the prerequisite for AC-FORK-19 (per-commit regression diff). Without a clean pre-application baseline, post-patch test failures cannot be bisected to a single landed patch.

**WHAT**: Run the relevant pytest suites against the current `d0913fe` head (no patches applied) and capture stdout/stderr to `/tmp/baseline-{falkordb,mcp,workaround}.txt`.

## Steps

```bash
cd ~/Projects/appmilla_github/graphiti
.venv/bin/pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/baseline-falkordb.txt
.venv/bin/pytest mcp_server/tests/ --tb=line 2>&1 | tee /tmp/baseline-mcp.txt

cd ~/Projects/appmilla_github/guardkit
.venv/bin/pytest tests/knowledge/test_falkordb_workaround.py -v 2>&1 | tee /tmp/baseline-workaround.txt
```

If guardkit's `tests/knowledge/test_falkordb_workaround.py` reveals already-failing tests against unforked graphiti-core (some may pass only when `apply_falkordb_workaround()` runs at runtime — which is the consumer-side patch path), record the baseline as-is. The post-fork goal is **at least** that baseline; new passes are expected and acceptable.

## Acceptance Criteria

- [ ] `/tmp/baseline-falkordb.txt` contains pytest output for graphiti-core's falkordb-tagged tests against current head.
- [ ] `/tmp/baseline-mcp.txt` contains pytest output for `mcp_server/tests/` against current head.
- [ ] `/tmp/baseline-workaround.txt` contains pytest output for guardkit's `test_falkordb_workaround.py` against current head.
- [ ] Each output file is non-empty and contains pytest's "passed/failed/error" summary line.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Mechanical plan" Step 0.
- AC-FORK-19 in parent.
- Review addendum: [TASK-FORK-PATCH-review-addendum-execution-flow.md](../../../.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md) §"Pre-application baseline capture".
