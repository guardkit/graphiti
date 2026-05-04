---
task_id: TASK-FORK-PATCH
mode: decision
depth: standard
reviewed_at: 2026-05-04
reviewer: claude-opus-4-7
fork_head: d0913fe (work/falkordb-fixes)
fork_version: 0.29.0
---

# Review Report: TASK-FORK-PATCH (decision mode, standard depth)

## Executive Summary

The task is **well-scoped, well-evidenced, and ready to execute** — the patches/ directory already contains three of the five graphiti-core fixes (bugs #5/#10/#11/#12/#13) as ready-to-apply unified diffs that all pass `git apply --check` against the current `0.29.0` head (`d0913fe`). The remaining gates are six explicit "TBD" decisions in the task file — four ownership/process decisions (1-4) and two patch-shape decisions (5-6). With one exception (Decision 1), every TBD has a clear right answer driven by evidence already on disk or in the knowledge graph; the decisions only feel open because nobody's typed the answer into the file yet.

**Headline recommendation**: lock all six decisions per the recommendations below, ship the guardkit fork at tag `v0.29.5-guardkit.1`, and treat this task as "decisions only — implementation already drafted." The 600-minute estimate is generous; with patches pre-built, realistic effort is 4-6 hours focused work on the GB10 (consumer pyproject updates and end-to-end verification dominate, not the patches themselves).

**Architecture score: 78/100.** Strong: evidence trail, audit completeness, patch quality. Weak: bugs #8/#9 still need cherry-picking (no patches drafted), and the staged `config-guardkit.yaml` foot-gun at `~/Projects/appmilla_github/graphiti-original/` should be discarded explicitly in the task file (currently only flagged in prose).

## Review Details

- **Mode**: Decision analysis
- **Depth**: Standard (1-2 hours equivalent)
- **Scope**: 6 open decisions + risk audit of the mechanical plan
- **Evidence sources**: task file, patches/, in-tree code (verified line-by-line), knowledge graph (`guardkit__project_decisions`, `architecture_decisions`)

## Findings

### F-01 — Fork is already at 0.29.0; Decision 1 is half-locked

`pyproject.toml` reports `version = "0.29.0"`, branch is `work/falkordb-fixes`, head is `d0913fe`. The task file describes Decision 1 as "TBD — pick a recent 0.29.x tag" but the practical situation is: the fork already exists, it's already on 0.29.0, and the patches are already verified against this exact tree. The remaining sub-decision is just "which tag string do we cut?" — not which version family.

**Severity**: low. **Implication**: just write down `v0.29.5-guardkit.1` (or similar) and move on.

### F-02 — Decisions 5 and 6 are de-facto pre-decided by the artefacts in this repo and the knowledge graph

- **Decision 5** (drop-filter vs escape-and-keep): patch [`patches/001-drop-fulltext-group-filter.patch`](../../patches/001-drop-fulltext-group-filter.patch) implements **drop-the-filter**. The patch is verified clean. The patches/README.md states this implements the audit's recommended approach. The in-tree consumer-side workaround at `guardkit/knowledge/falkordb_workaround.py:287-309` has been doing drop-the-filter for several months in production. There is no work to do on Decision 5 except write "drop-filter" into the task file.
- **Decision 6** (auto-detect vs explicit `openai_generic`): the in-flight diff at `~/Projects/appmilla_github/graphiti-original/mcp_server/src/services/factories.py` implements **auto-detect on `base_url`**. The knowledge graph confirms this was the established pattern as of 2026-04-03 ("The graphiti MCP server factory uses OpenAIGenericClient for non-OpenAI endpoints"). vLLM does not support the OpenAI Responses API — auto-detect on base_url is the correct routing logic. Approach B (explicit case) would force config migrations across study-tutor, guardkit, and jarvis with no compensating benefit before mid-May.

**Severity**: low. **Implication**: write "drop-filter" and "auto-detect" into the task file; both already have implementation artefacts.

### F-03 — Bugs #8 and #9 have no patches drafted yet

The patches/ directory covers #5, #10, #11, #12, #13 (five of thirteen audited bugs). Bug #6/#7 has the in-flight factories.py diff at `~/Projects/appmilla_github/graphiti-original/`. **Bugs #8 and #9 have no diffs anywhere in this repo** — the task tells you to cherry-pick from upstream PR #1170 (bug #8) and to re-derive from `guardkit/knowledge/falkordb_workaround.py:380-635` (bug #9) during the GB10 session.

This is the largest source of execution-time uncertainty. PR #1170 is described as "authored, not yet merged" — its mergeability against this fork's tree is not yet verified. The bug #9 fix in falkordb_workaround.py is 255 lines of monkey-patch code that needs to be re-shaped as an in-tree edit to `graphiti_core/search/search_utils.py`.

**Severity**: medium. **Implication**: pre-derive both before the GB10 session — drop them into `patches/` as `004-handle-multiple-group-ids-decorator.patch` and `005-edge-search-on-direct-endpoints.patch` so the GB10 session is purely apply-and-verify, not authoring. This protects the time budget and keeps the DDD demo and Kaggle deadline insulated from upstream-PR-mergeability surprises.

### F-04 — Consumer-side pin updates dominate the unestimated risk

Steps 5-7 of the mechanical plan update three consumer pyproject.tomls (study-tutor, guardkit, jarvis) and one shell script (`graphiti-mcp-build.sh`). The task names these but provides no diff samples. Realistic risk areas:

- **study-tutor**: pinned `>=0.29,<0.30`. The fork tag pin (`graphiti-core @ git+...@v0.29.5-guardkit.1#subdirectory=graphiti_core`) needs the `subdirectory=` qualifier because graphiti-core is a sub-package of the fork repo (verified: `graphiti_core/` lives at the fork root). Confirm `uv sync` accepts this URL syntax — `pip` does, `uv` is recent.
- **guardkit**: pinned `>=0.5.0` (loose). Update implies tightening — flag as a separate decision. The audit notes this is "due for a tightening anyway" but tightening is its own risk surface (every guardkit consumer of graphiti-core gets locked to the fork tag).
- **jarvis**: pinned `>=0.9,<1`. Lower priority per task notes.
- **graphiti-mcp-build.sh**: replaces `git clone https://github.com/getzep/graphiti.git` with the fork URL plus `--branch v0.29.5-guardkit.1`. Confirm the build script uses `git checkout` not `git clone --branch` because some old shells handle long branch flags inconsistently — but the fork uses tags, and `git clone --branch` accepts tags.

**Severity**: medium. **Implication**: pre-write the four consumer-side diffs as drafts before the GB10 session.

### F-05 — Stale-config foot-gun at `~/Projects/appmilla_github/graphiti-original/` is flagged but not commit-blocked

The "In-flight patch already drafted" section (lines 190-322 of the task) goes into commendable detail about why the staged `mcp_server/config/config-guardkit.yaml` is stale — Gemini-era, dead `:8001` embedder, wrong 1024-dim — and explicitly says "do NOT commit". The risk is that a fast-moving session at the GB10 might `git add .` the entire staged set and commit the stale yaml alongside the good factories.py diff. AC-FORK-16 captures this verbally.

**Severity**: medium. **Implication**: surface this as an explicit pre-commit checklist item, not just a section in the task narrative. Recommendation below in §Decision Matrix.

### F-06 — `transport_security` patch (#13) requires a separate guardkit-side env export

Patch [`003-mcp-early-host-binding.patch`](../../patches/003-mcp-early-host-binding.patch) reads `MCP_SERVER_HOST` at module load. For the fix to take effect in the GB10 deployment, `guardkit/scripts/graphiti-mcp.sh` must export `MCP_SERVER_HOST=0.0.0.0` to the container. The task file flags this in row 3 of the patches table ("also requires graphiti-mcp.sh to export MCP_SERVER_HOST=0.0.0.0"). Without that export, the patch is a no-op against the actual deployment — i.e. easy to miss during verification because the existing `graphiti-mcp-bootstrap.py` shim is still doing the work.

**Severity**: low (caught by AC-FORK-14 stretch goal, plus the bootstrap shim still works as a fallback). **Implication**: ensure the env export is added in the same commit as the bootstrap shim removal, not before, so the system never has both half-applied.

### F-07 — Bug #4 (group_id colon→dash migration) is shipped in 0.29.0 but its naming-convention follow-on isn't internal to this task

Bug #4 — `GroupIdValidationError` rejecting colons — is described in the task as "fixed in 0.29.0". This fork is at 0.29.0, so the validator change is in-tree. The downstream consequence (guardkit moved to underscore-only group_ids per `migrate-hyphens.py`) is **outside this task's scope** — the task correctly notes this. Worth a one-line explicit statement in FORK-NOTES.md so future readers don't conflate the colon-rejection fix with the dash-tokenisation fix from #5/#11.

**Severity**: low. **Implication**: documentation hygiene only; flag in AC-FORK-05.

### F-08 — Effort estimate 600 min likely high; risk window is bug #8/#9 derivation, not patch application

If patches 001-003 + the in-flight factories.py diff land cleanly (likely, given verification status), the bulk of the remaining work is bugs #8/#9 derivation (~2 hours focused if PR #1170 cherry-picks cleanly; up to 4 hours if it conflicts) plus consumer pyproject updates (~30 min) plus end-to-end verification (~1 hour). Realistic range: 4-6 hours. The 600-minute (10-hour) estimate already accounts for this, so this is an under-utilisation note, not a cost overrun risk.

**Severity**: informational.

## Decision Matrix — recommendations for the six open decisions

| # | Decision | Recommended | Confidence | Rationale |
|---|----------|-------------|------------|-----------|
| 1 | Fork from 0.28.x or 0.29.x | **0.29.x** | High | Fork already exists at 0.29.0 (`d0913fe`). Study-tutor pins `>=0.29,<0.30`. Single-version everywhere. The bug surface for #5 is identical in both 0.28 and 0.29, so no fix-quality argument for staying on 0.28. |
| 2 | Public or private | **Public** (`guardkit/graphiti`) | High | DDD South West talk gets a credible "we use a fork with these fixes" narrative. `pip install git+https://...` Just Works without auth plumbing. Private fork would force GH-token rotation across at least two CI surfaces (study-tutor venv install, GB10 docker image build). |
| 3 | Owner | **`guardkit` org** if it exists, else personal | High | Engineering-equivalent. URL stability favours org. |
| 4 | Tag vs branch pin | **Tag** (`v0.29.5-guardkit.1`) | High | Reproducible builds. Standard fork practice. Branch tip is mutable — not what consumers should pin to. Active dev still happens on a branch (e.g. `guardkit-fixes-0.29`); cut a fresh tag each shipping moment. |
| 5 | RediSearch fix shape | **Drop-the-filter** | High | Already implemented in [`patches/001-drop-fulltext-group-filter.patch`](../../patches/001-drop-fulltext-group-filter.patch) (clean apply). Already production-tested in `guardkit/knowledge/falkordb_workaround.py` for months. Fixes bugs #5 + #11 + #12 in one diff. Group isolation already enforced by multi-graph driver clone + Cypher WHERE clause. Knowledge graph confirms this is the established pattern. |
| 6 | Factory routing shape | **Auto-detect on `base_url`** (Approach A) | High | Already drafted in `~/Projects/appmilla_github/graphiti-original/`. Knowledge graph confirms "graphiti MCP server factory uses OpenAIGenericClient for non-OpenAI endpoints" since 2026-04-03. Zero config-schema churn — existing `provider: openai` configs Just Work. Reversible with one revert if we change our minds. Approach B blocks DDD demo on three consumer config migrations for no shipping benefit. |

## Recommendations beyond the six decisions

1. **Pre-draft patches 004 and 005** (bug #8 and bug #9) before the GB10 session. Drop them into `patches/` so the GB10 work is apply-and-verify only. Cherry-pick PR #1170 locally; re-shape `falkordb_workaround.py:380-635` against `graphiti_core/search/search_utils.py`. Each as its own commit, separately revertable. (Addresses F-03.)
2. **Pre-draft the four consumer-side diffs** (study-tutor pyproject, guardkit pyproject, jarvis pyproject, `graphiti-mcp-build.sh`). Stash them locally; apply during step 5-7 of the mechanical plan. (Addresses F-04.)
3. **Add an explicit pre-commit checklist item** to the task file under the mechanical plan: "before commit, confirm `mcp_server/config/config-guardkit.yaml` from the staged in-flight set is NOT included; only `config-local-neo4j.yaml` is." This converts the prose warning at task lines 259-308 into an actionable gate. (Addresses F-05.)
4. **Tightly couple bug #13 patch with `MCP_SERVER_HOST=0.0.0.0` export** in `guardkit/scripts/graphiti-mcp.sh`. Add a one-line note to AC-FORK-14 that the export must be added in the same commit as the bootstrap-shim removal. (Addresses F-06.)
5. **In FORK-NOTES.md, distinguish bug #4 (colon-rejection, fixed upstream in 0.29.0) from bug #5 (dash-tokenisation, fixed in this fork)** so readers don't conflate them. One sentence each. (Addresses F-07.)
6. **Stretch — fix the staged-but-stale upstream-tracker clone**: while you're on the GB10, `git -C ~/Projects/appmilla_github/graphiti-original/ stash` the staged set, fast-forward to current `origin/main`, and re-derive the factories.py diff cleanly against this fork's tree. Reduces the chance of confusion the next time someone goes spelunking in graphiti-original.
7. **Defer to post-DDD**: AC-FORK-14 (bug #13 + bootstrap-shim retirement) is correctly marked stretch. Don't try to land it under deadline pressure. The current bootstrap shim is functional and the deployment is live.

## Risk Register additions

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R-FORK-01 | PR #1170 conflicts on cherry-pick into the fork | Medium | Medium (extends GB10 session by 1-2h) | Pre-derive locally before the GB10 session (recommendation #1) |
| R-FORK-02 | Stale `config-guardkit.yaml` accidentally committed alongside good factories.py diff | Medium | High (silent foot-gun: wrong embedder dimensions → empty search results) | Pre-commit checklist item (recommendation #3) |
| R-FORK-03 | `MCP_SERVER_HOST=0.0.0.0` export missing from `graphiti-mcp.sh` after bootstrap-shim retirement | Low | High (HTTP 421 on every external request) | Same-commit coupling (recommendation #4) |
| R-FORK-04 | Consumer pyproject pin syntax mishandled by `uv sync` | Low | Medium (study-tutor blocked) | Test the pin syntax in a scratch venv before committing the pyproject change |

## Context Used

The following knowledge-graph items influenced this review:

- Fact (2026-04-03, `guardkit__project_decisions`): "The graphiti MCP server factory uses OpenAIGenericClient for non-OpenAI endpoints." → validates Decision 6 = auto-detect (Approach A).
- Fact (2026-04-03, `guardkit__project_decisions`): "OpenAIGenericClient uses the standard Chat Completions API response format." → confirms the routing target.
- Fact (2026-04-03, `guardkit__project_decisions`): "vLLM does not support the OpenAI Responses API." → root cause for bug #6/#7; the fork-side fix is the correct mitigation.
- Fact (2026-04-03, `guardkit__project_decisions`): "The factory bugs in TASK-GMO-004 have been fixed." → historical context; this fork-patch task is the current-cycle equivalent.
- Node (2026-04-19, `guardkit__project_decisions`): "Graphiti's role is to serve as the 'decision record'." → motivates AC-FORK-05 (FORK-NOTES.md as decision record alongside the patches).

## Verifications performed during this review

- `git apply --check` on each of `patches/001-*.patch`, `patches/002-*.patch`, `patches/003-*.patch` — all clean individually.
- `git apply --check` on all three together — clean.
- Read [`graphiti_core/driver/falkordb_driver.py:367-425`](graphiti_core/driver/falkordb_driver.py#L367-L425) — confirmed bugs #5/#11/#12 still present in current head; `sanitize` separator map confirms #10 scoped to backtick only (slashes, pipes, backslashes already stripped at lines 379-381).
- Read [`graphiti_core/driver/falkordb/operations/search_ops.py:80-120`](graphiti_core/driver/falkordb/operations/search_ops.py#L80-L120) — confirmed duplicate copy of the broken filter logic.
- Read [`mcp_server/src/services/factories.py:100-149`](mcp_server/src/services/factories.py#L100-L149) — confirmed bug #6/#7 (`base_url` not passed; `OpenAIClient` hardcoded; no auto-detect).
- Confirmed `pyproject.toml` `version = "0.29.0"` and current head `d0913fe` on `work/falkordb-fixes`.

## Decision Summary (one-liner per decision)

1. **Fork from 0.29.x.** Already done — fork is at 0.29.0.
2. **Public fork.** Enables the DDD talk story; simplifies pip-install plumbing.
3. **`guardkit` org** (or personal if org doesn't exist). Engineering-equivalent.
4. **Tag-and-pin** at `v0.29.5-guardkit.1`. Reproducible.
5. **Drop-the-filter** for RediSearch fulltext. Patch already drafted; matches in-tree workaround; fixes #5+#11+#12 together.
6. **Auto-detect on `base_url`** for factory routing. Already drafted in graphiti-original; matches established knowledge-graph decision.
