# Implementation Guide — Fork Patch Application

**Feature ID**: FEAT-FPA-2026-05
**Parent review**: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md)
**Review report**: [.claude/reviews/TASK-FORK-PATCH-review-report.md](../../../.claude/reviews/TASK-FORK-PATCH-review-report.md)
**Review addendum**: [.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md](../../../.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md)
**Execution location**: `promaxgb10-41b1` (single-machine session)
**Total estimated effort**: ~290 minutes (≈5 hours focused)

## Overview

This implementation lands six commits on a fork of `getzep/graphiti` at version 0.29.0 (commit `56cf7b3`), tags the release, and verifies the end-to-end behaviour via study-tutor's seed pipeline and MCP probes. All six locked decisions from the parent review's decision-mode analysis are honoured.

## Wave breakdown

```
Wave 1 — Repo setup (parallel-safe; both must complete before Wave 2)
├── TASK-FPA-001 — Capture pre-application baselines (15 min, direct)
└── TASK-FPA-002 — Push fork to GitHub (30 min, manual)

Wave 2 — Patch application (STRICTLY SEQUENTIAL — each commit's baseline diff
                            must pass before the next commit lands)
├── TASK-FPA-003 — Apply patches 001+002+003 (commit 1, 30 min, direct)
├── TASK-FPA-004 — Apply factories.py auto-detect (commit 2, 60 min, task-work)
├── TASK-FPA-005 — Apply patch 004 (commit 3, 20 min, direct)
└── TASK-FPA-006 — Apply patch 005 (commit 4, 30 min, direct)

Wave 3 — Tag and publish
└── TASK-FPA-007 — Tag v0.29.5-appmilla.1 + push (15 min, manual)

Wave 4 — Documentation and verification (sequential, can be parallelised
                                          with the cross-repo work below)
├── TASK-FPA-008 — Write FORK-NOTES.md (30 min, direct)
└── TASK-FPA-009 — End-to-end verification (60 min, direct)
```

**Total**: 290 minutes ≈ 5 hours focused work.

## Why mostly sequential, not parallel

This task has `execution_location: promaxgb10-41b1` because:

1. The MCP container deployment lives on the GB10.
2. The verification suite needs the live FalkorDB at `whitestocks:6379` and llama-swap at `localhost:9000`.
3. Each patch-application commit's baseline diff (AC-FORK-19) must clear before the next lands, so commits 1→4 are strictly sequential.

Conductor parallelism is therefore **not recommended** for this feature. The waves above describe logical groupings, not parallel execution. Within a wave, only Wave 1's TASK-FPA-001 and TASK-FPA-002 are independent enough to run side-by-side in two terminal tabs if desired.

## Cross-repo follow-ups (file separately, NOT in this graphiti repo)

After Wave 3 completes (tag exists and is pushed), file these in their own task systems:

| Repo | Action | Suggested task ID |
|------|--------|-------------------|
| study-tutor | Update `pyproject.toml` to pin `graphiti-core @ git+https://github.com/appmilla/graphiti.git@v0.29.5-appmilla.1#subdirectory=graphiti_core`; refresh venv; run baseline test suite | `TASK-STU-FORK-PIN` |
| guardkit | Same `pyproject.toml` update; update `scripts/graphiti-mcp-build.sh` to clone fork at the tag; add `MCP_SERVER_HOST=0.0.0.0` export to `scripts/graphiti-mcp.sh`; rebuild MCP container with `--no-cache` | `TASK-GK-FORK-PIN` |
| jarvis | Same `pyproject.toml` update | `TASK-JAR-FORK-PIN` |
| guardkit | (Optional, post-verification) Remove `apply_falkordb_workaround()` from `guardkit/knowledge/graphiti_client.py:62-63` once the fork eliminates the need; remove the corresponding monkey-patch at `falkordb_workaround.py` | `TASK-GK-RETIRE-WORKAROUND` |
| guardkit | (Optional) Refresh `docs/guides/graphiti-gb10-deployment.md` for the post-2026-04-29 llama-swap topology (per AC-FORK-18) | `TASK-GK-REFRESH-RUNBOOK` |

These are required for TASK-FPA-009 (end-to-end verification) to pass. If any are not yet in place when starting TASK-FPA-009, that subtask blocks until they land.

## Locked decisions in scope

The six TASK-FORK-PATCH decisions (locked 2026-05-04 per the review) are:

