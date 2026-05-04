---
id: TASK-FPA-004
title: Apply factories.py auto-detect (bug #6/#7) as commit 2 — derive from graphiti-official in-flight diff
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

**WHY**: Decision 6 is locked to **Approach A — auto-detect on `base_url`** (zero consumer-config-schema churn; established pattern per knowledge graph). The patch is **already drafted** as staged-but-unpushed changes at `~/Projects/appmilla_github/graphiti-official/mcp_server/src/services/factories.py` against upstream commit `9cdcc93`. Per the parent task's "In-flight patch already drafted" section, the diff is +14/-0 lines and has no conflict with this fork's two extra commits (`164030f`, `56cf7b3`).

**WHAT**: Cherry-pick the staged diff from `graphiti-official` onto current `appmilla-fixes-0.29`, verify it still compiles, commit as commit 2, and re-run the baseline diff.

## Bugs covered

- **#6**: graphiti-mcp `factories.py` `openai` branch silently ignores `api_url` → falls through to api.openai.com.
- **#7**: `OpenAIClient` calls `responses.parse()` instead of `chat.completions.create` → 404 against local OpenAI-compatible servers like vLLM/llama-swap.

## Steps

```bash
# 1. Capture the staged diff from the upstream-tracker clone
cd ~/Projects/appmilla_github/graphiti-official
git status                                       # expect: staged changes on factories.py + two new YAMLs
git diff --cached mcp_server/src/services/factories.py > /tmp/factories-autodetect.diff
cat /tmp/factories-autodetect.diff               # eyeball: should be +14/-0

# 2. Apply to the fork
cd ~/Projects/appmilla_github/graphiti
git checkout appmilla-fixes-0.29
git apply --check /tmp/factories-autodetect.diff || echo "Conflict — manually port instead"
git apply /tmp/factories-autodetect.diff

# 3. ALSO commit the generic config-local-neo4j.yaml from the staged set
#    (per AC-FORK-16; the staged config-guardkit.yaml is STALE and must NOT be committed)
cp ~/Projects/appmilla_github/graphiti-official/mcp_server/config/config-local-neo4j.yaml \
   mcp_server/config/config-local-neo4j.yaml
# DO NOT copy mcp_server/config/config-guardkit.yaml — it's a Gemini-era stale snapshot
# with dead :8001 embedder and wrong 1024-dim. See parent task lines 259-322.

# 4. Quick sanity-check: import factories.py to confirm it parses
.venv/bin/python -c "from mcp_server.src.services import factories; print('factories.py imports OK')"

# 5. Stage and commit
git add mcp_server/src/services/factories.py mcp_server/config/config-local-neo4j.yaml
git commit -m "fix(factories): auto-detect non-OpenAI endpoints, route to OpenAIGenericClient

When provider='openai' but api_url points at a non-api.openai.com host
(e.g. vLLM/llama-swap on localhost:9000), pass the base_url through to
LLMConfig and route to OpenAIGenericClient (Chat Completions) rather
than OpenAIClient (Responses API, which vLLM doesn't support). Default
behaviour for genuine OpenAI endpoints is preserved.

Also adds mcp_server/config/config-local-neo4j.yaml as a clean generic
Docker-compose-with-Neo4j example template.

Refs: TASK-FORK-PATCH bugs #6/#7; guardkit TASK-INF-5054;
graphiti knowledge-graph fact 2026-04-03 'graphiti MCP server factory
uses OpenAIGenericClient for non-OpenAI endpoints'."

# 6. Baseline diff (AC-FORK-19)
SHA=$(git rev-parse --short HEAD)
.venv/bin/pytest mcp_server/tests/ --tb=line 2>&1 | tee /tmp/post-${SHA}-mcp.txt
diff /tmp/baseline-mcp.txt /tmp/post-${SHA}-mcp.txt || echo "DIFF FOUND — investigate"
```

## Acceptance Criteria

- [ ] Staged diff from `graphiti-official` cherry-picked onto `appmilla-fixes-0.29` cleanly. If conflict: manually port the +14 lines per the diff in TASK-FORK-PATCH "In-flight patch already drafted" section.
- [ ] `factories.py` change is exactly the auto-detect form (Approach A): `base_url = config.providers.openai.api_url`, `is_openai_endpoint = base_url is None or 'api.openai.com' in base_url`, route to `OpenAIGenericClient` if not.
- [ ] `mcp_server/config/config-local-neo4j.yaml` committed (clean generic template).
- [ ] **`mcp_server/config/config-guardkit.yaml` is NOT committed** (stale Gemini-era foot-gun per parent task §"`mcp_server/config/config-guardkit.yaml` — staged file is **stale**, do NOT use").
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
