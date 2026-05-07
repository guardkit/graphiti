# Bug: MCP `get_episodes` tool returns empty results on FalkorDB

**Status:** open
**Severity:** medium (affects retrieval; no data loss)
**Tag affected:** `v0.29.5-guardkit.3` (and earlier guardkit tags)
**Component:** `mcp_server/src/graphiti_mcp_server.py`

## Summary

The MCP `get_episodes` tool queries FalkorDB on the shared default driver
instead of the per-group named-graph clone, so single-group calls return
empty results — the same class of failure that bug #8 fixed elsewhere via
the `handle_multiple_group_ids` decorator on `Graphiti` methods.

## Why the v0.29.5-guardkit.3 patch set does not fix it

`v0.29.5-guardkit.3` includes bug #8 (`graphiti_core/decorators.py`):
`handle_multiple_group_ids` now takes the FalkorDB per-group driver-clone
path for single-group calls too, not only multi-group calls. That fix is
applied to `Graphiti` methods that are decorated, e.g.
`Graphiti.retrieve_episodes` (`graphiti_core/graphiti.py:879`).

The MCP `get_episodes` tool bypasses that decorator entirely:

```python
# mcp_server/src/graphiti_mcp_server.py:649-654
from graphiti_core.nodes import EpisodicNode

if effective_group_ids:
    episodes = await EpisodicNode.get_by_group_ids(
        client.driver, effective_group_ids, limit=max_episodes
    )
```

`EpisodicNode.get_by_group_ids` (`graphiti_core/nodes.py:422`) takes a
driver, runs Cypher with `WHERE e.group_id IN $group_ids`, and returns
nodes from whatever graph the passed-in driver is bound to. On FalkorDB
the multi-graph layout means episodes for group `G` live in a named graph
keyed off `G`, not the shared default graph. Because `get_episodes`
passes the shared `client.driver`, the lookup hits the wrong graph and
returns `[]`.

## Reproduction

1. Add an episode via MCP `add_memory` for `group_id="X"`.
2. Call MCP `get_episodes(group_ids=["X"])`.
3. Expected: the episode just added.
4. Actual: `{"message": "No episodes found", "episodes": []}`.

## Suggested fix

Route the MCP tool through `Graphiti.retrieve_episodes` instead of
calling `EpisodicNode.get_by_group_ids` directly. `retrieve_episodes`
is already decorated with `@handle_multiple_group_ids`
(`graphiti_core/graphiti.py:879`), so it picks up the bug #8 driver-clone
behaviour for FalkorDB automatically — single- and multi-group calls
work the same way.

Sketch:

```python
from datetime import datetime, timezone

episodes = await client.retrieve_episodes(
    reference_time=datetime.now(timezone.utc),
    last_n=max_episodes,
    group_ids=effective_group_ids,
)
```

Notes:
- `retrieve_episodes` requires a `reference_time`. The current MCP tool
  has no equivalent parameter; default to "now" so it returns the most
  recent `max_episodes` episodes, which matches the existing tool's
  documented behaviour.
- The empty-`group_ids` branch (line 656–658) currently returns `[]`
  unconditionally. Decide whether to keep that or route through
  `retrieve_episodes` with `group_ids=None` for an all-groups view.

## Alternative fix (not recommended)

Replicate the decorator logic inline: clone the driver per group_id with
`driver.with_database(group_id)`, call `EpisodicNode.get_by_group_ids`
on each clone, merge the results. Works but duplicates logic that the
decorator already centralises and has to be revisited every time the
decorator changes.

## References

- bug #8 fix: `graphiti_core/decorators.py` (in v0.29.5-guardkit.3)
- decorated public method: `Graphiti.retrieve_episodes` at
  `graphiti_core/graphiti.py:879`
- direct-driver path used by the broken tool:
  `EpisodicNode.get_by_group_ids` at `graphiti_core/nodes.py:422`
- broken MCP tool: `get_episodes` at
  `mcp_server/src/graphiti_mcp_server.py:621`
