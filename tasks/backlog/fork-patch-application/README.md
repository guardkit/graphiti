# Fork Patch Application — feature subfolder

**Feature ID**: FEAT-FPA-2026-05
**Parent**: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md)
**Status**: ready (all nine subtasks in `backlog/`, awaiting GB10 session start)
**Estimated effort**: ~290 minutes (≈5 hours focused work)

## Problem statement

`getzep/graphiti` (the upstream library this fork is based on) has at least 13 audit-confirmed defects affecting the guardkit deployment stack across study-tutor, guardkit, jarvis, and the GB10's MCP container. Five of those defects (#5, #10, #11, #12, #13) live in graphiti-core's FalkorDB driver and the graphiti-mcp host-binding init order; two more (#6, #7) live in the MCP server's LLM-client factory routing; two more (#8, #9) live in the multi-group decorator and the edge-search Cypher.

Patches in consumer code (study-tutor, guardkit, jarvis venvs + the GB10 MCP container) don't propagate — bugs do. The audit's strategic decision (2026-05-03): fork getzep/graphiti, apply the known fixes in one place, point all consumers at the fork.

## Solution approach

Land six commits on a fork branch (`guardkit-fixes-0.29`):

1. **Commit 1** — Patches 001+002+003 (RediSearch drop-filter + sanitize backtick + MCP host binding)
2. **Commit 2** — factories.py auto-detect (bug #6/#7), derived from the in-flight diff at `~/Projects/appmilla_github/graphiti-original/`
3. **Commit 3** — Patch 004 (handle_multiple_group_ids decorator, bug #8)
4. **Commit 4** — Patch 005 (edge search startNode/endNode reshape, bug #9)
5. **Commit 5** — Tag `v0.29.5-guardkit.1`
6. **Commit 6** — `FORK-NOTES.md` documentation (post-tag, optional)

Each patch-application commit runs an AC-FORK-19 baseline diff against pre-application baselines so any new test failure bisects cleanly.

After the tag lands, file follow-up tasks in study-tutor, guardkit, and jarvis to update their `pyproject.toml` pins to the fork tag. Then run the AC-FORK-08 end-to-end verification (study-tutor seed → 25/25 writes; verify_lilymay.py → populated state; MCP write+read probes; container logs hit `localhost:9000` not `api.openai.com`).

## Subtasks (9 total)

| ID | Title | Wave | Mode | Min |
|----|-------|------|------|-----|
| [TASK-FPA-001](TASK-FPA-001-capture-baselines.md) | Capture pre-application test baselines | 1 | direct | 15 |
| [TASK-FPA-002](TASK-FPA-002-push-fork-to-github.md) | Push fork to GitHub (`guardkit/graphiti`) | 1 | manual | 30 |
| [TASK-FPA-003](TASK-FPA-003-apply-redisearch-sanitize-mcp-host-patches.md) | Apply patches 001+002+003 (commit 1) | 2 | direct | 30 |
| [TASK-FPA-004](TASK-FPA-004-apply-factories-auto-detect.md) | Apply factories.py auto-detect (commit 2) | 2 | task-work | 60 |
| [TASK-FPA-005](TASK-FPA-005-apply-decorator-patch.md) | Apply patch 004 (commit 3) | 2 | direct | 20 |
| [TASK-FPA-006](TASK-FPA-006-apply-edge-search-patch.md) | Apply patch 005 (commit 4) | 2 | direct | 30 |
| [TASK-FPA-007](TASK-FPA-007-tag-and-push-release.md) | Tag `v0.29.5-guardkit.1` + push | 3 | manual | 15 |
| [TASK-FPA-008](TASK-FPA-008-write-fork-notes.md) | Write FORK-NOTES.md | 4 | direct | 30 |
| [TASK-FPA-009](TASK-FPA-009-end-to-end-verification.md) | End-to-end verification (AC-FORK-08) | 4 | direct | 60 |

## Execution

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for:

- Wave-by-wave execution order
- Why this feature is sequential, not parallel (single execution machine, baseline-diff dependency)
- Cross-repo follow-up tasks (study-tutor, guardkit, jarvis pyproject pins)
- Regression-safety contract (AC-FORK-19 baseline diff per commit)
- Patch interaction notes from the review addendum
- Definition of done

To start: invoke `/task-work TASK-FPA-001` (Wave 1 first task) on the GB10.

## Provenance

- Created from `/task-review TASK-FORK-PATCH --mode=decision --depth=standard --no-questions` followed by `[R]evise` (deeper trace) and `[I]mplement`.
- Six decisions locked in the parent task on 2026-05-04 per the review report's recommendations.
- Patches 004 and 005 pre-drafted on 2026-05-04 as part of the implement flow; verified clean apply against `d0913fe`.
- Subtask structure (this folder) created on 2026-05-04 to feed `/task-work`.

## Related work (cross-repo, not subtasks of this feature)

- **study-tutor** TASK-GR-SEED — surfaced bugs #5/#11/#12 (R-WAVE5-03)
- **guardkit** TASK-INF-5054 — full spec for bugs #6/#7
- **guardkit** TASK-INF-5053 — surfaced the responses.parse / base_url ignore bugs
- **guardkit** TASK-REV-661E — surfaced bug #10 (sanitize gaps)
- **guardkit** TASK-REV-84A7 — llm_max_tokens cap rationale (orthogonal, not in scope)
