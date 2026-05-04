---
id: TASK-FPA-004
title: Apply factories.py auto-detect (bug #6/#7) as commit 2 — derive from graphiti-original in-flight diff
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 5
estimated_minutes: 60
execution_location: promaxgb10-41b1
tags: [graphiti, fork, factories, openai-generic, mcp]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 2
implementation_mode: task-work
dependencies: [TASK-FPA-003]
workspace_name: fork-patch-application-wave2-2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Apply factories.py auto-detect (bug #6/#7)

**WHY**: Decision 6 is locked to **Approach A — auto-detect on `base_url`** (zero consumer-config-schema churn; established pattern per knowledge graph). The patch shape is **fully specified** in the parent task at `TASK-FORK-PATCH §"Diff: mcp_server/src/services/factories.py"` (lines 206-241): `+14/-0` lines, no conflict with this fork's two extra commits (`164030f`, `56cf7b3`).

**WHAT**: Apply the diff to the fork's `factories.py`, verify it compiles, commit as commit 2, and re-run the baseline diff.

## Important: where the diff lives

The parent task originally referred to "staged-but-unpushed changes" in `~/Projects/appmilla_github/graphiti-original/`. **Those staged changes are on the Macbook**, not on the GB10. On the GB10 today (verified 2026-05-04), `~/Projects/appmilla_github/graphiti-original/` has a clean working tree with no staged changes and no `OpenAIGenericClient` import in `factories.py`.

**Two execution paths**:

- **Path A — sync from Macbook**: on the Mac, run `cd ~/Projects/appmilla_github/graphiti-original && git diff > /tmp/factories-autodetect.diff` and `cd ~/Projects/appmilla_github/graphiti-original && git diff --cached >> /tmp/factories-autodetect.diff` (combine working-tree + staged) and `scp /tmp/factories-autodetect.diff promaxgb10-41b1:/tmp/`. Then on the GB10 use that file as the patch source.

- **Path B — derive from the parent task spec**: the full +14/-0 diff is reproduced verbatim at TASK-FORK-PATCH lines 206-241. Save it as `patches/006-factories-auto-detect.patch` and apply it like the other five patches. This avoids the Mac round-trip and produces a patch file consistent with the rest of `patches/`. Recommended.

The recommended path (B) is captured in the steps below.

## Bugs covered

- **#6**: graphiti-mcp `factories.py` `openai` branch silently ignores `api_url` → falls through to api.openai.com.
- **#7**: `OpenAIClient` calls `responses.parse()` instead of `chat.completions.create` → 404 against local OpenAI-compatible servers like vLLM/llama-swap.

## Steps (Path B — recommended)

**Pre-requisite**: `patches/006-factories-auto-detect.patch` exists at the fork repo root. If it doesn't exist yet, draft it first by transcribing the diff at TASK-FORK-PATCH lines 206-241 verbatim into a unified diff with the same `--- a/...`/`+++ b/...` header style used by patches 001-005. Verify with `git apply --check patches/006-factories-auto-detect.patch`.

```bash
# 1. Pre-apply check
cd ~/Projects/appmilla_github/graphiti
git checkout guardkit-fixes-0.29
git apply --check patches/006-factories-auto-detect.patch

# 2. Apply
git apply patches/006-factories-auto-detect.patch

# 3. Quick sanity-check: import factories.py to confirm it parses
.venv/bin/python -c "from mcp_server.src.services import factories; print('factories.py imports OK')"

# 4. Stage and commit
git add mcp_server/src/services/factories.py
git commit -m "fix(factories): auto-detect non-OpenAI endpoints, route to OpenAIGenericClient

When provider='openai' but api_url points at a non-api.openai.com host
(e.g. vLLM/llama-swap on localhost:9000), pass the base_url through to
LLMConfig and route to OpenAIGenericClient (Chat Completions) rather
than OpenAIClient (Responses API, which vLLM doesn't support). Default
behaviour for genuine OpenAI endpoints is preserved.

Refs: TASK-FORK-PATCH bugs #6/#7; guardkit TASK-INF-5054;
graphiti knowledge-graph fact 2026-04-03 'graphiti MCP server factory
uses OpenAIGenericClient for non-OpenAI endpoints'."

# 5. Baseline diff (AC-FORK-19)
SHA=$(git rev-parse --short HEAD)
.venv/bin/pytest mcp_server/tests/ --tb=line 2>&1 | tee /tmp/post-${SHA}-mcp.txt
diff /tmp/baseline-mcp.txt /tmp/post-${SHA}-mcp.txt || echo "DIFF FOUND — investigate"
```

## Notes on `config-local-neo4j.yaml` and `config-guardkit.yaml`

The parent task originally proposed adding two YAML files alongside the factories.py diff (per AC-FORK-16). On the GB10 those files don't exist in `graphiti-original/mcp_server/config/`. **Defer both YAML additions to a follow-up task** — they're orthogonal to the factories.py fix and the verification path uses the live config at `guardkit/scripts/graphiti-mcp-config.yaml` which is already correct.

If you do want the example template, the `config-local-neo4j.yaml` would need to be authored fresh from the upstream `mcp_server/config/config-docker-neo4j.yaml` template with secrets stripped. This is **out of scope** for TASK-FPA-004; file as `TASK-FPA-CFGEX` if desired.

The stale `config-guardkit.yaml` (Gemini-era, dead `:8001` embedder, wrong 1024-dim per parent task lines 259-322) must **never** be committed.

## Acceptance Criteria

- [ ] `patches/006-factories-auto-detect.patch` exists, transcribed verbatim from TASK-FORK-PATCH lines 206-241.
- [ ] `git apply --check patches/006-factories-auto-detect.patch` passes.
- [ ] Patch landed as a single commit on `guardkit-fixes-0.29`.
- [ ] `factories.py` change is exactly the auto-detect form (Approach A): `base_url = config.providers.openai.api_url`, `is_openai_endpoint = base_url is None or 'api.openai.com' in base_url`, route to `OpenAIGenericClient` if not.
- [ ] `python -c "from mcp_server.src.services import factories"` returns 0.
- [ ] Baseline diff for `mcp` suite shows no new failures.

## Cross-references

- Parent: [TASK-FORK-PATCH](../TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) §"Decisions" 6, §"In-flight patch already drafted", §"Mechanical plan" Step 2 commit 2; AC-FORK-03, AC-FORK-15, AC-FORK-16, AC-FORK-17, AC-FORK-19.
- Addendum: [TASK-FORK-PATCH-review-addendum-execution-flow.md](../../../.claude/reviews/TASK-FORK-PATCH-review-addendum-execution-flow.md) §"Diagrams 12-13".

## Regression risk (from addendum Diagram 13)

| Configuration | Pre-patch | Post-patch | Regression? |
|---------------|-----------|------------|-------------|
| `provider: openai`, `api_url: api.openai.com` | Works | Works (auto-detect keeps OpenAIClient) | None |
| `provider: openai`, `api_url: null` | Works | Works (None → keeps OpenAIClient) | None |
| `provider: openai`, `api_url: localhost:9000` | **Broken** (401) | Works (Chat Completions) | None — this is the fix |
| `provider: openai`, `api_url: my-azure-proxy/openai/v1` | Works only if proxy supports Responses API | Routes to Chat Completions (graphiti-core uses Chat Completions semantics anyway) | Theoretical only — benign for graphiti-core's structured-output use case |

## Notes

- This is the only `task-work` mode subtask in Wave 2 because cherry-picking from a separate clone with manual conflict resolution may need it. If the apply is clean, downgrade to `direct` mode in practice.
- Smoke test deferred to TASK-FPA-009 (end-to-end verification needs the MCP container rebuild).
