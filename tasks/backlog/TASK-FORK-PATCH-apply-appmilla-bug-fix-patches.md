---
id: TASK-FORK-PATCH
title: Apply appmilla bug-fix patches to graphiti fork (RediSearch dash-escape + openai_generic factory)
status: review_complete
created: 2026-05-03T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 4
estimated_minutes: 600
execution_location: promaxgb10-41b1
tags: [graphiti, fork, falkordb, redisearch, mcp, infra]
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: comprehensive (revised)
  score: 82
  findings_count: 8
  recommendations_count: 7
  diagrams_count: 13
  decision: implement-with-locked-decisions
  report_path: .claude/reviews/TASK-FORK-PATCH-review-report.md
  addendum_path: .claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md
  completed_at: 2026-05-04T00:00:00Z
  regression_confidence: high (95%+)
  decisions_recommended:
    1: 0.29.x (fork already at 0.29.0)
    2: public (appmilla/graphiti)
    3: appmilla org (or personal)
    4: tag-and-pin (v0.29.5-appmilla.1)
    5: drop-the-filter (patch 001 already drafted)
    6: auto-detect on base_url (Approach A, already drafted in graphiti-official)
---

# Apply appmilla bug-fix patches to graphiti fork (RediSearch dash-escape + openai_generic factory)

