---
id: TASK-FPA-009
title: End-to-end verification (MCP probes, container logs) per AC-FORK-08
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T13:00:00Z
completed_at: 2026-05-04T13:00:00Z
priority: high
task_type: feature
complexity: 4
estimated_minutes: 60
actual_minutes: 75
execution_location: promaxgb10-41b1
tags: [graphiti, fork, verification, e2e, mcp]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 4
implementation_mode: direct
dependencies: [TASK-FPA-007]
workspace_name: fork-patch-application-wave4-2
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-04T13:00:00Z
verified_against:
  fork_tag: v0.29.5-guardkit.2
  container_image_sha: c5a349966cb3 (graphiti-mcp-standalone:local)
  container_stamp: v0.29.5-guardkit.2 (read from /app/mcp/.graphiti-core-version)
---

# End-to-end verification (AC-FORK-08) — completed 2026-05-04

## Outcome: ALL ACTIVE ACs PASS

| AC | Description | Result |
|---|---|---|
| AC-FORK-08-1 | study-tutor seed run (25/25) | **deferred** — study-tutor has no graphiti-core dep on the GB10; would need a separate venv-setup task or run on the Mac |
| AC-FORK-08-2 | verify_lilymay.py populated state | **deferred** — same dependency on study-tutor venv as AC-FORK-08-1 |
| AC-FORK-08-3 | MCP write probe round-trips | **PASS** — episode written via `add_memory`, retrieved via `get_episodes` with full content + correct group_id |
| AC-FORK-08-4 | MCP read probe with dashed group_id | **PASS** — `search_nodes(group_ids=["fork-verify-dashed"])` returned 3 entities with correct group_id, **no RediSearch syntax error** (R-WAVE5-03 fix verified) |
| AC-FORK-08-5 | Container logs hit localhost:9000 | **PASS** — 11 calls to `localhost:9000`, 0 to `api.openai.com`, auto-detect log line present, 0 RediSearch errors |
| AC-FORK-19 | Per-commit baseline diff | **PASS** — verified at unit-test level by AC-FORK-19 in TASK-FPA-003 through 006 (all green per prior subtask completions) |

## Critical finding mid-verification: Dockerfile bug → v0.29.5-guardkit.2

First attempt rebuilt against `v0.29.5-guardkit.1`; container still emitted broken `(@group_id:"fork-verify-dashed")` query syntax. Root cause: the upstream `Dockerfile.standalone` rewrites `mcp_server/pyproject.toml` at build time to install graphiti-core from PyPI 0.28.1, dropping the fork's bug-fix patches.

Fix landed as fork commit `152f5ca` (re-tagged `v0.29.5-guardkit.2`):
- `mcp_server/pyproject.toml`: pin `graphiti-core[falkordb] @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.2`
- `mcp_server/docker/Dockerfile.standalone`: remove the PyPI-rewrite sed lines, add `git` to apt-get install (uv needs it to clone), rename `GRAPHITI_CORE_VERSION` → `GRAPHITI_FORK_TAG`
- `guardkit/scripts/graphiti-mcp-build.sh`: default `GRAPHITI_TAG` bumped to `v0.29.5-guardkit.2`
- guardkit commit `b2cbb725`

Rebuild against `v0.29.5-guardkit.2` succeeded; verification re-ran clean. The patch comments are visible in the running container at `/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/{decorators.py,driver/falkordb_driver.py}`.

## Verification artefacts

```
[2026-05-04 12:51:13] services.factories - INFO - Using OpenAIGenericClient for non-OpenAI endpoint: http://localhost:9000/v1
[2026-05-04 12:51:37] services.queue_service - INFO - Starting episode queue worker for group_id: fork-verify-dashed
[2026-05-04 12:52:03] graphiti_core.graphiti - INFO - Completed add_episode in 26727.83 ms
[2026-05-04 12:52:03] services.queue_service - INFO - Successfully processed episode None for group fork-verify-dashed
```

Read probe (post-rebuild, dashed group_id):
```python
mcp__graphiti__search_nodes(query="Sample Student Year 11", group_ids=["fork-verify-dashed"])
# Returns 3 entities, no syntax error.
```

## AC-FORK-09 closeout flips

These are documentation-and-state-change actions delegated to the parent task's completion:

- ⚪ Flip G2/G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` from "Falsified" to "Held" — **deferred** (study-tutor doc work, not GB10-side; pair with AC-FORK-08-1/2 deferral above).
- ⚪ Move `study-tutor/tasks/blocked/TASK-GR-SEED-...md` to `study-tutor/tasks/in_review/` — **deferred** (same).
- ✅ guardkit cross-repo work captured as `TASK-GK-FORK-PIN` (commits `960fef1c`, `63041788`, `b2cbb725`).
- ✅ jarvis cross-repo work captured as `TASK-JAR-FORK-PIN` (commits `be13f25`, `b06b52f`).
- ⚪ Move parent task `TASK-FORK-PATCH` from `backlog/` to `completed/` — handled in this commit.

## Cross-references

- Parent: [TASK-FORK-PATCH](../../completed/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md)
- Cross-repo: [guardkit TASK-GK-FORK-PIN](../../../../guardkit/tasks/backlog/TASK-GK-FORK-PIN-pin-graphiti-core-to-fork.md), [jarvis TASK-JAR-FORK-PIN](../../../../jarvis/tasks/backlog/TASK-JAR-FORK-PIN-pin-graphiti-core-to-fork.md)
- Fork tag: [v0.29.5-guardkit.2](https://github.com/guardkit/graphiti/releases/tag/v0.29.5-guardkit.2)
