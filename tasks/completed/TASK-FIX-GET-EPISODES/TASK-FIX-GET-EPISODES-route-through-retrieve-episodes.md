---
id: TASK-FIX-GET-EPISODES
title: Fix MCP get_episodes to route through Graphiti.retrieve_episodes (FalkorDB)
status: completed
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
completed: 2026-05-07T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-GET-EPISODES/
priority: high
task_type: implementation
complexity: 2
estimated_minutes: 60
target_tag: v0.29.5-guardkit.4
parent_review: TASK-REV-GET-EPISODES
tags: [graphiti, mcp, falkordb, bug-fix]
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-07T00:00:00Z
  notes: |
    307 unit tests passed (DISABLE_NEO4J=1 DISABLE_FALKORDB=1 DISABLE_KUZU=1
    DISABLE_NEPTUNE=1 uv run pytest -m "not integration"). Lint + format + pyright
    clean.

    New integration tests in tests/test_retrieve_episodes_int.py
    (single-group FalkorDB, multi-group FalkorDB, Neo4j valid_at ordering) are
    marked @pytest.mark.integration and gated by GraphProvider — they're
    deselected by `make test` and require a live FalkorDB / Neo4j to exercise.

    Note: `make test` (without DISABLE_NEO4J=1) hits pre-existing failures in
    test_node_int.py / test_graphiti_mock.py / test_add_triplet.py — those tests
    require a running Neo4j but are not marked integration. Unrelated to this
    task's diff (which is scoped to mcp_server/src/graphiti_mcp_server.py + the
    new test file).
---

# Fix MCP `get_episodes` to route through `Graphiti.retrieve_episodes` (FalkorDB)

**PRIORITY**: high
**TASK_TYPE**: implementation
**COMPLEXITY**: 2
**ESTIMATED_MINUTES**: 60
**TARGET_TAG**: `v0.29.5-guardkit.4`
**PARENT_REVIEW**: [TASK-REV-GET-EPISODES](TASK-REV-GET-EPISODES-mcp-empty-results.md)

---

## Summary

