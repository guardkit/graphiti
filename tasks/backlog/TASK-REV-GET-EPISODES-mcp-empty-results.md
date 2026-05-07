---
id: TASK-REV-GET-EPISODES
title: Review fix path for MCP get_episodes empty-results on FalkorDB
status: completed
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
priority: high
task_type: review
review_mode: decision
review_depth: standard
complexity: 3
estimated_minutes: 45
tags: [graphiti, mcp, falkordb, review, decision]
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  decision_fix_path: recommended_route_through_retrieve_episodes
  decision_reference_time: hardcode_now_utc
  decision_empty_group_ids: preserve_empty_list
  decision_upstream_pr: candidate_after_fork_tag
  neo4j_regression_risk: low_with_ordering_change
  findings_count: 7
  recommendations_count: 6
  report_path: .claude/reviews/TASK-REV-GET-EPISODES-review-report.md
  checkpoint_decision: implement
  follow_on_task: TASK-FIX-GET-EPISODES
  completed_at: 2026-05-07T00:00:00Z
---

# Review fix path for MCP `get_episodes` empty-results on FalkorDB

**PRIORITY**: high
**TASK_TYPE**: review (decision)
**COMPLEXITY**: 3
**ESTIMATED_MINUTES**: 45

---

## Source bug document

[docs/bugs/get-episodes-mcp-empty-results.md](../../docs/bugs/get-episodes-mcp-empty-results.md)
— full reproduction, root cause, and two candidate fixes already written up.

## One-line summary

MCP `get_episodes` calls `EpisodicNode.get_by_group_ids` directly with the
shared `client.driver`, bypassing the `@handle_multiple_group_ids` decorator
that bug #8 (in `v0.29.5-guardkit.3`) extended to single-group calls. On
FalkorDB the per-group named-graph layout means the lookup hits the wrong
graph and returns `[]`.

## Why this is a review task, not a `/task-work` task

The bug doc proposes two fix shapes that are not equivalent in scope:

1. **Recommended** — route the MCP tool through `Graphiti.retrieve_episodes`
   (already decorated). One-method swap; inherits future decorator changes
   for free.
2. **Alternative** — replicate the decorator logic inline in the MCP tool
   (clone driver per `group_id`, call `get_by_group_ids` per clone, merge).
   Works but duplicates centralised logic.

There are also two open scope questions that change the public surface of
the MCP tool:

- **`reference_time` semantics** — `retrieve_episodes` requires one; current
  MCP tool has no equivalent param. Default to `now` (matches documented
  "most recent N" behaviour) or expose a parameter?
- **Empty-`group_ids` branch** — currently returns `[]` unconditionally
  (line 656–658). Keep as-is, or route through `retrieve_episodes` with
  `group_ids=None` for an all-groups view?

These are decisions, not code — `/task-review` is the right gate before
opening a `/task-work` ticket.

## Review scope

In scope:

- Confirm bug reproduction matches the writeup (steps 1–4 in the bug doc).
- Lock the fix path: recommended (route through `retrieve_episodes`) vs
  alternative (inline decorator replication).
- Decide `reference_time` handling: hardcoded `now` vs new MCP param.
- Decide empty-`group_ids` semantics: preserve existing `[]` behaviour vs
  switch to all-groups view.
- Decide whether the fix lands in this fork only (next guardkit tag) or is
  also a candidate for an upstream PR to `getzep/graphiti`.
- Identify regression risk on Neo4j (single shared graph — should be a
  no-op) and integration-test coverage gaps.

Out of scope:

- Re-litigating bug #8's decorator behaviour (already shipped in
  `v0.29.5-guardkit.3`).
- Broader MCP tool API redesign — keep the change surgical.
- The `add_memory` write path (separately tracked, already verified by
  AC-FORK-08-3 in TASK-FPA-009).

## Acceptance Criteria

- **AC-REV-EP-01** — Bug reproduction confirmed against current
  `v0.29.5-guardkit.3` deployment (or rationale recorded if reproduction
  is deferred to the implementation task).
- **AC-REV-EP-02** — Fix path decision recorded: recommended vs alternative,
  with stated rationale.
- **AC-REV-EP-03** — `reference_time` semantics decided and documented
  (hardcoded `now` vs new param; if new param, default value specified).
- **AC-REV-EP-04** — Empty-`group_ids` branch behaviour decided
  (preserve `[]` vs route through `retrieve_episodes`).
- **AC-REV-EP-05** — Upstream-PR disposition recorded (fork-only vs
  candidate for `getzep/graphiti` PR; if upstream, identify path-scoped
  files per `docs/reviews/notes.md` PR pattern).
- **AC-REV-EP-06** — Neo4j regression risk assessed (expected no-op given
  single-graph layout; confirm via reading or smoke test).
- **AC-REV-EP-07** — Test coverage plan defined: which integration tests
  must accompany the fix (FalkorDB single-group write→read round-trip at
  minimum).
- **AC-REV-EP-08** — Follow-on implementation task drafted (title, AC list,
  estimated minutes, target tag e.g. `v0.29.5-guardkit.4`) — created via
  `/task-create` only after review checkpoint accepted.

## Decision checkpoint outcomes

After `/task-review` completes, one of:

- **[A]ccept** — Decisions locked, follow-on `/task-create` for the
  implementation task (with AC inherited from this review).
- **[I]mplement** — Same as Accept; review tool auto-generates the
  implementation task stub.
- **[R]evise** — Reproduction unclear or fix paths produce more questions;
  schedule a deeper investigation (e.g. read FalkorDB driver-clone code
  path end-to-end, add probe).
- **[C]ancel** — Bug not reproducible / fix already in flight elsewhere /
  obsolete after another change.

## Cross-references

- Bug doc: [docs/bugs/get-episodes-mcp-empty-results.md](../../docs/bugs/get-episodes-mcp-empty-results.md)
- Decorator fix (bug #8): `graphiti_core/decorators.py`
  (shipped in `v0.29.5-guardkit.3`)
- Decorated public method: `graphiti_core/graphiti.py:879`
  (`Graphiti.retrieve_episodes`)
- Direct-driver path used by the broken tool:
  `graphiti_core/nodes.py:422` (`EpisodicNode.get_by_group_ids`)
- Broken MCP tool: `mcp_server/src/graphiti_mcp_server.py:621`
  (`get_episodes`, with `EpisodicNode.get_by_group_ids` call at 649–654)
- Prior fork-patch context: [TASK-FORK-PATCH](TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md)
- Upstream-PR mechanics: [docs/reviews/notes.md](../../docs/reviews/notes.md)
  (path-scoped `git checkout <branch> -- <paths>` pattern)

## How to run the review

```bash
cd /home/richardwoollcott/Projects/appmilla_github/graphiti
/task-review TASK-REV-GET-EPISODES --mode=decision --depth=standard --no-questions
```

Same rationale as the FORK-PATCH review (see `docs/reviews/notes.md`):
`--mode=decision` because the open items are decisions not analysis;
`--depth=standard` because the bug doc is already comprehensive;
`--no-questions` because review scope is fully specified above.

Skip `--capture-knowledge` until MCP write/read round-trips are verified
against the post-fix tag — capturing review findings into Graphiti right
now would land them in the same path being reviewed.
