---
id: TASK-FPA-007
title: Tag v0.29.5-guardkit.1 and push tag to fork remote
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T14:00:00+01:00
completed: 2026-05-04T14:00:00+01:00
previous_state: backlog
completed_location: tasks/completed/fork-patch-application/
priority: high
task_type: feature
complexity: 1
estimated_minutes: 15
execution_location: promaxgb10-41b1
tags: [graphiti, fork, release, tag]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 3
implementation_mode: manual
dependencies: [TASK-FPA-006]
workspace_name: fork-patch-application-wave3-1
tag_name: v0.29.5-guardkit.1
tag_object_sha: bc48a6e578616cce29a0bdaab0cb25cdad28b0a8
tag_target_commit: 8a8174713f5958320515b80fea8ebdcbaf36b3cb
verification:
  status: passed
  api_check: "gh api repos/guardkit/graphiti/git/refs/tags/v0.29.5-guardkit.1 -> 200, type=tag, sha=bc48a6e..."
  pip_install_check: deferred_to_TASK-FPA-009
  last_run: 2026-05-04T14:00:00+01:00
---

# Tag v0.29.5-guardkit.1 and push tag

**WHY**: Decision 4 is locked to **tag-and-pin**. After all four patch-application commits land cleanly on `guardkit-fixes-0.29`, cut a release tag so consumer pyprojects can pin reproducibly.

**WHAT**: Create an annotated tag, push it to the `origin` remote, and verify it's visible from the GitHub web UI / `gh release list`.

## Steps

```bash
cd ~/Projects/appmilla_github/graphiti
git checkout guardkit-fixes-0.29
git log --oneline -8                              # confirm last 4-5 commits are the patch applications

# Annotated tag with summary message (use HEREDOC for multiline)
git tag -a v0.29.5-guardkit.1 -m "$(cat <<'EOF'
guardkit fork release: graphiti-core 0.29.0 + guardkit bug fixes 1-13

Forked from getzep/graphiti at version 0.29.0 (commit 56cf7b3). Includes:

- bug #5 + #11 + #12: drop @group_id fulltext filter on FalkorDB
  (RediSearch dash-as-NOT bug); return * for empty post-stopword queries
- bug #10: strip backtick in sanitize() (slashes/pipes/backslashes
  already in upstream's strip list as of 0.29.0)
- bug #13: bind FastMCP host at construction time so transport_security
  freezes against the right allow-list (MCP_SERVER_HOST env var)
- bug #6 + #7: factories.py auto-detects non-OpenAI endpoints and
  routes to OpenAIGenericClient (Chat Completions API) — fixes silent
  401s against vLLM/llama-swap and other OpenAI-compatible servers
- bug #8: handle_multiple_group_ids decorator now takes the per-group
  driver-clone path for single-group calls (mirrors upstream PR #1170)
- bug #9: edge_fulltext_search and edge_bfs_search use startNode/endNode
  for O(n) endpoint access instead of O(n×m) re-MATCH (mirrors upstream
  issue #1272)

See FORK-NOTES.md for full audit and rationale.
EOF
)"

# Push tag
git push origin v0.29.5-guardkit.1

# Verify
gh release list --repo guardkit/graphiti        # tag should appear (release optional)
gh api repos/guardkit/graphiti/git/refs/tags/v0.29.5-guardkit.1
```

## Acceptance Criteria

- [ ] Annotated tag `v0.29.5-guardkit.1` created locally on the tip of `guardkit-fixes-0.29`.
- [ ] Tag pushed to `origin` remote.
- [ ] `gh api repos/guardkit/graphiti/git/refs/tags/v0.29.5-guardkit.1` returns 200 with the tag's commit SHA.
- [ ] Tag is reachable from `pip install git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1` (verified by a scratch venv install — defer to TASK-FPA-009).

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Decisions" 4, §"Mechanical plan" Step 4; AC-FORK-04.

## Notes

- A GitHub Release (with formatted release notes) is **optional**. The tag is what consumers pin against; the release page is documentation. If creating one: paste FORK-NOTES.md content into the release body when it exists (i.e. after TASK-FPA-008 lands).
- Subsequent guardkit-fork releases bump the suffix: `v0.29.5-guardkit.2`, etc. Re-base from upstream getzep/graphiti tags as they ship.