1. **0.29.x**: fork is at 0.29.0, head `d0913fe`. No version selection needed.
2. **Public**: `appmilla/graphiti` (or personal fallback if org doesn't exist).
3. **`appmilla` org**, else personal account.
4. **Tag-and-pin**, releasing as `v0.29.5-appmilla.1`.
5. **Drop-the-filter** for RediSearch fulltext (patch 001).
6. **Auto-detect on `base_url`** for factory routing (factories.py commit 2).

Each subtask references the relevant decision in its body.

## Regression-safety contract (AC-FORK-19)

**Pre-application** (TASK-FPA-001):
- Capture three pytest output files: `/tmp/baseline-{falkordb,mcp,workaround}.txt`.

**Per-commit** (TASK-FPA-003 through 006):
- After each commit, re-run the relevant pytest suites with `SHA=$(git rev-parse --short HEAD)` and write to `/tmp/post-${SHA}-*.txt`.
- `diff /tmp/baseline-*.txt /tmp/post-${SHA}-*.txt` — if any new failures, **revert the commit, file a blocker subtask, and pause**.
- New passes are expected (especially for guardkit's workaround test suite after patches 004/005 land) and are acceptable.

**Final** (TASK-FPA-009):
- Plus the live smoke tests (seed run, verify_lilymay.py, MCP probes, container logs).

## Patch interaction notes (from review addendum)

- **Patches 001 + 004 are commutatively safe.** No application order produces *worse* output than upstream. Worst case for any partial state is `[]`.
- **Patch 005 changes `edge_bfs_search` semantics**: original undirected `MATCH (n)-[e]-(m)` returned each edge twice with swapped endpoints. Patch returns each edge once in directed (source → target) form. Result-count drops by ~2× for that call; latent bug fix, not a regression. Document in FORK-NOTES.md (TASK-FPA-008).
- **Patch 003 needs MCP_SERVER_HOST env export** in `guardkit/scripts/graphiti-mcp.sh` for the fix to take effect against the live deployment. That export and the bootstrap-shim retirement must land in the same guardkit commit (filed separately as `TASK-GK-FORK-PIN`).

## What can go wrong (named risks)

From [.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md](../../../.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md) §"Regression Matrix":

| Risk | Mitigation | Detection |
|------|------------|-----------|
| Patch 001 `*` wildcard returns noise instead of crash for all-stopword queries | Behaviour change is intentional; documented in FORK-NOTES.md | Unit test would need to cover degenerate queries |
| Patch 002 search-miss against legacy backtick-tainted index | Theoretical only — guardkit pre-strips since months ago; production has no backtick tokens | Re-run guardkit seed against backtick-rich corpus |
| Patch 003 + missing env export → HTTP 421 on Tailscale clients | Tied to TASK-GK-FORK-PIN: same-commit env export | `curl -H 'Host: promaxgb10-41b1:8004' http://...:8004/mcp/` returns 200 |
| factories.py + Azure-fronted proxy expecting Responses API | Theoretical only — graphiti-core's structured-output use case is Chat-Completions-compatible | Auto-detect log line in container logs |
| Patch 005 edge_bfs_search consumer expects 2× rows | Latent bug fix — document in FORK-NOTES.md | Existing test_falkordb_workaround.py tests cover this shape |

## Task execution order (recommended)

```
1. TASK-FPA-001  ──┐  Wave 1 (parallel-safe)
2. TASK-FPA-002  ──┘
3. TASK-FPA-003  ──┐  Wave 2 (sequential)
4. TASK-FPA-004    │
5. TASK-FPA-005    │
6. TASK-FPA-006  ──┘
7. TASK-FPA-007       Wave 3
   ↓
   [File cross-repo follow-ups: TASK-STU-FORK-PIN, TASK-GK-FORK-PIN, TASK-JAR-FORK-PIN]
   ↓
   [Wait for cross-repo follow-ups to complete]
   ↓
8. TASK-FPA-008  ──┐  Wave 4 (sequential)
9. TASK-FPA-009  ──┘
```

## Definition of done (this feature)

The feature is complete when:

- All nine subtasks (TASK-FPA-001 through 009) are in `tasks/completed/`.
- The fork tag `v0.29.5-appmilla.1` is pushed and pinnable.
- All four AC-FORK-08 sub-criteria pass in the live verification.
- AC-FORK-09 flips are actioned (G2/G3 to Held in study-tutor; cross-repo task moves).
- AC-FORK-19's final post-tag baseline diff shows no new failures.
- Parent TASK-FORK-PATCH is moved to `tasks/completed/`.
