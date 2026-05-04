---
id: TASK-FPA-004
title: Apply factories.py auto-detect (bug #6/#7) as commit 2 — derive from graphiti-original in-flight diff
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 2
estimated_minutes: 20
execution_location: promaxgb10-41b1
tags: [graphiti, fork, factories, openai-generic, mcp]
parent_review: TASK-FORK-PATCH
feature_id: FEAT-FPA-2026-05
wave: 2
implementation_mode: direct
dependencies: [TASK-FPA-003]
workspace_name: fork-patch-application-wave2-2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Apply factories.py auto-detect (bug #6/#7)

**WHY**: Decision 6 is locked to **Approach A — auto-detect on `base_url`** (zero consumer-config-schema churn; established pattern per knowledge graph). The patch is now **drafted as a clean unified diff** at [`patches/006-factories-auto-detect.patch`](../../../patches/006-factories-auto-detect.patch), captured 2026-05-04 from the original Macbook in-flight diff via `rsync` over Tailscale.

**WHAT**: Apply [`patches/006-factories-auto-detect.patch`](../../../patches/006-factories-auto-detect.patch) on top of commit 1 (RediSearch + sanitize + MCP host), verify it compiles, commit as commit 2, and re-run the baseline diff.

## What's in patch 006

- `mcp_server/src/services/factories.py`: +14 lines auto-detect (Approach A — pass `base_url` from `config.providers.openai.api_url` into `LLMConfig`, route to `OpenAIGenericClient` when `base_url` doesn't contain `api.openai.com`).
- `mcp_server/config/config-local-neo4j.yaml`: +103 lines clean generic Docker-compose-with-Neo4j example template (per AC-FORK-16).

`mcp_server/config/config-guardkit.yaml` from the same Mac in-flight set is **deliberately not included** — it's a stale Gemini-era snapshot with dead `:8001` embedder and wrong 1024-dim per parent task lines 259-322.

## Bugs covered

- **#6**: graphiti-mcp `factories.py` `openai` branch silently ignores `api_url` → falls through to api.openai.com.
- **#7**: `OpenAIClient` calls `responses.parse()` instead of `chat.completions.create` → 404 against local OpenAI-compatible servers like vLLM/llama-swap.

## Steps

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
git add mcp_server/src/services/factories.py mcp_server/config/config-local-neo4j.yaml
git commit -m "fix(factories): auto-detect non-OpenAI endpoints, route to OpenAIGenericClient

When provider='openai' but api_url points at a non-api.openai.com host
(e.g. vLLM/llama-swap on localhost:9000), pass the base_url through to
LLMConfig and route to OpenAIGenericClient (Chat Completions) rather
than OpenAIClient (Responses API, which vLLM doesn't support). Default
behaviour for genuine OpenAI endpoints is preserved.

Also adds mcp_server/config/config-local-neo4j.yaml as a clean generic
Docker-compose-with-Neo4j example template (per AC-FORK-16).

Refs: TASK-FORK-PATCH bugs #6/#7; guardkit TASK-INF-5054;
graphiti knowledge-graph fact 2026-04-03 'graphiti MCP server factory
uses OpenAIGenericClient for non-OpenAI endpoints'."

# 5. Baseline diff (AC-FORK-19)
SHA=$(git rev-parse --short HEAD)
.venv/bin/pytest mcp_server/tests/ --tb=line 2>&1 | tee /tmp/post-${SHA}-mcp.txt
diff /tmp/baseline-mcp.txt /tmp/post-${SHA}-mcp.txt || echo "DIFF FOUND — investigate"
```

## Acceptance Criteria

- [ ] `git apply --check patches/006-factories-auto-detect.patch` passes (already verified 2026-05-04 against `d0913fe`).
- [ ] Patch landed as a single commit on `guardkit-fixes-0.29`.
- [ ] `factories.py` change is exactly the auto-detect form (Approach A): `base_url = config.providers.openai.api_url`, `is_openai_endpoint = base_url is None or 'api.openai.com' in base_url`, route to `OpenAIGenericClient` if not.
- [ ] `mcp_server/config/config-local-neo4j.yaml` is present in the working tree after apply (clean generic template — env-var placeholders, no secrets, no GB10-specific values).
- [ ] **`mcp_server/config/config-guardkit.yaml` is NOT in the working tree** (deliberately excluded from the patch — stale Gemini-era foot-gun per parent task §"`mcp_server/config/config-guardkit.yaml` — staged file is **stale**, do NOT use").
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

- Patch was captured 2026-05-04 from the original Macbook in-flight diff via `rsync` over Tailscale (graphiti-original synced from Mac → GB10), then sliced to extract just the factories.py change + the clean generic config-local-neo4j.yaml. The stale config-guardkit.yaml from the same Mac state was deliberately excluded.
- Smoke test deferred to TASK-FPA-009 (end-to-end verification needs the MCP container rebuild).
