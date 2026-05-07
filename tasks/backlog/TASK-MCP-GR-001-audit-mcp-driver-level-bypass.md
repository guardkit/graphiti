---
id: TASK-MCP-GR-001
title: Audit MCP driver-level group-id bypass (get_episodes + 3 related tools)
status: backlog
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
priority: high
task_type: review
complexity: 4
estimated_minutes: 120
tags: [mcp, falkordb, group-id, multi-graph, review, audit]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Audit MCP driver-level group-id bypass (get_episodes + 3 related tools)

**PRIORITY**: high
**TASK_TYPE**: review
**COMPLEXITY**: 4
**ESTIMATED_MINUTES**: 120
**TAGS**: mcp, falkordb, group-id, multi-graph, review, audit

---

## Why this is a review task, not an implementation task

The user has filed a confirmed bug against `get_episodes` and identified
three additional MCP tools that follow the same suspicious pattern
(direct driver-level lookup with no per-group graph routing). Before
patching, we need:

1. Verify the suspected three tools actually have the bug (read the
   code, don't guess).
2. Decide on the fix shape that should apply to all of them — route
   through a `Graphiti` client method (preferred, hits the
   `@handle_multiple_group_ids` decorator) vs. replicate the
   driver-clone logic inline. Pick one and stick to it across all
   tools.
3. Produce a follow-up implementation task with concrete file/line
   changes and a verification plan.

Doing the analysis as a separate task keeps the implementation task
small and reviewable, and avoids guessing the right fix shape.

## Bug report (verbatim from user)

> **Bug**: `get_episodes` tool queries default graph instead of
> group-specific graph
>
> **Location**: `mcp_server/src/graphiti_mcp_server.py`,
> `get_episodes` function
>
> **Problem**: The `get_episodes` MCP tool returns empty results
> even when episodes exist for the requested `group_ids`. The tool
> calls `EpisodicNode.get_by_group_ids(client.driver,
> effective_group_ids, limit=max_episodes)` which executes a Cypher
> query against the driver's default graph (configured as
> `default_db` in `graphiti-mcp-config.yaml`). However,
> graphiti-core creates a separate FalkorDB graph per `group_id` —
> episodes written via `client.add_episode(group_id="student-lilymay")`
> are stored in a FalkorDB graph named `student-lilymay`, not in
> `default_db`.
>
> **Evidence**:
> ```bash
> # default_db contains zero episodes
> redis-cli -h whitestocks GRAPH.QUERY default_db \
>   "MATCH (e:Episodic) RETURN count(e)"
> → 0
>
> # student-lilymay graph contains the actual episodes
> redis-cli -h whitestocks GRAPH.QUERY student-lilymay \
>   "MATCH (e:Episodic) RETURN count(e), e.name LIMIT 5"
> → 3 episodes: "topic_confidence_updated" (×2), "session_completed"
> ```
>
> **Why other tools work**: `search_nodes` and `search_memory_facts`
> use graphiti-core's `client.search_()` / `client.search()`
> methods, which are group-aware and internally switch to the
> correct per-group-id graph. `get_episodes` bypasses this layer by
> calling the driver-level `EpisodicNode.get_by_group_ids()`
> directly, which has no group-to-graph routing logic.
>
> **Required fix**: The `get_episodes` tool needs to use a
> graphiti-core client method that is group-aware (similar to how
> `search_nodes` uses `client.search_()`), or it needs to replicate
> the group-id-to-graph resolution that the search methods perform
> internally before querying `EpisodicNode.get_by_group_ids`. The
> same pattern should be audited for `delete_episode` and
> `get_entity_edge` which also call driver-level methods directly
> and may have the same issue.
>
> **Affected tools (audit candidates)**:
> - `get_episodes` — confirmed broken
> - `delete_episode` — uses `EpisodicNode.get_by_uuid(client.driver, uuid)` — likely same issue
> - `delete_entity_edge` — uses `EntityEdge.get_by_uuid(client.driver, uuid)` — likely same issue
> - `get_entity_edge` — uses `EntityEdge.get_by_uuid(client.driver, uuid)` — likely same issue
>
> **Reproduction**: Call `get_episodes(group_ids=["student-lilymay"])`
> via the MCP — returns empty. Then query FalkorDB directly on the
> `student-lilymay` graph — episodes are present.

## Existing context in this repo

A first-pass bug stub already exists at
`docs/bugs/get-episodes-mcp-empty-results.md` (committed as part of
`v0.29.5-guardkit.3` work). It points at:

- The broken call site in `mcp_server/src/graphiti_mcp_server.py:621`
  (`get_episodes`), specifically the
  `EpisodicNode.get_by_group_ids(client.driver, ...)` call at lines
  651–654.
