# appmilla fork — pre-built patches

This directory holds ready-to-apply patches drafted ahead of the GB10 fork-application session for [TASK-FORK-PATCH](../tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md). Each patch is a unified diff (`diff -u`) that applies cleanly via `git apply -p1` (or `patch -p1`) against this fork at version 0.29.0 (verified 2026-05-03 — all three pass `git apply --check` individually and together).

## What's here, in suggested apply order

| # | File | Bugs fixed (audit IDs) | Files touched |
|---|------|------------------------|---------------|
| 1 | `001-drop-fulltext-group-filter.patch` | #5 (RediSearch dash-as-NOT) + #11 (`@group_id` filter broken on FalkorDB) + #12 (empty post-stopword query produces invalid `()` syntax) | `graphiti_core/driver/falkordb_driver.py` (`build_fulltext_query`), `graphiti_core/driver/falkordb/operations/search_ops.py` (`_build_falkor_fulltext_query`) |
| 2 | `002-extend-sanitize-strip-backtick.patch` | #10 (partial — only backtick remains missing in 0.29.0; slashes/pipes/backslashes already in 0.29's strip list) | `graphiti_core/driver/falkordb_driver.py` (`sanitize` method), `graphiti_core/driver/falkordb/operations/search_ops.py` (`_SEPARATOR_MAP` constant) |
| 3 | `003-mcp-early-host-binding.patch` | #13 (graphiti-mcp's `transport_security` frozen with localhost-only allow-list because host is mutated AFTER FastMCP construction) | `mcp_server/src/graphiti_mcp_server.py` |

These three patches do **not** cover every entry in the audit punchlist. Bugs #1-#4 are already fixed in 0.29.0 (or live in consumer-side wiring per the audit's "stays in consumer code" note). Bugs #6/#7 — the `openai_generic` / `responses.parse` factory routing — are addressed by the in-flight diff already drafted at `~/Projects/appmilla_github/graphiti-official/mcp_server/src/services/factories.py` per the task's "In-flight patch already drafted" section. Bugs #8 (PR #1170) and #9 (issue #1272) have explicit upstream PR/issue references; cherry-pick or re-derive those during the GB10 session.

Decision 5 in the task file (drop-filter vs escape-and-keep) is implicitly answered by patch 1 — it implements **drop-the-filter**, the recommended approach. Apply patch 1 only after locking that decision.

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

# Option B — patch -p1 (works even outside a git checkout)
patch -p1 < patches/001-drop-fulltext-group-filter.patch
patch -p1 < patches/002-extend-sanitize-strip-backtick.patch
patch -p1 < patches/003-mcp-early-host-binding.patch
```

After all three are applied, commit each as a separate commit so each fix is independently revertable. Suggested commit messages:

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

## What's NOT in this directory (and why)

- **Bug #6/#7 — `openai_generic` factory routing**: addressed by the in-flight diff at `~/Projects/appmilla_github/graphiti-official/mcp_server/src/services/factories.py` (Approach A — auto-detect on `base_url`). Apply that diff verbatim per the task's "In-flight patch already drafted" section.
- **Bug #8 — `handle_multiple_group_ids` `>1` vs `>=1`**: cherry-pick from upstream PR #1170 (already authored, not yet merged).
- **Bug #9 — `edge_fulltext_search` / `edge_bfs_search` O(n×m) scan**: cherry-pick from the patch in `guardkit/knowledge/falkordb_workaround.py:380-635`, or re-derive against upstream issue #1272.
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
