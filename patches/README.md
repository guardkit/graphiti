# guardkit fork — pre-built patches

This directory holds ready-to-apply patches drafted ahead of the GB10 fork-application session for [TASK-FORK-PATCH](../tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md). Each patch is a unified diff (`diff -u`) that applies cleanly via `git apply -p1` (or `patch -p1`) against this fork at version 0.29.0 (verified 2026-05-04 — all five pass `git apply --check` individually and together against `d0913fe`).

## What's here, in suggested apply order

| # | File | Bugs fixed (audit IDs) | Files touched |
|---|------|------------------------|---------------|
| 1 | `001-drop-fulltext-group-filter.patch` | #5 (RediSearch dash-as-NOT) + #11 (`@group_id` filter broken on FalkorDB) + #12 (empty post-stopword query produces invalid `()` syntax) | `graphiti_core/driver/falkordb_driver.py` (`build_fulltext_query`), `graphiti_core/driver/falkordb/operations/search_ops.py` (`_build_falkor_fulltext_query`) |
| 2 | `002-extend-sanitize-strip-backtick.patch` | #10 (partial — only backtick remains missing in 0.29.0; slashes/pipes/backslashes already in 0.29's strip list) | `graphiti_core/driver/falkordb_driver.py` (`sanitize` method), `graphiti_core/driver/falkordb/operations/search_ops.py` (`_SEPARATOR_MAP` constant) |
| 3 | `003-mcp-early-host-binding.patch` | #13 (graphiti-mcp's `transport_security` frozen with localhost-only allow-list because host is mutated AFTER FastMCP construction) | `mcp_server/src/graphiti_mcp_server.py` |
| 4 | `004-handle-multiple-group-ids-decorator.patch` *(new 2026-05-04)* | #8 (`handle_multiple_group_ids` decorator skips driver-clone for single-group calls because of `len > 1` check) — derived from upstream PR [#1170](https://github.com/getzep/graphiti/pull/1170) / issue [#1161](https://github.com/getzep/graphiti/issues/1161) | `graphiti_core/decorators.py` (`handle_multiple_group_ids` wrapper) |
| 5 | `005-edge-search-direct-endpoints.patch` *(new 2026-05-04)* | #9 (`edge_fulltext_search` and `edge_bfs_search` use O(n×m) re-MATCH on `rel.uuid` to re-find endpoints) — derived from upstream issue [#1272](https://github.com/getzep/graphiti/issues/1272) and `guardkit/knowledge/falkordb_workaround.py:380-635` | `graphiti_core/search/search_utils.py` (default `match_query` for `edge_fulltext_search`; default-else branch for `edge_bfs_search`) |

