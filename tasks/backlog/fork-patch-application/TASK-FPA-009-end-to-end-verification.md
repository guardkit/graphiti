---
id: TASK-FPA-009
title: End-to-end verification (seed run, MCP probes, container logs) per AC-FORK-08
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 4
estimated_minutes: 60
execution_location: promaxgb10-41b1
tags: [graphiti, fork, verification, e2e, mcp]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 4
implementation_mode: direct
dependencies: [TASK-FPA-007]
workspace_name: fork-patch-application-wave4-2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# End-to-end verification (AC-FORK-08)

**WHY**: All preceding subtasks confirm individual patches apply and don't break unit tests. AC-FORK-08 requires a full smoke test: study-tutor seed runs 25/25, verify_lilymay.py shows populated state, MCP write+read probes succeed (including dashed group_id), container logs show LLM calls hit `localhost:9000` (not `api.openai.com`).

**WHAT**: Run the verification protocol from TASK-FORK-PATCH §"Mechanical plan" Step 9 against the freshly-built fork-pinned consumer venvs and rebuilt MCP container.

**SCOPE NOTE**: This task assumes the consumer-side updates (study-tutor pyproject pin, guardkit pyproject pin, `graphiti-mcp-build.sh` updates, MCP container rebuild) have been completed in their respective repos (see "Cross-repo follow-ups" below). If those haven't landed yet, this task is **BLOCKED** and should be moved to `tasks/blocked/`.

## Prerequisites (in OTHER repos)

These are NOT subtasks of this graphiti fork-patch feature — they live in their own repos' task systems. File them there before starting this verification:

1. **study-tutor**: update `pyproject.toml` to pin `graphiti-core @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1#subdirectory=graphiti_core`. Refresh venv via `uv sync`.
2. **guardkit**: update `pyproject.toml` to pin the same. Update `guardkit/scripts/graphiti-mcp-build.sh` to clone fork at the tag (replace `git clone https://github.com/getzep/graphiti.git` with `git clone --branch v0.29.5-guardkit.1 https://github.com/guardkit/graphiti.git`). Add `MCP_SERVER_HOST=0.0.0.0` env export to `guardkit/scripts/graphiti-mcp.sh` (paired with bootstrap-shim retirement decision).
3. **jarvis**: update `pyproject.toml` to pin the same.
4. **MCP container rebuild**: run `./scripts/graphiti-mcp-build.sh --no-cache` then `./scripts/graphiti-mcp.sh` to restart the container at `http://promaxgb10-41b1:8004/mcp`.

## Verification steps

```bash
# 1. study-tutor seed (expect 25/25 succeeded_writes)
cd ~/Projects/appmilla_github/study-tutor
.venv/bin/python scripts/seed_student_model.py 2>&1 | tee /tmp/verify-seed.log
grep "succeeded_writes" /tmp/verify-seed.log     # expect: succeeded_writes=25

# 2. verify_lilymay.py (expect populated state)
.venv/bin/python .guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py 2>&1 | tee /tmp/verify-lilymay.log
# Expect: ac_seed_03_get_student_state populated (year_group=11, target_grade='8',
# non-empty subjects, non-empty topic_confidences). Non-empty
# ac_seed_02_student_lilymay_nodes.

# 3. MCP write probe
mcp__graphiti__add_memory(
  name="fork-verify",
  episode_body="guardkit fork v0.29.5-guardkit.1 verification probe — 2026-05-04",
  group_id="guardkit__test_fork",
  source="text"
)
# Wait ~10s for ingestion
sleep 10
mcp__graphiti__get_episodes(group_ids=["guardkit__test_fork"])
# Expect: episode retrievable.

# 4. MCP read probe with dashed group_id (R-WAVE5-03 fix verification)
mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])
# Expect: populated Student entity. NO RediSearch syntax error (the dash is no
# longer interpreted as NOT — patches 001 + 004 working together).

# 5. Container logs — confirm LLM calls hit localhost:9000
docker logs graphiti-mcp 2>&1 | grep -E "Using OpenAIGenericClient|api.openai.com|localhost:9000" | head -20
# Expect: "Using OpenAIGenericClient for non-OpenAI endpoint: http://localhost:9000/v1"
# (auto-detect log line on first LLM call). Should see ZERO references to api.openai.com.
```

## Acceptance Criteria

- [ ] **AC-FORK-08-1**: `seed_student_model.py` reports `succeeded_writes=25` (25 of 25).
- [ ] **AC-FORK-08-2**: `verify_lilymay.py` shows populated `ac_seed_03_get_student_state` and non-empty `ac_seed_02_student_lilymay_nodes`.
- [ ] **AC-FORK-08-3**: MCP write probe round-trips (`add_memory` → `get_episodes` returns the just-written episode).
- [ ] **AC-FORK-08-4**: MCP read probe with `group_ids=["student-lilymay"]` returns populated Student entity with NO RediSearch syntax error.
- [ ] **AC-FORK-08-5**: `docker logs graphiti-mcp` shows the auto-detect log line on first LLM call. Zero `api.openai.com` references in the log window covering the verification window.
- [ ] **AC-FORK-19 final diff**: post-final-commit (post-005, post-tag) baseline diff for graphiti-core / mcp_server / guardkit workaround suites shows no new failures versus the TASK-FPA-001 baselines. New passes are accepted.

## Post-verification flips (per AC-FORK-09)

If all AC-FORK-08 sub-criteria pass, also action:

- [ ] Flip G2 and G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` from "Falsified" to "Held" with evidence excerpts (per AC-SEED-05's exact format).
- [ ] Move `study-tutor/tasks/blocked/TASK-GR-SEED-...md` to `study-tutor/tasks/in_review/` (or `completed/` if the verification window is sufficient).
- [ ] Move `guardkit/tasks/backlog/TASK-INF-5054-...md` to `guardkit/tasks/completed/2026-05/`.
- [ ] Move parent task `TASK-FORK-PATCH` from `backlog/` to `completed/`.

These flips are documentation/state-change actions — they belong to this verification subtask because they're the "all green, mark everything done" closeout.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Mechanical plan" Step 9-10; AC-FORK-08, AC-FORK-09, AC-FORK-19.
- Review report: [TASK-FORK-PATCH-review-report.md](../../../.claude/reviews/TASK-FORK-PATCH-review-report.md) §"Verifications performed during this review".
- Cross-repo: study-tutor TASK-GR-SEED, guardkit TASK-INF-5054.