**PRIORITY**: high
**TASK_TYPE**: feature
**COMPLEXITY**: 4
**ESTIMATED_MINUTES**: 600 (8-10 hours focused work, executed on `promaxgb10-41b1` directly — original 240 estimate was based on the 2-row punchlist before the audit surfaced bugs #8-#13 and the in-flight `openai_generic` diff)
**TAGS**: graphiti, fork, falkordb, redisearch, mcp, infra
**EXECUTION_LOCATION**: promaxgb10-41b1 (work directly on the GB10, not via SSH from a Mac dev machine — same rationale as guardkit's TASK-INF-5054)

---

## Why this fork exists

Counting bugs across the appmilla graphiti integration:

1. graphiti-core LLM client defaults to OpenAI (silent 401 if API_KEY=not_needed) — fixed in study-tutor Wave 2 wiring
2. graphiti-core Read API mismatch (`search_nodes` doesn't exist on `Graphiti` class) — worked around with `_read_student_partition` seam in study-tutor `queries.py`
3. graphiti-core Write API mismatch (`add_episode` kwargs wrong) — worked around with `_add_episode_kwargs` helper in study-tutor `async_write.py`
4. graphiti-core `GroupIdValidationError` rejects colons → forced format migration colon→dash (commit a210472)
5. **graphiti-core RediSearch dashes-as-NOT — upstream attempted fix at `falkordb_driver.py:406-410` is broken; the comment claims to escape hyphens but double-quote wrap doesn't actually escape dashes in RediSearch syntax. Bug present in 0.28.x AND 0.29.x.** Discovered 2026-05-03 during TASK-GR-SEED Wave 5 retry; documented in `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry — TASK-GR-SEED run 5 — 2026-05-03 (afternoon)". Risk-register entry R-WAVE5-03.
6. graphiti-mcp `factories.py` `openai` branch silently ignores `api_url` → falls through to api.openai.com and 401s. Filed as guardkit TASK-INF-5054.
7. graphiti-core `OpenAIClient` calls `responses.parse()` instead of `chat.completions.create` → 404 against local OpenAI-compatible servers. Compounds with #6; the TASK-INF-5054 fix uses `OpenAIGenericClient` to address both.

That's 7 distinct upstream defects across two graphiti-core minor versions. Patches in consumer code (study-tutor/guardkit/jarvis venvs + the GB10 MCP container) don't propagate — bugs do.

**Strategic decision (2026-05-03)**: fork getzep/graphiti, apply known fixes in one place, point all consumers (study-tutor, guardkit, jarvis pyproject.tomls + the graphiti-mcp-build.sh clone target) at the fork. Ship that for the DDD South West talk (mid-May) and the Kaggle hackathon submission for study-tutor. Defer the larger "shrink graphiti's role or replace entirely" research to after mid-May.

## Punchlist — the patches that need to land in this fork

| # | Fix | File(s) | Source task |
|---|-----|---------|-------------|
| 1 | RediSearch dash-escape — replace double-quote wrap with brace-wrap (`{group_id}`, RediSearch treats as opaque) OR backslash-escape (`group\-id`). Apply to BOTH call sites. | `graphiti_core/driver/falkordb_driver.py` lines 406-410 (`build_fulltext_query` method on `FalkorDriver`) AND `graphiti_core/driver/falkordb/operations/search_ops.py` lines 105-107 (standalone `_build_falkor_fulltext_query` function — duplicated code) | study-tutor TASK-GR-SEED (R-WAVE5-03) — see `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry" |
| 2 | `openai_generic` factory branch — pass `base_url`, use `OpenAIGenericClient` instead of `OpenAIClient`. Add new `case 'openai_generic':` alongside existing `openai`, `groq` cases. Also add the matching YAML schema entry for `providers.openai_generic` (api_key + api_url) wherever the config model is defined (likely under `mcp_server/src/config/...` or `mcp_server/src/services/config.py`). | `mcp_server/src/services/factories.py` plus the config-model file (search for `class OpenAIProvider` or `providers.openai`) | guardkit TASK-INF-5054 — full patch shape already specced in that task file |

The Wave 2 fixes (LLM/embedder wiring in `get_client`, the `_read_student_partition` seam, the `_add_episode_kwargs` helper) **stay in consumer code** — they're not bugs in graphiti-core, they're consumer wiring choices around graphiti-core's API surface. Don't try to push those upstream into this fork.

### Pre-built patches available at [`patches/`](../../patches/) (drafted 2026-05-03)

Three of the audit-surfaced fixes are already drafted as ready-to-apply unified diffs in [`patches/`](../../patches/) at the fork repo root. Each was verified against the fork's current 0.29.0 main with `git apply --check`:

| Patch | Bugs covered | Apply step |
|-------|--------------|------------|
| [`patches/001-drop-fulltext-group-filter.patch`](../../patches/001-drop-fulltext-group-filter.patch) | #5 + #11 + #12 (the audit's recommended **drop-the-filter** approach for Decision 5) | `git apply patches/001-drop-fulltext-group-filter.patch` after Decision 5 = drop-filter is locked |
| [`patches/002-extend-sanitize-strip-backtick.patch`](../../patches/002-extend-sanitize-strip-backtick.patch) | #10 (only backtick remains missing from `sanitize()` in 0.29.0; slashes/pipes/backslashes already in upstream's strip list) | `git apply patches/002-extend-sanitize-strip-backtick.patch` |
| [`patches/003-mcp-early-host-binding.patch`](../../patches/003-mcp-early-host-binding.patch) | #13 (read `MCP_SERVER_HOST` env var at module load, pass to FastMCP construction so transport_security freezes against the right allow-list) | `git apply patches/003-mcp-early-host-binding.patch` — also requires `graphiti-mcp.sh` to export `MCP_SERVER_HOST=0.0.0.0` for the bootstrap shim to be retirable |

Suggested commit messages and full apply instructions are in [`patches/README.md`](../../patches/README.md). The remaining fixes (bugs #6/#7 via the in-flight `openai_generic` diff at `~/Projects/appmilla_github/graphiti-official/`, bug #8 via upstream PR #1170, bug #9 via upstream issue #1272 / `falkordb_workaround.py:380-635`) still need to be derived/cherry-picked during the GB10 session.

## Decisions to lock in before patching starts

1. **Which version to fork from?** Local clone is at 0.28.2; study-tutor venv pins `>=0.29,<0.30`. The bug surface for #1 is identical in both versions (verified: both `falkordb_driver.py:406-410` files have the same broken double-quote escape).
   - **Recommended: standardise on 0.29.x** — pick a recent tag, fork from there, rebuild the MCP container against it. Single version everywhere. Bigger upfront move (MCP container upgrade) but no two-branch maintenance burden during DDD prep.
   - Alternative: maintain two branches `appmilla-0.28.x` and `appmilla-0.29.x`. More maintenance overhead.
   - **DECISION (LOCKED 2026-05-04)**: **0.29.x** — fork is already at 0.29.0 (`d0913fe` on `work/falkordb-fixes`). Cut tag `v0.29.5-appmilla.1` after the fix-commit lands. Rationale: study-tutor pin already `>=0.29,<0.30`, single-version policy is operationally simpler, all five drafted patches verified against this exact tree.

2. **Public or private fork?** Affects:
   - **DDD talk story**: public fork enables credible "we use a fork of graphiti with these fixes" narrative. Private fork means talk says "we use graphiti" with no asterisk.
   - **Pip install mechanics**: public is `pip install git+https://github.com/...` straight up. Private needs auth (GH token in env, deploy keys for docker builds). More moving parts.
   - **Recommended: public**, named clearly (e.g. `appmilla/graphiti` with branch `appmilla-fixes-0.29`).
   - **DECISION (LOCKED 2026-05-04)**: **public**. Rationale: enables DDD South West talk narrative; `pip install git+https://...` works without auth plumbing; avoids GH-token rotation across two CI surfaces (study-tutor venv install, GB10 docker image build).

3. **Where does the fork live?** Github org `appmilla` (if exists) or personal account. Engineering-equivalent; affects only URL.
   - **DECISION (LOCKED 2026-05-04)**: **`appmilla` org if it exists, else personal account**. Confirm during the GB10 session step 1 (`gh repo view appmilla/graphiti` to check). URL stability favours org; engineering-equivalent if not.

4. **Tag-and-pin or branch-and-pin?** Consumers pin via tag (`@v0.29.5-appmilla.1` — reproducible). Active dev happens on a branch. Standard fork practice: cut a tag when shipping.
   - **DECISION (LOCKED 2026-05-04)**: **tag-and-pin** at `v0.29.5-appmilla.1`. Rationale: reproducible builds; standard fork practice. Active dev on `appmilla-fixes-0.29` branch; cut a fresh tag at each shipping moment. Branch tip is mutable — never what consumers should pin to.

## Mechanical plan (11 steps, execute on the GB10)

0. **Capture pre-application baselines** so any regression bisects cleanly to a single landed patch (added 2026-05-04 per task-review addendum, AC-FORK-19):

   ```bash
   cd ~/Projects/appmilla_github/graphiti
   .venv/bin/pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/baseline-falkordb.txt
   .venv/bin/pytest mcp_server/tests/ --tb=line 2>&1 | tee /tmp/baseline-mcp.txt

   # And against guardkit's monkey-patch test suite (currently runs on un-forked graphiti-core)
   cd ~/Projects/appmilla_github/guardkit
   .venv/bin/pytest tests/knowledge/test_falkordb_workaround.py -v 2>&1 | tee /tmp/baseline-workaround.txt
   ```

   Re-run the same commands after **each** patch commit, with output to `/tmp/post-${COMMIT_SHA:0:7}-*.txt`, and `diff` against the baseline. Any new failure must bisect to a single landed patch — that is the AC-FORK-19 contract.

1. Push the local `~/Projects/appmilla_github/graphiti/` clone to the github fork (or fresh-fork from upstream + apply patches if cleaner).
2. On a fix branch (`appmilla-fixes-0.29` or similar), apply the patches in this order (each as its own commit so they are independently revertable; bisect-safe per addendum execution-flow trace):
   - **Commit 1**: `git apply patches/001-drop-fulltext-group-filter.patch patches/002-extend-sanitize-strip-backtick.patch patches/003-mcp-early-host-binding.patch` (the three RediSearch / sanitize / MCP-host fixes — already drafted, all verified clean apply against `d0913fe`).
   - **Commit 2**: apply the `factories.py` auto-detect diff per Decision 6 (rebase + cherry-pick from `~/Projects/appmilla_github/graphiti-official/`). Per addendum Diagram 13 the diff is +14/-0 lines; no schema migration.
   - **Commit 3**: `git apply patches/004-handle-multiple-group-ids-decorator.patch` (bug #8 — drafted 2026-05-04, derived from upstream PR #1170).
   - **Commit 4**: `git apply patches/005-edge-search-direct-endpoints.patch` (bug #9 — drafted 2026-05-04, derived from `guardkit/knowledge/falkordb_workaround.py:380-635` reshape).
   - After each commit, re-run the step 0 baseline diff. **Stop and bisect immediately** if any new failure appears.
3. (folded into step 2, commit 2)
4. Tag the final commit (e.g. `v0.29.5-appmilla.1`).
5. Update `pyproject.toml` in study-tutor: replace `"graphiti-core>=0.29,<0.30"` with `"graphiti-core @ git+https://github.com/appmilla/graphiti.git@v0.29.5-appmilla.1#subdirectory=graphiti_core"`. Refresh venv (`uv sync` or equivalent).
6. Same update in guardkit + jarvis pyproject.tomls (probably opportunistic, not all at once — guardkit is `>=0.5.0` loose pin, jarvis is `>=0.9,<1`; both are due for a tightening anyway).
7. Update `~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-build.sh` to clone from the fork at the tag (replace `git clone https://github.com/getzep/graphiti.git` with the fork URL + `--branch v0.29.5-appmilla.1`).
8. Rebuild MCP image on GB10: `./scripts/graphiti-mcp-build.sh --no-cache` then `./scripts/graphiti-mcp.sh` to restart.
9. Verify end-to-end:
   - Re-run the seed: `cd ~/Projects/appmilla_github/study-tutor && .venv/bin/python scripts/seed_student_model.py` — expect 25/25 writes succeed (no RediSearch syntax errors), `succeeded_writes=25` in summary.
   - Run `verify_lilymay.py`: expect populated `ac_seed_03_get_student_state` (year_group=11, target_grade='8', non-empty subjects, non-empty topic_confidences) and non-empty `ac_seed_02_student_lilymay_nodes`.
   - MCP probe (write): `mcp__graphiti__add_memory(name="fork-verify", episode_body="...", group_id="guardkit__test_fork", source="text")` then wait ~10s then `mcp__graphiti__get_episodes(group_ids=["guardkit__test_fork"])` — expect episode retrievable (TASK-INF-5054 fix verified).
   - MCP probe (read with dashed group_id): `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` — expect populated Student entity, NO RediSearch syntax error (R-WAVE5-03 fix verified).
   - Check container logs: `docker logs graphiti-mcp` — confirm LLM calls hit `localhost:9000` not `api.openai.com`.
10. If green:
    - Flip G2/G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` from "Falsified" to "Held" with evidence excerpts (per AC-SEED-05's exact format, already documented in TASK-GR-SEED).
    - Move `study-tutor/tasks/blocked/TASK-GR-SEED-...md` to `tasks/in_review/` or `tasks/completed/` as appropriate.
    - Move `guardkit/tasks/backlog/TASK-INF-5054-...md` to `tasks/completed/2026-05/`.
    - Move this task to `completed/`.
    - Commit + push the fork tag and the consumer pyproject.toml updates.

## Acceptance Criteria

- [ ] **AC-FORK-01** — Decisions 1-4 above are explicitly captured in this task file (which version, public/private, where, tag-vs-branch). Update this section with the chosen values before starting work.
- [ ] **AC-FORK-02** — RediSearch dash-escape patch applied to BOTH `graphiti_core/driver/falkordb_driver.py:406-410` and `graphiti_core/driver/falkordb/operations/search_ops.py:105-107`. Diff committed on the fix branch with a commit message referencing study-tutor R-WAVE5-03 and this task.
- [ ] **AC-FORK-03** — `openai_generic` factory branch added to `mcp_server/src/services/factories.py` per guardkit TASK-INF-5054's spec (the patch shape is fully detailed in that task file). YAML schema entry for `providers.openai_generic` added to the config model.
- [ ] **AC-FORK-04** — Fix commit tagged (e.g. `v0.29.5-appmilla.1`). Tag pushed to the fork remote.
- [ ] **AC-FORK-05** — `FORK-NOTES.md` (or equivalent) at the fork repo root documents what's patched and why, with links back to study-tutor TASK-GR-SEED and guardkit TASK-INF-5054.
- [ ] **AC-FORK-06** — `study-tutor/pyproject.toml` updated to pin the fork tag. Venv refreshed. Test suite still passes (`695/696` baseline maintained — the one expected failure is the pre-existing mypy-on-system-Python issue).
- [ ] **AC-FORK-07** — `guardkit/scripts/graphiti-mcp-build.sh` updated to clone the fork at the tag. MCP image rebuilt on GB10 with `--no-cache`. Container restarted and reachable at `http://promaxgb10-41b1:8004/mcp`.
- [ ] **AC-FORK-08** — End-to-end verification (step 9 above): seed runs 25/25, verify_lilymay.py shows populated state, MCP write probe round-trips, MCP read probe with dashed group_id returns populated entity (NO syntax error), container logs show LLM calls hitting `localhost:9000`.
- [ ] **AC-FORK-09** — G2/G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` flipped from Falsified to Held with evidence per AC-SEED-05 format. TASK-GR-SEED moved to completed. TASK-INF-5054 moved to completed.

## Cross-references

- **study-tutor TASK-GR-SEED** (`study-tutor/tasks/blocked/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md`) — the seed task that surfaced the RediSearch dash bug. Currently blocked pending this fork.
- **guardkit TASK-INF-5054** (`guardkit/tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md`) — the MCP-server `openai_generic` task. Already specced in detail; the patch shape is in that task file, just needs to land in the fork instead of as a local-only patch.
- **guardkit TASK-INF-5053** (`guardkit/tasks/completed/2026-05/TASK-INF-5053-graphiti-mcp-http-server-group-id-fix.md`) — the parent investigation task that ruled out the alleged group_id coercion bug and surfaced the actual `responses.parse` / `base_url` ignore bugs.
- **guardkit TASK-REV-661E** (`guardkit/tasks/backlog/TASK-REV-661E-analyse-graphiti-seed-failures.md`) — root cause for character-sanitization gaps (backticks, slashes, pipes, backslashes) in upstream `sanitize()`. Patched in-tree at `falkordb_workaround.py:280-285`.
- **guardkit TASK-REV-84A7** (`guardkit/tasks/backlog/TASK-REV-84A7-analyse-failing-graphiti-add-context-commands.md`) — root cause for `llm_max_tokens: 4096` cap in `graphiti-mcp-config.yaml` (graphiti-core's 16384 default exceeds 32K context window of the GB10 vLLM deployment).
- **study-tutor phase-1-validation.md** (`study-tutor/docs/research/ideas/phase-1-validation.md`) §"Wave 4 retry — TASK-GR-SEED run 5 — 2026-05-03 (afternoon)" — full evidence + R-WAVE5-03 + R-WAVE5-04 risk register entries.

---

## Audit findings — comprehensive guardkit workaround inventory (2026-05-03)

This section was added after auditing the entire guardkit repo for graphiti-related workarounds. **Five additional graphiti-core defects (and one graphiti-mcp defect) currently live as runtime monkey-patches, defence-in-depth code, or operational scripts in guardkit but should be considered for upstream consolidation in this fork.** The two-row punchlist above covers only the most-recently-surfaced bugs (RediSearch dash-escape + `openai_generic` factory). The picture is wider than that.

### Extended punchlist — additional graphiti-core / graphiti-mcp defects discovered in-tree

| # | Bug | Symptom | Where the patch currently lives | Source task | Recommendation |
|---|-----|---------|---------------------------------|-------------|----------------|
| 8 | `handle_multiple_group_ids` decorator uses `len(group_ids) > 1` instead of `>= 1` | Single-group-id searches skip the FalkorDB driver-clone path, which selects the wrong named graph and returns empty/incorrect results | `guardkit/knowledge/falkordb_workaround.py:97-176` (runtime monkey-patch) — re-decorates `Graphiti.retrieve_episodes`, `build_communities`, `search`, `search_` | Upstream PR [#1170](https://github.com/getzep/graphiti/pull/1170), issue [#1161](https://github.com/getzep/graphiti/issues/1161) | **fork-candidate** — apply PR #1170 directly to `graphiti_core/decorators.py` |
| 9 | `edge_fulltext_search` and `edge_bfs_search` use `MATCH (n)-[e:RELATES_TO {uuid: rel.uuid}]->(m)` to re-find edge endpoints — O(n×m) full-edge scan per result | With 1500 fulltext results × 5000 edges = 7.5M comparisons → 26-118s per query | `guardkit/knowledge/falkordb_workaround.py:380-635` (runtime monkey-patch) — replaces re-MATCH with `startNode(e)/endNode(e)` for O(n) direct access | Upstream issue [#1272](https://github.com/getzep/graphiti/issues/1272) | **fork-candidate** — patch `graphiti_core/search/search_utils.py` directly |
| 10 | Upstream `sanitize()` in graphiti-core 0.26.3 omits backticks, forward slashes, pipes, and backslashes from its character-stripping list | Markdown documents with code references like `` `path/to/file.md` `` produce entity names containing these characters, which then break RediSearch syntax during `add_episode` → fulltext index writes | `guardkit/knowledge/falkordb_workaround.py:280-292` — pre-sanitises these chars before delegating to upstream `build_fulltext_query` | guardkit TASK-REV-661E | **fork-candidate** — extend `sanitize()` upstream to strip `` ` / \| \\ `` |
| 11 | `build_fulltext_query` `@group_id` filter is broken on FalkorDB — group_ids tokenised at index time (underscores split tokens), and group isolation is **already** handled by the multi-graph driver clone (workaround #8) plus the Cypher `WHERE` clause | Fulltext index lookups either return no results or raise RediSearch syntax errors when group_ids contain non-alphanumeric chars | `guardkit/knowledge/falkordb_workaround.py:287-309` — always passes `group_ids=None` to skip the filter entirely (a more aggressive fix than the dash-escape in the punchlist row #1 above) | Same root cause as punchlist #1 (R-WAVE5-03) | **fork-candidate, but pick one** — see "Discrepancy" note below |
| 12 | `build_fulltext_query` produces invalid `'()'` or `''` syntax when the input query is empty after stopword removal | RediSearch syntax error on every search whose query text is all stopwords | `guardkit/knowledge/falkordb_workaround.py:303-305` — replaces empty/`'()'` results with `'*'` (match-all) | Same root cause as punchlist #1 | **fork-candidate** — patch `build_fulltext_query` upstream |
| 13 | graphiti-mcp's `main()` mutates `mcp.settings.host = "0.0.0.0"` **after** FastMCP has frozen `transport_security` with localhost-only allow-list | All non-loopback clients (e.g. Tailscale hostnames like `promaxgb10-41b1:8004`) receive `421 Invalid Host header` | `guardkit/scripts/graphiti-mcp-bootstrap.py:38-39` — patches `TransportSecurityMiddleware._validate_host`/`_validate_origin` to no-op before importing graphiti-mcp's main | (none, surfaced during graphiti-mcp container deploy) | **fork-candidate** — graphiti-mcp should accept a `host` constructor arg or re-init `transport_security` after mutating `host`, so consumers don't need a bootstrap shim |

### Discrepancy: punchlist #1's "dash-escape" vs. in-tree "drop the filter entirely"

The existing punchlist row #1 proposes fixing the FalkorDB RediSearch escape bug at `falkordb_driver.py:406-410` by either brace-wrapping (`{group_id}`) or backslash-escaping (`group\-id`) the group_id token. The in-tree workaround at `guardkit/knowledge/falkordb_workaround.py:287-309` takes a different approach: it **always passes `group_ids=None` to the fulltext query**, bypassing the filter entirely on the basis that group isolation is already enforced by:

1. The multi-graph driver clone (per-group named graph in FalkorDB — see workaround #8 above)
2. The Cypher `WHERE e.group_id IN $group_ids` clause that runs after the fulltext lookup

**Which approach should land in the fork?** Both are valid. The "drop filter" approach is simpler and removes a class of bugs (#11 + #12 disappear together). The "fix escape" approach preserves the upstream design intent. Recommendation: **drop the filter** — that's what's been in production in guardkit for several months, and removing the filter eliminates two adjacent bugs in one commit. Capture this decision below before patching starts.

**Decision 5 (new): RediSearch fulltext fix shape — escape-and-keep, or drop-the-filter?**
- Recommended: **drop the filter** (matches in-tree workaround, fixes bugs #1 + #11 + #12 simultaneously)
- Alternative: escape and keep (smaller diff, closer to upstream intent, but leaves bugs #11 + #12 unaddressed)
- **DECISION (LOCKED 2026-05-04)**: **drop the filter**. Implemented in [`patches/001-drop-fulltext-group-filter.patch`](../../patches/001-drop-fulltext-group-filter.patch) (verified clean apply against `d0913fe`). Rationale: (a) already production-tested for months in `guardkit/knowledge/falkordb_workaround.py:287-309`, (b) fixes bugs #5 + #11 + #12 in one diff, (c) Cypher `WHERE n.group_id IN $group_ids` backstop verified at `search_ops.py:142-144, 187-189, 240-243, 292-294`, (d) per the addendum execution-flow trace, no execution path produces *worse* output than upstream regardless of bug #8 fix presence.

### Defence-in-depth code (stays put — do NOT push upstream)

These are consumer-side guards layered on top of the MCP API surface. They compensate for the absence of strong correctness guarantees from graphiti-mcp's response messages, not for graphiti-core defects per se. They should remain in guardkit even after the fork lands.

| File | Purpose | Status after fork lands |
|------|---------|-------------------------|
| `installer/core/commands/lib/graphiti_response_parser.py` | Parses MCP `add_memory` response message and detects whether the server's reported `group_id` matches the requested one (originally a B1F7 mitigation; subsequently invalidated by TASK-INF-5053 audit but retained as cheap regression guard) | Keep as defence-in-depth. Reason: zero-cost at runtime, gives a hard error if any future graphiti-mcp regression silently misroutes episodes. |
| `installer/core/commands/lib/graphiti_check.py` and `~/.agentecflow/bin/graphiti-check` | Tiered availability check (Tier 0 MCP → Tier 1 CLI → Tier 2 skip) for graphiti integration in slash commands | Keep — orthogonal to graphiti-core/mcp bugs |
| `task-complete.md` MCP→CLI fallback logic | Falls back to `guardkit graphiti capture-outcome` (Python client) if `mcp__graphiti__add_memory` is unavailable or returns a divergent group_id | Keep — orthogonal |

### Operational migration scripts (one-shot remediation, do NOT push upstream)

| File | Purpose |
|------|---------|
| `guardkit/docs/fixes/migrate-hyphens.py` | Idempotent migration to convert FalkorDB graph names and `group_id` properties from hyphens to underscores. Surfaced because RediSearch tokenises hyphens. The real fix is the naming convention enforced at write time (documented in `.claude/rules/graphiti-knowledge-graph.md`); the script is the catch-up migration for already-written episodes. |
| `guardkit/scripts/graphiti-mcp-config.yaml` `llm_max_tokens: 4096` cap | Caps LLM extraction to 4096 tokens because graphiti-core's default 16384 exceeds the 32K context window of the GB10 vLLM deployment (TASK-REV-84A7). Could be pushed upstream as "respect a configurable cap" but lower priority than the bugs above. |

### Production wiring of the workaround module

`apply_falkordb_workaround()` is invoked from `guardkit/knowledge/graphiti_client.py:62-63` at client construction time. It is therefore active for **every CLI write path** through `guardkit graphiti add-context`, `capture-outcome`, `seed`, and `seed-system`. It is **NOT active** for the MCP write path (the graphiti-mcp container runs unpatched graphiti-core). This is one more reason to land the fixes in the fork: the MCP container is currently running unpatched code for bugs #8-#12, and the consumer-side monkey-patch can't reach into the container.

### Recommended additions to Acceptance Criteria

- [ ] **AC-FORK-10** — `handle_multiple_group_ids` decorator fix (PR #1170 equivalent) applied in fork at `graphiti_core/decorators.py`. Verify by removing `apply_falkordb_workaround()` from `guardkit/knowledge/graphiti_client.py` (locally, not committed) and confirming the existing falkordb_workaround test suite (`tests/knowledge/test_falkordb_workaround.py`) still passes against the forked graphiti-core. **Then re-add `apply_falkordb_workaround()` for now** — it can be removed in a follow-up task once all consumers are on the fork tag.
- [ ] **AC-FORK-11** — Edge-search O(n×m) fix (issue #1272) applied in fork at `graphiti_core/search/search_utils.py`. Verify with the same falkordb_workaround test suite (it has separate tests for `edge_fulltext_search` and `edge_bfs_search`).
- [ ] **AC-FORK-12** — `sanitize()` extended in fork to strip backticks, forward slashes, pipes, and backslashes (TASK-REV-661E gap). Verify by running guardkit's seed pipeline against a markdown corpus containing `` `path/to/file.md` `` references (the original repro case).
- [ ] **AC-FORK-13** — Decision 5 (drop-filter vs. escape-and-keep) captured. If "drop filter": apply that in fork at both call sites and verify guardkit's in-tree `apply_fulltext_query_workaround()` still no-ops cleanly (it has a "already fixed upstream, skipping" branch at line 84-86 that should activate). If "escape-and-keep": apply that and additionally fix bugs #11 + #12 in separate commits.
- [ ] **AC-FORK-14** *(stretch)* — graphiti-mcp `transport_security` re-init after host mutation (bug #13). If shipped: verify by removing `scripts/graphiti-mcp-bootstrap.py` from the build pipeline and confirming the rebuilt MCP image accepts `Host: promaxgb10-41b1:8004` from a Tailscale client.

## In-flight patch already drafted in `~/Projects/appmilla_github/graphiti-official/` (2026-05-03)

A working draft of the punchlist #2 fix is **already sitting as staged-but-unpushed changes** in the upstream-tracking clone at `~/Projects/appmilla_github/graphiti-official/`. Reviewed 2026-05-03. The fix targets bug #2 (`openai_generic` factory) and was authored against upstream commit `9cdcc93` (i.e. *before* the two appmilla-fork commits `164030f` "custom edge type support" and `56cf7b3` "Bump graphiti-core to 0.29.0"; nothing in the patch conflicts with either).

### What's staged

```
mcp_server/config/config-guardkit.yaml      | new file  (78 lines)
mcp_server/config/config-local-neo4j.yaml   | new file  (103 lines)
mcp_server/src/services/factories.py        | modified  (+14 / -0)
```

### Diff: `mcp_server/src/services/factories.py`

Apply verbatim to the same file in this fork (currently at [mcp_server/src/services/factories.py:117-128](mcp_server/src/services/factories.py#L117-L128) in the `case 'openai':` arm — bug confirmed still present):

```diff
@@ -17,6 +17,7 @@
 from graphiti_core.embedder import EmbedderClient, OpenAIEmbedder
 from graphiti_core.llm_client import LLMClient, OpenAIClient
+from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
 from graphiti_core.llm_client.config import LLMConfig as GraphitiLLMConfig

@@ -118,15 +119,28 @@
                 # Use the same model for both main and small model slots
                 small_model = config.model
+                base_url = config.providers.openai.api_url

                 llm_config = CoreLLMConfig(
                     api_key=api_key,
                     model=config.model,
                     small_model=small_model,
+                    base_url=base_url,
                     temperature=config.temperature,
                     max_tokens=config.max_tokens,
                 )

+                # Use OpenAIGenericClient for non-OpenAI endpoints (Ollama, vLLM, etc.)
+                # OpenAIClient uses the Responses API which local servers don't support
+                is_openai_endpoint = base_url is None or 'api.openai.com' in base_url
+                if not is_openai_endpoint:
+                    logger.info(
+                        f'Using OpenAIGenericClient for non-OpenAI endpoint: {base_url}'
+                    )
+                    return OpenAIGenericClient(
+                        config=llm_config, max_tokens=config.max_tokens
+                    )
+
                 # Check if this is a reasoning model (o1, o3, gpt-5 family)
                 reasoning_prefixes = ('o1', 'o3', 'gpt-5')
                 is_reasoning_model = config.model.startswith(reasoning_prefixes)
```

`OpenAIGenericClient` already exists in this fork at [graphiti_core/llm_client/openai_generic_client.py:37](graphiti_core/llm_client/openai_generic_client.py#L37) — no graphiti-core changes needed for this part.

### Patch shape diverges from punchlist #2 — pick one

The punchlist row #2 specifies a **new `case 'openai_generic':` arm** alongside the existing `openai`/`groq` cases, plus a YAML schema entry under `providers.openai_generic`. The staged in-flight patch takes a **different approach**: it keeps a single `case 'openai':` arm and **auto-detects** non-OpenAI endpoints from `base_url`, routing to `OpenAIGenericClient` when the host is not `api.openai.com`. Both approaches are valid; they differ in user-facing config shape:

| Approach | Config users write | Pros | Cons |
|----------|--------------------|------|------|
| **A. Auto-detect (staged in-flight)** | `provider: "openai"` with non-openai `api_url` | Zero config-schema churn; existing configs Just Work; reuses `providers.openai` block. Minimal diff (+14 lines, no schema edits). | Implicit behaviour. Operator who reads `provider: "openai"` may not realise the runtime swaps to a different client. |
| **B. New `openai_generic` case (punchlist #2 plan)** | `provider: "openai_generic"` with explicit `providers.openai_generic` block | Explicit. Easy to grep for. Self-documenting in YAML. | Requires touching the config Pydantic model **and** every existing local-LLM YAML in the wild. Larger blast radius across consumer repos (study-tutor, guardkit, jarvis configs all need updates). |

**Decision 6 (new): factory routing shape — auto-detect on `api_url`, or explicit `openai_generic` provider?**
- Recommended: **auto-detect (Approach A)** — matches the already-drafted in-flight patch, zero config migration burden on consumers, reversible with one commit if we change our minds.
- Alternative: explicit `openai_generic` (Approach B) — better long-term ergonomics, but blocks the DDD demo while we update three consumer pyprojects' configs.
- **DECISION (LOCKED 2026-05-04)**: **auto-detect (Approach A)**. Implemented as the in-flight diff at `~/Projects/appmilla_github/graphiti-official/mcp_server/src/services/factories.py` (rebase + apply during GB10 session step 3). Rationale: (a) Graphiti knowledge graph confirms this was the established pattern from 2026-04-03 ("graphiti MCP server factory uses OpenAIGenericClient for non-OpenAI endpoints"), (b) `vLLM does not support the OpenAI Responses API` (knowledge graph), so routing on `base_url` is the correct discrimination axis, (c) zero consumer-config-schema churn, (d) per addendum execution-flow trace Diagram 13, the only theoretical regression (Azure-fronted proxy expecting Responses API) is benign for graphiti-core's structured-output use case which doesn't use Responses-only features.

### `mcp_server/config/config-guardkit.yaml` — staged file is **stale**, do NOT use

Re-reviewed 2026-05-03 against the actual live GB10 setup
([guardkit/scripts/graphiti-mcp-config.yaml](../../guardkit/scripts/graphiti-mcp-config.yaml),
[guardkit/scripts/graphiti-stack-up.sh](../../guardkit/scripts/graphiti-stack-up.sh),
[guardkit/scripts/infra-up.sh](../../guardkit/scripts/infra-up.sh),
[guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md](../../guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md)).
Conclusion: the staged YAML is a snapshot of an earlier Gemini-era config (~2026-04-20)
that was **never refreshed after the 2026-04-29 vLLM → llama-swap migration**. It
diverges from the live deployment on four points, the third of which is a silent
foot-gun:

| Field | Staged file | Live config (mounted into the running container) | Risk if used as-is |
|-------|-------------|--------------------------------------------------|---------------------|
| LLM provider | `gemini` (paid Gemini 2.5 Pro) | `openai` shaped, pointed at llama-swap | Bypasses the local LLM that `llama-swap-keepalive.timer` is actively keeping warm; consumes paid Gemini quota unnecessarily |
| LLM model | `${LLM_MODEL:gemini-2.5-pro}` | `${LLM_MODEL:qwen-graphiti}` (llama-swap alias for `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic`) | Alias `qwen-graphiti` won't resolve under `provider: gemini` |
| Embedder URL | `${EMBEDDING_API_URL:http://promaxgb10-41b1:8001/v1}` (**dead** vLLM-embed endpoint, retired 2026-04-29; scripts archived under `guardkit/scripts/archive-vllm/`) | `${EMBEDDING_API_URL:http://localhost:9000/v1}` (llama-swap on :9000) | Embedding calls hit a closed port; ingestion + search both fail |
| Embedder model + dimensions | `nomic-embed-text-v1.5`, **`dimensions: 1024`** (Matryoshka) | `nomic-embed`, **`dimensions: 768`** (verified 2026-05-01 by curling `:9000/v1/embeddings`) | **Silent foot-gun**: if FalkorDB's vector index was rebuilt against the staged file's 1024-dim and the actual model returns 768-dim, queries silently return zero hits — the exact "Embedder dimension mismatch" symptom documented at [graphiti-gb10-deployment.md §Embedder dimension mismatch](../../guardkit/docs/guides/graphiti-gb10-deployment.md#L478) |

**Single source of truth.** The actually-running config is
[guardkit/scripts/graphiti-mcp-config.yaml](../../guardkit/scripts/graphiti-mcp-config.yaml),
mounted read-only into the container at `/app/mcp/config/config.yaml` by
`graphiti-mcp.sh`. Its history comment block records all three eras (vLLM → Gemini
profiling → llama-swap) and its endpoint defaults all read `:9000`. There is also a
backup `graphiti-mcp-config.yaml.pre-llamacpp.bak` next to it confirming the
post-migration cutover.

**Tightly coupled to the factories.py fix (punchlist #2).** The live config sets
`provider: openai` with `api_url: http://localhost:9000/v1` — i.e. an OpenAI-shaped
client pointed at a non-OpenAI endpoint. That is **exactly** the case the staged
`factories.py` patch detects (`'api.openai.com' not in base_url`) and reroutes to
`OpenAIGenericClient`. Without the factory fix landing in the fork, the live config
would hit `api.openai.com/v1/responses` instead of llama-swap. So the factory fix
is the **enabler** for the live config; the live config is the **target**
deployment shape that exercises the fix on the GB10. Today this works only because
the running container builds against an unforked graphiti-core where the
`OpenAIGenericClient` routing was patched in-tree (or because `LLM_API_URL` env
override is set explicitly, depending on whether `graphiti-stack-up.sh` exports it
in `gb10` mode — which it currently does NOT for `gb10`, only for `mac`/`custom`,
so the YAML default reads-through and the bug-fix path is the one that runs).

**Action.** Do NOT commit the staged `mcp_server/config/config-guardkit.yaml` to
the public fork. Discard the staged file. The real GuardKit-deployment config
already lives in [guardkit/scripts/graphiti-mcp-config.yaml](../../guardkit/scripts/graphiti-mcp-config.yaml)
and is correct. If the desire is to ship a "GuardKit-style" example template inside
the fork for documentation purposes, derive it from the live config (provider
openai, llama-swap defaults, 768-dim) with all GB10-specific values stripped to
`${...}` env placeholders — and name it explicitly an example (e.g.
`config-llama-swap-example.yaml`), not `config-guardkit.yaml`, to avoid future
drift between the in-fork example and the live config it was once a snapshot of.

**Stale runbook follow-up.** [guardkit/docs/guides/graphiti-gb10-deployment.md](../../guardkit/docs/guides/graphiti-gb10-deployment.md)
is itself stale relative to the post-2026-04-29 reality — its topology diagram
(lines 26-50) still depicts `vllm-graphiti :8000` and `vllm-embedding :8001` as
separate containers, the "supersedes Gemini" note no longer matches the actual
provider history, and the supersedes-link at line 10 points back to the
already-superseded Gemini setup doc. File a separate doc-update task to refresh
the runbook to the llama-swap topology; do not roll that into this fork-patch
task. Recorded here so it isn't forgotten.

### `mcp_server/config/config-local-neo4j.yaml` — generic, ship with the fork

The staged file is a **clean generic Docker-compose-with-Neo4j config template** — no Tailscale-specific values, environment variables for everything, all five LLM providers (openai/azure_openai/anthropic/gemini/groq) and four embedder providers (openai/azure_openai/gemini/voyage). Useful as an upstream addition. Recommend: **commit this one to the fork** as `mcp_server/config/config-local-neo4j.yaml` (it's a clean documentation/example artefact and slots alongside the existing `config-docker-neo4j.yaml`).

### Stale upstream-tracker note

`~/Projects/appmilla_github/graphiti-official/` was 2 commits behind its own `origin/main` at review time (missing `164030f` + `56cf7b3` — the two appmilla-fork commits already in this fork). The patch was written against `9cdcc93` (upstream's tip pre-fork-divergence), so applying it on top of this fork's current `main` (`56cf7b3`) is a clean fast-forward apply with no rebase needed — verified by manual three-way comparison of the `case 'openai':` block, which is unchanged across the two appmilla-fork commits.

### Recommended additions to Acceptance Criteria

- [ ] **AC-FORK-15** — Decision 6 (auto-detect vs explicit `openai_generic` case) captured in this task file before patching starts. If Approach A: apply the in-flight diff above verbatim and skip the config-schema edits. If Approach B: apply the punchlist #2 spec and update study-tutor/guardkit/jarvis configs in the same PR sweep.
- [ ] **AC-FORK-16** — `mcp_server/config/config-local-neo4j.yaml` from the in-flight staged set committed to the fork (generic template, no secrets). The staged `config-guardkit.yaml` is **discarded entirely** — it is stale (Gemini era, dead `:8001` embedder, wrong 1024-dim) and the actual live config already lives at [guardkit/scripts/graphiti-mcp-config.yaml](../../guardkit/scripts/graphiti-mcp-config.yaml). If a GuardKit-style example is desired in the fork for documentation, derive it fresh from the live config (provider openai → llama-swap, 768-dim, GB10-specific values blanked to `${...}` env placeholders) and name it `config-llama-swap-example.yaml`.
- [ ] **AC-FORK-17** — After applying the factory fix, smoke-test on the GB10 with the staged guardkit config: `docker logs graphiti-mcp` should show `INFO Using OpenAIGenericClient for non-OpenAI endpoint: http://...` on first LLM call, confirming the auto-detect branch executed.
- [ ] **AC-FORK-18** — Separate doc-update task filed (NOT part of this fork-patch task) to refresh [guardkit/docs/guides/graphiti-gb10-deployment.md](../../guardkit/docs/guides/graphiti-gb10-deployment.md) for the post-2026-04-29 llama-swap topology: replace the dual-vLLM box diagram, remove the "supersedes Gemini" note, fix the broken supersedes-link at line 10, and update the file map / config-relationships / troubleshooting sections to reflect the single-port `:9000` reality.

- [ ] **AC-FORK-19** *(new 2026-05-04, per task-review addendum)* — Pre-application baseline captured (mechanical-plan step 0). Post-each-commit diff via `diff /tmp/baseline-falkordb.txt /tmp/post-${SHA:0:7}-falkordb.txt` (and the equivalent for `mcp` and `workaround`) shows **no new test failures** for any commit landing patches 001-005 + factories.py. If any new failure appears, the GB10 session pauses, the offending commit is reverted, the cause is investigated against the addendum's regression matrix (`.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md` §"Regression Matrix"), and the task moves to BLOCKED. New passes (e.g. previously-failing tests in guardkit's `test_falkordb_workaround.py` that now pass against the un-monkeypatched fork) are expected and acceptable.

## Notes

- **Why now (May 2026)**: DDD South West talk mid-May + Kaggle hackathon submission for study-tutor. Forking is the lowest-risk way to ship demonstrable working state without de-railing either deadline. The larger "shrink graphiti's role or replace entirely" research is deferred until after mid-May (separate research task to be filed later).
- **Why not push fixes upstream right now**: getzep responsiveness unknown; the dash-escape upstream "fix" was attempted and shipped broken, suggesting their test surface for FalkorDB-side fulltext queries is thin. Once the fork is stable and verified end-to-end, consider opening upstream PRs at that point with the appmilla fix as a reference implementation. Don't block consumer migration on upstream merge.
- **Consumer migration order**: study-tutor first (it has the active blocker), then guardkit (medium use), then jarvis (lower-pri, can wait). Don't try to migrate all three in one sitting.
- **Maintenance discipline**: Whoever owns this fork needs a plan for pulling upstream changes periodically (probably quarterly during the fork's expected lifetime). Document the merge process in FORK-NOTES.md.
