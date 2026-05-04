---
id: TASK-FPA-008
title: Write FORK-NOTES.md at fork repo root documenting patches and rationale
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T15:45:00+01:00
completed: 2026-05-04T15:45:00+01:00
previous_state: in_review
completed_location: tasks/completed/fork-patch-application/
priority: medium
task_type: docs
complexity: 2
estimated_minutes: 30
execution_location: promaxgb10-41b1
tags: [graphiti, fork, docs]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 4
implementation_mode: direct
dependencies: [TASK-FPA-007]
workspace_name: fork-patch-application-wave4-1
patch_commit: e0f92a3
test_results:
  status: not_applicable
  coverage: null
  last_run: 2026-05-04T15:30:00+01:00
  notes: docs-only task — no automated tests; AC compliance verified by content review
---

# Write FORK-NOTES.md

**WHY**: AC-FORK-05 requires a discoverable "what's patched and why" document at the fork repo root. Future readers (including anyone updating the fork against new upstream releases) need a single source of truth for the patch inventory and the rationale behind each.

**WHAT**: Create `FORK-NOTES.md` at the fork repo root summarising:

1. What graphiti version this is forked from (0.29.0, commit `56cf7b3`).
2. The five drafted patches (001-005) plus the factories.py auto-detect (in-flight diff origin, applied as commit 2).
3. The six locked decisions from TASK-FORK-PATCH.
4. Cross-references to study-tutor TASK-GR-SEED, guardkit TASK-INF-5054, TASK-INF-5053, TASK-REV-661E, TASK-REV-84A7.
5. **Explicit semantic-change callouts** (per addendum):
   - `edge_bfs_search` no longer double-counts edges with swapped source/target (latent bug fix, may surprise consumers).
   - `build_fulltext_query` returns `*` for empty post-stopword queries (was a crash).
6. **Distinction between bug #4 (colon-rejection, fixed upstream in 0.29.0) and bug #5 (dash-tokenisation, fixed in this fork)** — recommendation #5 from the parent review report.
7. Maintenance plan: how to merge new upstream releases, how to re-cut tags, when to consider proposing fixes upstream.

## Suggested structure

```markdown
# guardkit fork — FORK-NOTES.md

## What this fork is

This is a fork of [getzep/graphiti](https://github.com/getzep/graphiti) at version 0.29.0
(commit 56cf7b3) with bug-fix patches applied for the guardkit deployment stack
(study-tutor, guardkit, jarvis). Maintained by guardkit; cuts release tags as
`vX.Y.Z-guardkit.N`.

## Patches in this fork

[Table of patches 001-005 + factories.py with bug coverage and commit SHAs.]

## Locked decisions (from TASK-FORK-PATCH)

[Six decisions with rationale.]

## Important semantic changes

[Two explicit callouts: edge_bfs_search dedup, build_fulltext_query * wildcard.]

## Bug-numbering note

bug #4 (colon-rejection) was fixed upstream in 0.29.0 — i.e. before this fork was
cut. Don't conflate it with bug #5 (dash-tokenisation), which is fixed here.

## Cross-references

- study-tutor TASK-GR-SEED — surfaced bugs #5/#11/#12 (R-WAVE5-03)
- guardkit TASK-INF-5054 — full spec for bugs #6/#7
- guardkit TASK-INF-5053 — surfaced the responses.parse / base_url ignore bugs
- guardkit TASK-REV-661E — surfaced bug #10 (sanitize gaps)
- guardkit TASK-REV-84A7 — llm_max_tokens cap rationale (separate, not patched here)
- guardkit/knowledge/falkordb_workaround.py — runtime monkey-patch that this fork makes redundant for bugs #8, #9, #5/#11, #10

## Maintenance plan

[Quarterly upstream merge cadence; how to handle conflicts; when to propose
fixes upstream once they're stable here.]
```

## Steps

1. Draft `FORK-NOTES.md` per the structure above.
2. Commit on `guardkit-fixes-0.29` with message `docs: add FORK-NOTES.md (TASK-FORK-PATCH AC-FORK-05)`.
3. Do NOT push a new tag for this — FORK-NOTES.md is documentation that can land post-tag. (Optional: if a GitHub Release was created at TASK-FPA-007, copy the FORK-NOTES.md content into the release body.)

## Acceptance Criteria

- [ ] `FORK-NOTES.md` exists at the fork repo root.
- [ ] Content covers: forked-from version + commit, patch inventory with bug IDs, locked decisions, semantic changes, bug-#4-vs-#5 distinction, cross-references, maintenance plan.
- [ ] Committed on `guardkit-fixes-0.29` and pushed to the origin remote.
- [ ] No code changes in the same commit (docs-only).

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Acceptance Criteria" AC-FORK-05; recommendations #5 + §"Notes" §"Maintenance discipline".
- Review report: [TASK-FORK-PATCH-review-report.md](../../../.claude/reviews/TASK-FORK-PATCH-review-report.md) §"Recommendations beyond the six decisions" #5.
