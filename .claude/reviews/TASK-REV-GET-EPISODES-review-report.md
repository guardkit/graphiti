# Review Report: TASK-REV-GET-EPISODES

## Executive Summary

**Bug**: MCP `get_episodes` returns `[]` on FalkorDB single-group queries because it bypasses the `@handle_multiple_group_ids` decorator (bug #8) by calling `EpisodicNode.get_by_group_ids` directly with the shared `client.driver`, hitting the wrong named graph.

**Recommended fix**: Route through `client.retrieve_episodes(...)` — already decorated. One-method swap, ~6 lines of diff in `mcp_server/src/graphiti_mcp_server.py`. Inherits all current and future decorator behaviour.

**Decisions locked**:
1. Fix path: **Recommended** (route through `Graphiti.retrieve_episodes`).
2. `reference_time`: **Hardcode `datetime.now(timezone.utc)`** — no new MCP param.
3. Empty-`group_ids` branch: **Preserve `[]` behaviour** — do not route through `retrieve_episodes(group_ids=None)`.
4. Upstream PR: **Yes, candidate** — path-scoped to `mcp_server/src/graphiti_mcp_server.py`, after fork tag `v0.29.5-guardkit.4` lands and tests pass.
5. Neo4j regression risk: **Low**, with one documented behaviour change (ordering flips `uuid DESC` → `valid_at DESC`, which is a correction).

**Follow-on**: Implementation task drafted below (~60 min, target tag `v0.29.5-guardkit.4`).

## Review Details

- **Mode**: Decision
- **Depth**: Standard
- **Duration**: ~30 min (bug doc was already comprehensive)
- **Reviewer**: Direct codebase analysis (no agent dispatch — decision review with fully-specified scope)
- **Graphiti context**: Skipped (per task body: avoid round-tripping review through MCP path under review)

## Findings

### F1. Bug reproduction confirmed via code inspection (AC-REV-EP-01)

Code paths verified:

| Location | Behaviour |
|---|---|
| [mcp_server/src/graphiti_mcp_server.py:649-654](mcp_server/src/graphiti_mcp_server.py#L649-L654) | Imports `EpisodicNode` and calls `.get_by_group_ids(client.driver, ...)` directly — bypasses `Graphiti` instance methods entirely. |
| [graphiti_core/decorators.py:53-58](graphiti_core/decorators.py#L53-L58) | `@handle_multiple_group_ids` only triggers when called on `Graphiti` instance with `self.clients.driver.provider == FALKORDB`. Class-method call path doesn't hit this. |
| [graphiti_core/nodes.py:421-459](graphiti_core/nodes.py#L421-L459) | `EpisodicNode.get_by_group_ids` runs `MATCH (e:Episodic) WHERE e.group_id IN $group_ids` against whatever graph the passed driver is bound to. |
| [graphiti_core/graphiti.py:879-931](graphiti_core/graphiti.py#L879-L931) | `Graphiti.retrieve_episodes` is decorated with `@handle_multiple_group_ids` — picks up FalkorDB per-group driver-clone behaviour automatically. |

On FalkorDB the per-group named-graph layout means `client.driver` (default graph) does not contain episodes written for `group_id="X"` (which live in named graph `X`). Bug claim is consistent with code; no runtime reproduction needed before implementation. Reproduction will be the regression test in the implementation task.

### F2. Two fix shapes, recommended is unambiguous (AC-REV-EP-02)

**Fix A (Recommended) — route through `Graphiti.retrieve_episodes`**

```python
from datetime import datetime, timezone

if effective_group_ids:
    episodes = await client.retrieve_episodes(
        reference_time=datetime.now(timezone.utc),
        last_n=max_episodes,
        group_ids=effective_group_ids,
    )
else:
    episodes = []
```

Rationale:
- DRY — single source of truth for FalkorDB per-group dispatch lives in `decorators.py`.
- Future-proof — when `@handle_multiple_group_ids` evolves, MCP tool inherits the change.
- Symmetric with existing MCP `add_memory`, which already uses high-level `Graphiti.add_episode`, not internal node constructors.
- ~6-line diff (import + body change + drop the local `EpisodicNode` import).

**Fix B (Alternative) — replicate decorator logic inline**

```python
# Clone driver per group_id, call EpisodicNode.get_by_group_ids per clone, merge
```

Rejected:
- Duplicates centralised logic — has to be revisited every time `decorators.py` changes.
- Larger diff, more failure surface.
- No upside over Fix A.

**Decision: Fix A.**

### F3. `reference_time` semantics — hardcode `now`, no new param (AC-REV-EP-03)

`Graphiti.retrieve_episodes` requires `reference_time: datetime` ([graphiti.py:882](graphiti_core/graphiti.py#L882)) and FalkorDB applies it as `WHERE e.valid_at <= $reference_time` ([falkordb/operations/episode_node_ops.py:257](graphiti_core/driver/falkordb/operations/episode_node_ops.py#L257)).

Current MCP `get_episodes` exposes only `group_ids` and `max_episodes` — no time semantics. Documented behaviour is "most recent N episodes".

**Decision: hardcode `reference_time = datetime.now(timezone.utc)`.**

Rationale:
- Matches documented "most recent N" intent.
- No public-surface change to the MCP tool — zero breaking change for existing clients.
- Time-travel queries are a power feature with no current demand; YAGNI.
- If demand surfaces, adding an optional `reference_time` param later is forward-compatible (hardcoded `now` becomes the default).

### F4. Empty-`group_ids` branch — preserve `[]` (AC-REV-EP-04)

Current behaviour ([mcp_server/src/graphiti_mcp_server.py:655-658](mcp_server/src/graphiti_mcp_server.py#L655-L658)): when `effective_group_ids` is empty (caller passed `None` AND no `config.graphiti.group_id` configured), returns `[]` unconditionally.

**Decision: preserve `[]` behaviour. Do not route through `retrieve_episodes(group_ids=None)`.**

Rationale:
- On FalkorDB, "all groups" has no sensible meaning — episodes live in per-group named graphs; the shared default graph is empty of episodes.
- Routing `group_ids=None` through the decorator: the check at [decorators.py:53-58](graphiti_core/decorators.py#L53-L58) requires truthy `group_ids` — empty list/None falls through to normal execution on the shared driver. On FalkorDB this would query an empty graph; on Neo4j it would return all-groups data. **Cross-backend asymmetry of exactly the kind we're fixing** — explicit anti-pattern.
- The fallback chain already prefers `config.graphiti.group_id` — the empty branch only triggers when neither caller nor config specifies a group, which is a configuration error, not a legitimate query.
- Surgical change. No new behaviour to reason about.

Optional (not required): emit a `logger.warning` when the empty branch fires. Defer to implementation task author's judgement.

### F5. Neo4j regression risk — low, one documented behaviour change (AC-REV-EP-06)

Neo4j uses a single shared graph; `client.driver` and `driver.clone(database=gid)` are equivalent. `WHERE e.group_id IN $group_ids` filter returns the same set.

**Behaviour change to flag** (not in the bug doc):

| Field | Old (`get_by_group_ids`) | New (`retrieve_episodes`) |
|---|---|---|
| Ordering | `ORDER BY uuid DESC` ([nodes.py:455](graphiti_core/nodes.py#L455)) | `ORDER BY e.valid_at DESC` ([falkordb episode_node_ops.py:266](graphiti_core/driver/falkordb/operations/episode_node_ops.py#L266), [graph_data_operations.py](graphiti_core/utils/maintenance/graph_data_operations.py#L67)) |
| Time filter | none | `WHERE e.valid_at <= $reference_time` |

UUID order ≈ insertion order roughly but is **not** strictly time-ordered (UUID4 is random). `valid_at DESC` is the documented bi-temporal field for "most recent" — switching to it is a **correction**, not a regression. Document in the changelog / patch notes for `v0.29.5-guardkit.4`.

The `valid_at <= now` filter excludes future-dated episodes, which shouldn't exist in normal use; if they do (e.g., scheduled events), users get the more correct behaviour. Acceptable.

Risk level: **low**. No Neo4j smoke test required — confirm via reading and rely on the integration test (F6) as regression coverage.

### F6. Test coverage plan (AC-REV-EP-07)

Required tests in implementation task:

1. **FalkorDB single-group write→read round-trip** *(primary fix verification)*:
   - `add_episode(group_id="X", ...)` → `retrieve_episodes(group_ids=["X"], reference_time=now)` returns the episode.
   - This is the test that fails on `v0.29.5-guardkit.3` and passes on `.4`.

2. **FalkorDB multi-group**:
   - Add episodes to `"X"` and `"Y"` → `retrieve_episodes(group_ids=["X","Y"])` returns both, merged by the decorator.

3. **FalkorDB empty-result**:
   - `retrieve_episodes(group_ids=["nonexistent"])` returns `[]`. Validates the decorator's per-group iteration handles missing graphs gracefully.

4. **Neo4j single-group write→read round-trip** *(regression guard for ordering change)*:
   - Write episodes with distinct `valid_at` timestamps; assert returned order matches `valid_at DESC`.

5. **MCP-tool layer** *(if existing MCP test harness covers it)*:
   - Verify `get_episodes` MCP tool calls `client.retrieve_episodes` with `reference_time=<now>`, `last_n=max_episodes`, `group_ids=effective_group_ids`. Existing MCP integration tests in `mcp_server/tests/` exercise the tool — extend them rather than building new harness.

Existing tests in [tests/test_node_int.py:204](tests/test_node_int.py#L204) cover `EpisodicNode.get_by_group_ids` and stay relevant for the underlying class method (still used elsewhere). New tests target `Graphiti.retrieve_episodes` for the FalkorDB single-group path.

### F7. Upstream-PR disposition (AC-REV-EP-05)

**Decision: candidate for upstream PR after fork tag lands.**

Rationale:
- Bug exists in `getzep/graphiti` upstream too — MCP server source matches; bug #8 fixed `decorators.py` but didn't touch `mcp_server/`.
- FalkorDB-only impact; Neo4j/other-backend behaviour unchanged (modulo the `valid_at` ordering correction, which is also an improvement upstream).
- Fix uses public `Graphiti.retrieve_episodes` API — no internal coupling, no test infrastructure churn.
- Path-scoped per [docs/reviews/notes.md](docs/reviews/notes.md):
  ```bash
  git checkout work/get-episodes-fix -- mcp_server/src/graphiti_mcp_server.py mcp_server/tests/
  ```
- Lineage matches bug #8 (upstream PR #1170 / issue #1161 referenced in [decorators.py:52](graphiti_core/decorators.py#L52)) — tell the same story upstream.

**Sequence**: ship in fork's `v0.29.5-guardkit.4` first → confirm via integration tests on FalkorDB → then path-scoped upstream PR.

## Recommendations

| # | Recommendation | Rationale |
|---|---|---|
| 1 | **Adopt Fix A**: route MCP `get_episodes` through `client.retrieve_episodes` | DRY, future-proof, ~6-line diff, symmetric with `add_memory` |
| 2 | Hardcode `reference_time = datetime.now(timezone.utc)` | Matches documented "most recent N" intent, no API surface change, YAGNI |
| 3 | Preserve empty-`group_ids` `[]` branch | Avoids cross-backend asymmetry; configuration-error scenario, not a legitimate query |
| 4 | Document `uuid DESC` → `valid_at DESC` ordering change in `v0.29.5-guardkit.4` notes | Non-obvious behaviour change, even though it's a correction |
| 5 | Add 4 integration tests (FalkorDB ×3, Neo4j ×1) before tagging | Regression coverage matches the surface area touched |
| 6 | After fork tag lands, open path-scoped upstream PR to `getzep/graphiti` | Real bug, narrow surface, public API only — high acceptance probability |

## Decision Matrix

| Option | Effort | Risk | DRY | Future-proof | Recommendation |
|---|---|---|---|---|---|
| A. Route through `retrieve_episodes` | Low (~10 min code) | Low | ✓ | ✓ | **Recommended** |
| B. Inline decorator replication | Medium (~30 min) | Medium (logic dup) | ✗ | ✗ | Reject |
| C. Defer / no fix | None | High (broken on FalkorDB) | — | — | Reject (bug confirmed) |

## Acceptance Criteria — Status

| AC | Status | Notes |
|---|---|---|
| AC-REV-EP-01 | ✓ Confirmed via code inspection | Runtime reproduction deferred to implementation task as the regression test |
| AC-REV-EP-02 | ✓ Decision: Fix A (route through `retrieve_episodes`) | See F2 |
| AC-REV-EP-03 | ✓ Decision: hardcode `now`, no new param | See F3 |
| AC-REV-EP-04 | ✓ Decision: preserve `[]` behaviour | See F4 |
| AC-REV-EP-05 | ✓ Decision: upstream PR candidate after fork tag | See F7 |
| AC-REV-EP-06 | ✓ Neo4j risk: low; ordering change documented | See F5 |
| AC-REV-EP-07 | ✓ Test coverage plan defined (4 tests minimum) | See F6 |
| AC-REV-EP-08 | ✓ Implementation task drafted | See below |

## Follow-on Implementation Task (draft)

```yaml
title: Fix MCP get_episodes to route through Graphiti.retrieve_episodes (FalkorDB)
task_type: implementation
priority: high
complexity: 2
estimated_minutes: 60
target_tag: v0.29.5-guardkit.4
related_to: TASK-REV-GET-EPISODES
tags: [graphiti, mcp, falkordb, bug-fix]
```

**Acceptance Criteria**:
- **AC-IMP-EP-01** — Replace direct `EpisodicNode.get_by_group_ids` call in `mcp_server/src/graphiti_mcp_server.py:649-654` with `await client.retrieve_episodes(reference_time=datetime.now(timezone.utc), last_n=max_episodes, group_ids=effective_group_ids)`. Drop the local `from graphiti_core.nodes import EpisodicNode` import; add `from datetime import datetime, timezone` if not already present.
- **AC-IMP-EP-02** — `reference_time` hardcoded to `datetime.now(timezone.utc)`; do not expose as MCP tool param.
- **AC-IMP-EP-03** — Preserve empty-`group_ids` `[]` branch unchanged (lines 655-658). Optional: add `logger.warning` when fired.
- **AC-IMP-EP-04** — Add FalkorDB integration test: write→read round-trip for single `group_id` via `Graphiti.retrieve_episodes` (or via MCP tool layer if test harness supports).
- **AC-IMP-EP-05** — Add FalkorDB multi-group test: write to two groups, retrieve from both, assert merged result.
- **AC-IMP-EP-06** — Add Neo4j single-group test: assert `valid_at DESC` ordering on returned episodes (regression guard for ordering change).
- **AC-IMP-EP-07** — `make check` passes (format, lint, test).
- **AC-IMP-EP-08** — Tag `v0.29.5-guardkit.4`; update `patches/` if guardkit patch chain is in use.
- **AC-IMP-EP-09** — Document `uuid DESC` → `valid_at DESC` ordering change in tag/release notes.
- **AC-IMP-EP-10** — *(deferred to follow-up)* Open path-scoped upstream PR to `getzep/graphiti` once integration tests confirm fix on the fork. Paths: `mcp_server/src/graphiti_mcp_server.py` + relevant `mcp_server/tests/` additions.

**Estimated breakdown**: 10 min code change · 30 min tests · 15 min `make check` + tag/commit · 5 min release-notes blurb.

## Cross-references

- Bug doc: [docs/bugs/get-episodes-mcp-empty-results.md](docs/bugs/get-episodes-mcp-empty-results.md)
- Decorator (bug #8 fix): [graphiti_core/decorators.py](graphiti_core/decorators.py)
- Decorated method: [graphiti_core/graphiti.py:879](graphiti_core/graphiti.py#L879)
- Direct-driver path (broken): [graphiti_core/nodes.py:421](graphiti_core/nodes.py#L421)
- Broken MCP tool: [mcp_server/src/graphiti_mcp_server.py:621](mcp_server/src/graphiti_mcp_server.py#L621)
- Upstream-PR mechanics: [docs/reviews/notes.md](docs/reviews/notes.md)
- Prior fork-patch context: [TASK-FORK-PATCH](tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) (referenced from task)
