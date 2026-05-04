---
id: TASK-FPA-001
title: Capture pre-application test baselines (graphiti-core, mcp_server, guardkit workaround suite)
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T08:50:00+01:00
completed: 2026-05-04T08:50:00+01:00
completed_location: tasks/completed/fork-patch-application/
previous_state: in_review
state_transition_reason: Baselines captured and verified; outputs persisted to /tmp/baseline-{falkordb,mcp,workaround}.txt
organized_files:
  - TASK-FPA-001-capture-baselines.md
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
  status: captured
  coverage: null
  last_run: 2026-05-04T08:43:00+01:00
  baselines:
    falkordb: "5 failed, 24 passed, 1 skipped, 381 deselected, 42 errors in 6.45s"
    mcp: "32 failed, 11 passed, 2 errors in 150.60s"
    workaround: "43 passed, 1 warning in 2.19s"
---

# Capture pre-application test baselines

**WHY**: This task implements **Step 0** of TASK-FORK-PATCH's mechanical plan and is the prerequisite for AC-FORK-19 (per-commit regression diff). Without a clean pre-application baseline, post-patch test failures cannot be bisected to a single landed patch.

**WHAT**: Run the relevant pytest suites against the current `d0913fe` head (no patches applied) and capture stdout/stderr to `/tmp/baseline-{falkordb,mcp,workaround}.txt`.

## Steps (as written)

```bash
cd ~/Projects/appmilla_github/graphiti
.venv/bin/pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/baseline-falkordb.txt
.venv/bin/pytest mcp_server/tests/ --tb=line 2>&1 | tee /tmp/baseline-mcp.txt

cd ~/Projects/appmilla_github/guardkit
.venv/bin/pytest tests/knowledge/test_falkordb_workaround.py -v 2>&1 | tee /tmp/baseline-workaround.txt
```

If guardkit's `tests/knowledge/test_falkordb_workaround.py` reveals already-failing tests against unforked graphiti-core (some may pass only when `apply_falkordb_workaround()` runs at runtime — which is the consumer-side patch path), record the baseline as-is. The post-fork goal is **at least** that baseline; new passes are expected and acceptable.

## Steps (as actually run on `promaxgb10-41b1`, 2026-05-04 — script needed adapting)

The original script assumed a project-local `.venv/bin/pytest`. Both repos are `uv`-managed without a checked-in `.venv`, and `mcp_server/` is a separate uv project with its own lockfile. The commands below were run instead and produced the captured baselines:

```bash
# Prerequisites: install dev deps so pytest is importable from each project's venv
cd ~/Projects/appmilla_github/graphiti && uv sync --extra dev
cd ~/Projects/appmilla_github/graphiti/mcp_server && uv sync   # mcp_server has no `dev` extra; main sync is enough

# 1. graphiti-core falkordb-tagged tests
cd ~/Projects/appmilla_github/graphiti
uv run pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/baseline-falkordb.txt

# 2. mcp_server tests (PYTHONPATH=tests so `from test_fixtures import …` resolves;
#    --timeout=10 overrides pytest.ini's 300s/test default so tests fail fast when
#    backends are unavailable instead of blocking the run)
cd ~/Projects/appmilla_github/graphiti/mcp_server
PYTHONPATH=tests uv run pytest tests/ --tb=line --timeout=10 2>&1 | tee /tmp/baseline-mcp.txt

# 3. guardkit workaround tests (worked unmodified)
cd ~/Projects/appmilla_github/guardkit
uv run pytest tests/knowledge/test_falkordb_workaround.py -v 2>&1 | tee /tmp/baseline-workaround.txt
```

**Source-tree equivalence to `d0913fe`**: every commit between `d0913fe` and the
HEAD this baseline was captured at (`0bcf01d Add patch 006`) only adds files
under `patches/`, `tasks/`, `docs/`, and `.claude/reviews/`. `git diff
d0913fe..HEAD -- graphiti_core/ mcp_server/src/ tests/ mcp_server/tests/`
produces no output, so the captured baseline is faithfully a "no patches
applied" run.

**Captured summary lines**:
- falkordb: `5 failed, 24 passed, 1 skipped, 381 deselected, 1 warning, 42 errors in 6.45s`
- mcp:      `32 failed, 11 passed, 2 errors in 150.60s` (pydantic ValidationError on `StdioServerParameters` — backends/config not present locally)
- workaround: `43 passed, 1 warning in 2.19s`

## Acceptance Criteria

- [x] `/tmp/baseline-falkordb.txt` contains pytest output for graphiti-core's falkordb-tagged tests against current head.
- [x] `/tmp/baseline-mcp.txt` contains pytest output for `mcp_server/tests/` against current head.
- [x] `/tmp/baseline-workaround.txt` contains pytest output for guardkit's `test_falkordb_workaround.py` against current head.
- [x] Each output file is non-empty and contains pytest's "passed/failed/error" summary line.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Mechanical plan" Step 0.
- AC-FORK-19 in parent.
- Review addendum: [TASK-FORK-PATCH-review-addendum-execution-flow.md](../../../.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md) §"Pre-application baseline capture".