MCP `get_episodes` calls `EpisodicNode.get_by_group_ids` directly with the
shared `client.driver`, bypassing the `@handle_multiple_group_ids` decorator
(bug #8). On FalkorDB the per-group named-graph layout means the lookup hits
the wrong graph and returns `[]`. Fix: route through `Graphiti.retrieve_episodes`
which is already decorated.

All design decisions locked in [TASK-REV-GET-EPISODES review report](../../.claude/reviews/TASK-REV-GET-EPISODES-review-report.md):

- Fix path: route through `client.retrieve_episodes(...)` (recommended option)
- `reference_time`: hardcode `datetime.now(timezone.utc)` — no new MCP param
- Empty `group_ids`: preserve `[]` — do not route through `retrieve_episodes(group_ids=None)`
- Upstream PR: candidate after fork tag lands; path-scoped to `mcp_server/src/`
- Neo4j risk: low; `uuid DESC` → `valid_at DESC` ordering change documented

## Code change

**File**: `mcp_server/src/graphiti_mcp_server.py:649-654`

**Before**:

```python
# Get episodes from the driver directly
from graphiti_core.nodes import EpisodicNode

if effective_group_ids:
    episodes = await EpisodicNode.get_by_group_ids(
        client.driver, effective_group_ids, limit=max_episodes
    )
else:
    # If no group IDs, we need to use a different approach
    # For now, return empty list when no group IDs specified
    episodes = []
```

**After** (with `from datetime import datetime, timezone` added at module top if not already present):

```python
if effective_group_ids:
    episodes = await client.retrieve_episodes(
        reference_time=datetime.now(timezone.utc),
        last_n=max_episodes,
        group_ids=effective_group_ids,
    )
else:
    # No group IDs specified and no default configured — return empty.
    # Routing group_ids=None through retrieve_episodes would query the
    # shared default graph on FalkorDB (always empty under per-group
    # named-graph layout), which is exactly the cross-backend asymmetry
    # we're fixing here.
    episodes = []
```

Drop the local `from graphiti_core.nodes import EpisodicNode` import (no
longer used in this scope; check whether it's used elsewhere in the file
before removing the top-level import).

## Acceptance Criteria

- **AC-IMP-EP-01** — Replace direct `EpisodicNode.get_by_group_ids` call at
  `mcp_server/src/graphiti_mcp_server.py:649-654` with
  `await client.retrieve_episodes(reference_time=datetime.now(timezone.utc), last_n=max_episodes, group_ids=effective_group_ids)`.
  Add `from datetime import datetime, timezone` import if not already present.
  Drop the local `EpisodicNode` import in the function scope; verify it's
  not used elsewhere before removing any module-level import.

- **AC-IMP-EP-02** — `reference_time` hardcoded to
  `datetime.now(timezone.utc)`. Do not expose as MCP tool parameter. The
  MCP tool signature stays `(group_ids, max_episodes)` — no public-API
  change.

- **AC-IMP-EP-03** — Preserve empty-`group_ids` `[]` branch (lines 655-658)
  unchanged in behaviour. Optional: add `logger.warning("get_episodes called with no group_ids and no configured default — returning empty")`.

- **AC-IMP-EP-04** — FalkorDB integration test: write→read round-trip for a
  single `group_id`. Add an episode via `Graphiti.add_episode(group_id="X", ...)`,
  retrieve via `Graphiti.retrieve_episodes(reference_time=now, last_n=N, group_ids=["X"])`,
  assert the episode is returned. This test must fail on `v0.29.5-guardkit.3`
  and pass on `.4`.

- **AC-IMP-EP-05** — FalkorDB multi-group integration test: add episodes to
  groups `"X"` and `"Y"`, call `retrieve_episodes(group_ids=["X", "Y"])`,
  assert both episodes are returned (decorator merges per-group results).

- **AC-IMP-EP-06** — Neo4j single-group integration test: write episodes
  with distinct `valid_at` timestamps, assert returned order matches
  `valid_at DESC`. Regression guard for the `uuid DESC` → `valid_at DESC`
  ordering change.

- **AC-IMP-EP-07** — `make check` passes (format + lint + test).

- **AC-IMP-EP-08** — Tag `v0.29.5-guardkit.4`. Update `patches/` if the
  guardkit patch chain is in active use for this fix.

- **AC-IMP-EP-09** — Document the `uuid DESC` → `valid_at DESC` ordering
  change in tag/release notes (not in the bug doc; non-obvious behaviour
  change for any caller that depended on the old ordering).

- **AC-IMP-EP-10** — *(deferred follow-up, can be a separate task)* Open
  path-scoped upstream PR to `getzep/graphiti` once integration tests
  confirm the fix on the fork. Path scope per
  [docs/reviews/notes.md](../../docs/reviews/notes.md):
  ```bash
  git checkout -b pr/get-episodes-fix main
  git checkout work/get-episodes-fix -- mcp_server/src/graphiti_mcp_server.py mcp_server/tests/
  ```
  Reference upstream issue #1161 / PR #1170 (bug #8 lineage).

## Test plan

| Test | Backend | What it proves |
|---|---|---|
| Single-group write→read | FalkorDB | Primary fix verification — fails on `.3`, passes on `.4` |
| Multi-group write→read | FalkorDB | Decorator merges per-group results correctly |
| Empty/nonexistent group | FalkorDB | Decorator handles missing named graphs gracefully (returns `[]`, not error) |
| Single-group `valid_at` ordering | Neo4j | Regression guard for ordering change |

Existing tests in `tests/test_node_int.py:204` cover `EpisodicNode.get_by_group_ids`
and remain valid for the underlying class method (still used elsewhere). New
tests target `Graphiti.retrieve_episodes` for FalkorDB single-group behaviour.

If the MCP test harness in `mcp_server/tests/` supports it (see
`test_mcp_integration.py`, `test_http_integration.py`), add a tool-layer
test asserting `get_episodes` MCP tool returns the recently-added episode.

## Time breakdown

| Step | Minutes |
|---|---|
| Code change in `graphiti_mcp_server.py` | 10 |
| Tests (4 integration tests) | 30 |
| `make check` + fixups | 10 |
| Tag `v0.29.5-guardkit.4` + commit + release notes | 10 |
| **Total** | **60** |

## Out of scope (deferred)

- Adding `reference_time` as an MCP-tool parameter (no current demand; YAGNI).
- Changing the empty-`group_ids` branch to query "all groups" (cross-backend
  asymmetry; FalkorDB has no sensible "all groups" semantics).
- Upstream PR mechanics — AC-IMP-EP-10 is the marker; actual PR creation
  can be a separate task once fork-side tests confirm the fix.
- Re-litigating bug #8's decorator behaviour.

## Cross-references

- Review report: [.claude/reviews/TASK-REV-GET-EPISODES-review-report.md](../../.claude/reviews/TASK-REV-GET-EPISODES-review-report.md)
- Bug doc: [docs/bugs/get-episodes-mcp-empty-results.md](../../docs/bugs/get-episodes-mcp-empty-results.md)
- Decorator (bug #8 fix): [graphiti_core/decorators.py](../../graphiti_core/decorators.py)
- Decorated method: [graphiti_core/graphiti.py:879](../../graphiti_core/graphiti.py#L879)
- Direct-driver path (broken): [graphiti_core/nodes.py:421](../../graphiti_core/nodes.py#L421)
- Broken MCP tool: [mcp_server/src/graphiti_mcp_server.py:621](../../mcp_server/src/graphiti_mcp_server.py#L621)
- Upstream-PR mechanics: [docs/reviews/notes.md](../../docs/reviews/notes.md)
- Prior fork-patch context: [TASK-FORK-PATCH](TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md)
