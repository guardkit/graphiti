# Bug: MCP `get_episodes` tool returns empty results on FalkorDB

**Status:** RESOLVED in `v0.29.5-guardkit.5` (2026-05-07)
**Severity:** medium (affects retrieval; no data loss)
**Tag affected:** `v0.29.5-guardkit.3` and `v0.29.5-guardkit.4` (and earlier)
**Tag fixed in:** `v0.29.5-guardkit.5`
**Component:** `mcp_server/src/graphiti_mcp_server.py` + `mcp_server/docker/Dockerfile.standalone` + `mcp_server/pyproject.toml`

---

## Resolution (2026-05-07)

**The original "Suggested fix" below shipped in `v0.29.5-guardkit.4`
(commit `83abbec`) and was correct as far as it went, but it did not
resolve the symptom because of a separate packaging defect that
orphaned every fork patch in `graphiti_core/` at runtime.** The full
fix needed two layers, both required:

### Layer 1 (v0.29.5-guardkit.4, MCP-side routing — commit `83abbec`)

`mcp_server/src/graphiti_mcp_server.py` `get_episodes` routes through
`Graphiti.retrieve_episodes` (decorated with
`@handle_multiple_group_ids`) instead of calling
`EpisodicNode.get_by_group_ids` directly with the shared driver. Exactly
as proposed in the original "Suggested fix" section below.

### Layer 2 (v0.29.5-guardkit.5, Dockerfile vendoring — commit `4ba8a4d`)

The decorator fix (bug #8, commit `7a914ec`) that drops the
`len(group_ids) > 1` gate had been in `graphiti_core/decorators.py`
since `v0.29.5-guardkit.3` — but it never reached the running image.
`mcp_server/docker/Dockerfile.standalone` was deliberately stripping
`[tool.uv.sources]` from `mcp_server/pyproject.toml` and pinning
`graphiti-core[neo4j,falkordb]==0.28.1` from PyPI, so every fork patch
in `graphiti_core/` (#5/#8/#9/#10/#11/#12) was on disk but not in the
runtime venv:

```dockerfile
# pre-fix
RUN sed -i '/\[tool\.uv\.sources\]/,/graphiti-core/d' pyproject.toml && \
    sed -i "s/graphiti-core\[falkordb\][>=]\+[0-9]\+\.[0-9]\+\.[0-9]\+/graphiti-core[neo4j,falkordb]==${GRAPHITI_CORE_VERSION}/" pyproject.toml && \
    rm -f uv.lock && uv lock
```

Empirically confirmed on `promaxgb10-41b1` against the running
`v0.29.5-guardkit.4` container (2026-05-07): the venv at
`.venv/lib/python3.11/site-packages/graphiti_core/decorators.py` still
had `len(group_ids) > 1` despite the source-tree fix being in place.

**Why this orphaned the patches:** upstream removed
`[tool.uv.sources] graphiti-core = { path = "../", editable = true }`
in commit `e1e652e` (PR #1186, "Pin mcp_server to graphiti-core
0.26.3"). The fork inherited that change without re-adding the
override, so both Docker builds and local `uv sync` against
`mcp_server/` resolved graphiti-core from PyPI.

**The Dockerfile fix:** build context becomes the fork root (was
`mcp_server/`), the image lays out `/app/{pyproject.toml,README.md,graphiti_core/}`
one level above `/app/mcp/`, and `mcp_server/pyproject.toml` re-adds
`[tool.uv.sources] graphiti-core = { path = "../", editable = true }`.
`uv sync` now editable-installs graphiti-core from `/app/`. `WORKDIR`
stays `/app/mcp` because consumers bind-mount to
`/app/mcp/{config,bootstrap.py}`.

### Verification (2026-05-07, on `promaxgb10-41b1`, FalkorDB at `whitestocks`)

Pre-fix (any guardkit tag through `.4`):
```
single-group get_episodes(["command_workflows"]) → [] (FalkorDB has 169 episodes in that named graph)
multi-group get_episodes(["command_workflows", "patterns"]) → 6 episodes
```

Post-fix (`v0.29.5-guardkit.5`):
```
single-group get_episodes(["command_workflows"])           → 3 episodes (PASS)
single-group get_episodes(["patterns"])                    → 3 episodes (PASS)
single-group get_episodes(["guardkit__project_decisions"]) → 3 episodes (PASS)
single-group get_episodes(["guardkit__task_outcomes"])     → 3 episodes (PASS)
multi-group regression check                                → 8 episodes (PASS)
```

### Lessons (logged to GuardKit memory)

- **The fork's appearance of containing bug fixes was a false-green.**
  Source-level audit looked clean; runtime behaviour was upstream-broken.
  Verifying a fix by reading the patched file in `graphiti_core/` is
  insufficient when the runtime image installs from PyPI.
- **The fork is a fork *because* the patches in `graphiti_core/` are
  needed at runtime.** Future Dockerfile changes in this fork must
  never strip `[tool.uv.sources]`.

### Companion fix

`v0.29.5-guardkit.6` (commit `c8b5a65`, 2026-05-07) fixes a separate
write-path issue (TASK-INF-5054) that prevented `add_memory` from
completing extraction on local LLM endpoints. See
[`llm-endpoint-misrouting-task-inf-5054.md`](./llm-endpoint-misrouting-task-inf-5054.md).

### Refs

- Tag annotation: `git show v0.29.5-guardkit.5`
- Companion guardkit commit: `705b7000` on `github.com/guardkit/guardkit`
- Runbook verification: GuardKit `docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md` Phase 8.1

---

## Original analysis (preserved for posterity)


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