These five patches still do **not** cover the `openai_generic` / `responses.parse` factory routing (bugs #6/#7) — that's the in-flight diff already drafted at `~/Projects/appmilla_github/graphiti-original/mcp_server/src/services/factories.py` per the task's "In-flight patch already drafted" section. Apply that as a separate sixth commit during the GB10 session (rebase onto current `d0913fe` first).

Decision 5 in the task file (drop-filter vs escape-and-keep) is **locked to drop-filter** as of 2026-05-04 — patch 1 implements it. Decision 6 (auto-detect vs explicit `openai_generic`) is **locked to auto-detect**; the in-flight diff matches that shape.

## Patch interaction notes (added 2026-05-04 per task-review addendum)

Per the execution-flow trace in `.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md`:

- **Patches 001 + 004 are commutatively safe.** No application order produces *worse* output than upstream. Worst case for any partial state is `[]` (same shape as the existing upstream bugs). Both patches together restore correctness for single-group searches against FalkorDB.
- **Patch 005 changes `edge_bfs_search` semantics**: the original undirected `MATCH (n)-[e]-(m)` returned each edge twice with swapped endpoints. The patch returns each edge once in directed (source → target) form. Result-count drops by ~2× for that specific call; that is a latent-bug fix, not a regression.
- **Each patch is independently revertable.** Land them as separate commits. After each commit, re-run AC-FORK-19's baseline-diff (`diff /tmp/baseline-falkordb.txt /tmp/post-${SHA:0:7}-falkordb.txt`) so any new failure bisects to a single commit.

## Applying the patches

From the fork repo root (e.g. `~/Projects/appmilla_github/graphiti/` on the GB10):

```bash
# Option A — git apply (recommended; respects whitespace, integrates with index)
git apply --check patches/001-drop-fulltext-group-filter.patch
git apply patches/001-drop-fulltext-group-filter.patch

git apply --check patches/002-extend-sanitize-strip-backtick.patch
git apply patches/002-extend-sanitize-strip-backtick.patch

git apply --check patches/003-mcp-early-host-binding.patch
git apply patches/003-mcp-early-host-binding.patch

git apply --check patches/004-handle-multiple-group-ids-decorator.patch
git apply patches/004-handle-multiple-group-ids-decorator.patch

git apply --check patches/005-edge-search-direct-endpoints.patch
git apply patches/005-edge-search-direct-endpoints.patch

# Option B — patch -p1 (works even outside a git checkout)
patch -p1 < patches/001-drop-fulltext-group-filter.patch
patch -p1 < patches/002-extend-sanitize-strip-backtick.patch
patch -p1 < patches/003-mcp-early-host-binding.patch
patch -p1 < patches/004-handle-multiple-group-ids-decorator.patch
patch -p1 < patches/005-edge-search-direct-endpoints.patch
```

After all are applied, commit each as a separate commit so each fix is independently revertable. Suggested commit messages:

```
fix(falkordb): drop @group_id fulltext filter (TASK-FORK-PATCH bugs #5/#11/#12)

The upstream `(@group_id:"...")` prefix is unreliable on FalkorDB — RediSearch
tokenises group_ids at index time and parses dashes as NOT operators inside
the double-quote wrap. Group isolation already comes from the multi-graph
driver clone plus the Cypher WHERE clause, so we drop the prefix entirely
and return RediSearch's match-all wildcard for empty post-stopword queries.

Refs: study-tutor R-WAVE5-03; guardkit/knowledge/falkordb_workaround.py
```

```
fix(falkordb): strip backtick in sanitize() (TASK-FORK-PATCH bug #10)

Backticks survive upstream's strip list, so markdown-style `path/to/file.md`
references in episode bodies leak into entity names and break RediSearch
syntax at index time.

Refs: guardkit TASK-REV-661E
```

```
fix(mcp): bind FastMCP host at construction time (TASK-FORK-PATCH bug #13)

graphiti-mcp's initialize_server() mutates `mcp.settings.host` AFTER FastMCP
has frozen transport_security with a localhost-only allow-list. Read
MCP_SERVER_HOST from the environment at module load and pass it to FastMCP
so the allow-list freezes against the right host. Default preserves
upstream behaviour.

Refs: guardkit/scripts/graphiti-mcp-bootstrap.py — once this lands and
graphiti-mcp.sh exports MCP_SERVER_HOST=0.0.0.0, the bootstrap shim can be
removed in a follow-up.
```

```
fix(decorator): handle single-group FalkorDB calls (TASK-FORK-PATCH bug #8)

handle_multiple_group_ids previously skipped its driver-clone path when
group_ids has exactly one element (`len > 1` check). Single-group searches
ran on whatever named graph the shared driver was last on — wrong graph,
empty results.  Drop the `len > 1` check so single-group calls also fan
out via `driver.clone(database=gid)`.

Refs: upstream PR #1170 / issue #1161;
guardkit/knowledge/falkordb_workaround.py:97-176 (consumer-side patch).
```

```
fix(search): direct endpoint access via startNode/endNode (TASK-FORK-PATCH bug #9)

edge_fulltext_search and edge_bfs_search re-MATCH every yielded
relationship by uuid to re-find its endpoints. With ~1500 fulltext yields
× ~5000 edges that's 7.5M comparisons per query (26-118s observed). Use
startNode(rel)/endNode(rel) for O(n) direct access. The Neptune branch
already does this; the default branch now matches. Also fixes a latent
double-count in edge_bfs_search where an undirected MATCH was emitting
each edge twice with swapped source/target.

Refs: upstream issue #1272;
guardkit/knowledge/falkordb_workaround.py:380-635 (consumer-side patch).
```

## What's NOT in this directory (and why)

- **Bug #6/#7 — `openai_generic` factory routing**: addressed by the in-flight diff at `~/Projects/appmilla_github/graphiti-original/mcp_server/src/services/factories.py` (Approach A — auto-detect on `base_url`). Apply that diff verbatim per the task's "In-flight patch already drafted" section.
- **Patches for the verification ACs themselves** (smoke tests, container rebuild, doc updates) — those live in the task file's mechanical plan, not as code diffs.

## Verifying after apply

After the patches land + the openai_generic + #8/#9 fixes are also in:

```bash
# In the fork
.venv/bin/python -c "from graphiti_core.driver.falkordb_driver import FalkorDriver; print('OK')"

# In a study-tutor venv pinned to the forked tag
.venv/bin/python scripts/seed_student_model.py    # expect 25/25 succeeded_writes
.venv/bin/python .guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py    # expect populated state
```

See AC-FORK-08 in the task file for the full end-to-end verification checklist.