- `graphiti_core/nodes.py:422` — the driver-level
  `EpisodicNode.get_by_group_ids` classmethod that runs raw Cypher
  against whatever driver is passed in.
- `graphiti_core/graphiti.py:879` — `Graphiti.retrieve_episodes`,
  which IS decorated with `@handle_multiple_group_ids` and so picks
  up the bug #8 driver-clone behaviour.

This task extends the analysis from one tool to four and produces
the follow-up implementation task.

## Scope

### In scope

1. **Confirm the bug** in the three suspected tools by reading the
   code and tracing the call path. Document the exact line numbers
   and the call signature each tool uses.
2. **Identify the routing seam**. Trace what
   `client.search_()` / `client.search()` actually do to land on the
   right per-group named graph. Is it the
   `@handle_multiple_group_ids` decorator (bug #8 path), something
   else inside `Graphiti.search_()`, or a separate seam? Pin down
   the exact mechanism so the fix can use the same one.
3. **Inventory available group-aware client methods** on `Graphiti`
   that could replace each direct driver call:
   - `get_episodes` → `Graphiti.retrieve_episodes` (already known)
   - `delete_episode` → ? (look for an episode-delete on `Graphiti`)
   - `get_entity_edge` → ? (look for an edge-get on `Graphiti`)
   - `delete_entity_edge` → ? (look for an edge-delete on `Graphiti`)
4. **Recommend a fix shape** (one approach for all four tools) with
   rationale. Two candidates:
   - **A. Route through `Graphiti` methods.** Preferred if all four
     tools have a corresponding decorated method. Lowest duplication,
     auto-inherits any future fixes to the decorator.
   - **B. Inline driver-clone.** Replicate
     `handle_multiple_group_ids`'s FalkorDB clone-per-group_id logic
     in the MCP tools. Required if no `Graphiti` method exists. More
     duplication, more places to keep in sync.
5. **Verification plan**. Reproduction recipe per tool (mirroring the
   `redis-cli GRAPH.QUERY` evidence pattern in the bug report) so the
   follow-up implementation task can prove its fix.

### Out of scope

- Writing the fix. That's the follow-up task.
- Touching `graphiti_core/` (the bug is entirely in the MCP server
  layer; `graphiti_core` already exposes group-aware methods).
- Auditing tools beyond the four named ones unless the analysis
  trivially surfaces another with the same pattern.

## Acceptance criteria

- [ ] Each of the four named tools has a confirmed verdict: bugged /
      not bugged, with exact file:line citation for the offending
      driver call.
- [ ] The group-routing seam is identified by name and location
      (decorator vs. method internals vs. driver method) with a
      concrete code reference.
- [ ] A fix-shape recommendation is documented with rationale,
      covering all four tools. If shapes have to differ across tools,
      that's stated explicitly and justified.
- [ ] A follow-up implementation task is filed in `tasks/backlog/`
      with concrete edits and a verification plan. Suggested ID:
      `TASK-MCP-GR-002-fix-mcp-driver-level-bypass`.
- [ ] Findings are appended to or supersede
      `docs/bugs/get-episodes-mcp-empty-results.md` (the existing
      stub) so all four tools are documented in one place.

## Deliverable

A short review report (committed under `docs/reviews/` or appended to
the existing bug stub) covering:

1. Per-tool verdict table (tool, file:line, broken? Y/N, evidence).
2. Routing-seam analysis (where group-id → graph happens today).
3. Fix-shape recommendation with rationale.
4. Pointer to the follow-up implementation task.

## Notes

- `v0.29.5-guardkit.3` (the current fork tag) does NOT fix this
  class of bug — it only restores the four-file `graphiti_core`
  patch set (decorator + RediSearch). The MCP server layer is
  untouched. Whatever this audit recommends will land in a future
  guardkit tag (probably `v0.29.5-guardkit.4`).
- The user has confirmed `get_episodes` is broken on FalkorDB; the
  three suspected tools are unconfirmed but the call signature
  (`*.get_by_uuid(client.driver, uuid)`) is structurally identical
  to the broken pattern.
- Graphiti's MCP server is at
  `mcp_server/src/graphiti_mcp_server.py`. The four tool
  definitions to audit are decorated with `@mcp.tool()`.

## References

- Bug stub: `docs/bugs/get-episodes-mcp-empty-results.md`
- Broken tool: `mcp_server/src/graphiti_mcp_server.py:621`
  (`get_episodes`)
- Driver-level call: `graphiti_core/nodes.py:422`
  (`EpisodicNode.get_by_group_ids`)
- Group-aware decorated method:
  `graphiti_core/graphiti.py:879` (`Graphiti.retrieve_episodes`)
- Decorator (bug #8 in v0.29.5-guardkit.3):
  `graphiti_core/decorators.py` (`handle_multiple_group_ids`)
