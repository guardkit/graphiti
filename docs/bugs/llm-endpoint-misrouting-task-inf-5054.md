# Bug: MCP `add_memory` queue worker hits `api.openai.com` instead of configured local endpoint (TASK-INF-5054)

**Status:** RESOLVED in `v0.29.5-guardkit.6` (2026-05-07)
**Severity:** high (blocks all writes to FalkorDB on local-LLM deployments)
**Tag affected:** `v0.29.5-guardkit.5` and earlier (any tag carrying upstream `mcp_server/src/services/factories.py` from before this fix)
**Tag fixed in:** `v0.29.5-guardkit.6`
**Component:** `mcp_server/src/services/factories.py`

## Summary

When the MCP server is configured with `provider: openai` and a custom
`api_url` (e.g. a local llama-swap, vLLM, ollama, openrouter, or
anthropic-via-openai-compat endpoint), `LLMClientFactory.create` for
the `openai` provider:

1. **Drops `base_url` on the floor.** It never reads
   `config.providers.openai.api_url` when constructing
   `graphiti_core.llm_client.config.LLMConfig`, so `OpenAIClient` falls
   back to the openai SDK default (`https://api.openai.com/v1`).
2. **Always returns `OpenAIClient`.** `OpenAIClient`'s
   structured-output path (`_create_structured_completion`) calls
   `client.responses.parse(...)` — the OpenAI Responses API at
   `/v1/responses`, which exists ONLY on OpenAI cloud. Any local
   OpenAI-compatible server returns 404 / 400 / unrecognized-route on
   `/v1/responses`.

Combined: every `add_memory` queues an episode, the queue worker tries
to call `https://api.openai.com/v1/responses` with whatever the local
API key was set to (typically a placeholder like
`not-needed-vllm-local`), gets HTTP 401 ("Incorrect API key
provided"), retries twice, fails, drops the episode. **The
EpisodicNode never lands in FalkorDB.**

## Reproduction

1. Configure `mcp_server` with `provider: openai` and
   `api_url: http://localhost:9000/v1` (or any non-OpenAI endpoint).
2. Set `api_key: not-needed-vllm-local` (placeholder; only OpenAI cloud
   would care).
3. Call MCP `add_memory` with any `group_id` and content.
4. Observe in `docker logs graphiti-mcp`:
   ```
   httpx - INFO - HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 401 Unauthorized"
   graphiti_core.llm_client.openai_base_client - ERROR - OpenAI Authentication Error: Error code: 401 - {'error': {'message': 'Incorrect API key provided: not-need*********ocal. ...'}}
   ...
   services.queue_service - ERROR - Failed to process episode None for group <X>: Error code: 401
   ```
5. Subsequent `get_episodes(group_ids=[X])` returns `[]` — the episode
   was queued but the worker dropped it before persisting.

## Why the embedder factory wasn't affected

Asymmetry. The embedder factory at
`EmbedderFactory.create` (same file) has always passed `base_url`:

```python
embedder_config = OpenAIEmbedderConfig(
    api_key=api_key,
    embedding_model=config.model,
    base_url=config.providers.openai.api_url,  # Support custom endpoints like Ollama
    embedding_dim=config.dimensions,
)
```

The LLM factory's missing `base_url` was a pre-existing oversight that
became visible only when paired with a local LLM endpoint and the
Responses-API-only `OpenAIClient` codepath.

## Root cause

`mcp_server/src/services/factories.py` `LLMClientFactory.create`
`'openai'` case:

```python
# pre-fix
llm_config = CoreLLMConfig(
    api_key=api_key,
    model=config.model,
    small_model=small_model,
    temperature=config.temperature,
    max_tokens=config.max_tokens,
    # ← no base_url
)
...
return OpenAIClient(config=llm_config, ...)
```

And in `graphiti_core/llm_client/openai_client.py:99`:

```python
response = await self.client.responses.parse(**request_kwargs)
```

`responses.parse` is the OpenAI Responses API, OpenAI-cloud only. The
older `chat.completions.create` path is what every OpenAI-compatible
server speaks.

## Fix

Two coordinated changes in `mcp_server/src/services/factories.py`
(commit `c8b5a65`):

### 1. Pass `base_url` to `LLMConfig`

```python
api_url = config.providers.openai.api_url
...
llm_config = CoreLLMConfig(
    api_key=api_key,
    base_url=api_url,
    model=config.model,
    small_model=small_model,
    temperature=config.temperature,
    max_tokens=config.max_tokens,
)
```

### 2. Auto-pick the right client for the endpoint

```python
is_openai_cloud = (
    not api_url
    or api_url.startswith('https://api.openai.com')
)

if not is_openai_cloud:
    logger.info(
        f'OpenAI-compatible endpoint detected (api_url={api_url}); '
        f'using OpenAIGenericClient (chat.completions + json_schema). '
        f'OpenAIClient (Responses API) is reserved for openai.com.'
    )
    return OpenAIGenericClient(config=llm_config)

# OpenAI cloud path: keep OpenAIClient + Responses API + reasoning model wiring
...
```

`OpenAIGenericClient` (in `graphiti_core/llm_client/openai_generic_client.py`)
uses `chat.completions.create` with `response_format =
{'type': 'json_schema', 'json_schema': {...}}`, which works against any
modern OpenAI-compatible server. It also honours `base_url` correctly
on its own (line 91).

The OpenAI cloud path is unchanged: it continues to use `OpenAIClient`
with the full reasoning-model wiring (`reasoning='minimal'`,
`verbosity='low'` for the gpt-5 / o1 / o3 family).

## Verification

End-to-end on `promaxgb10-41b1` (2026-05-07) with llama-swap on
`localhost:9000`:

- Factory startup log:
  ```
  services.factories - INFO - OpenAI-compatible endpoint detected
    (api_url=http://localhost:9000/v1); using OpenAIGenericClient
    (chat.completions + json_schema). OpenAIClient (Responses API)
    is reserved for openai.com.
  ```
- MCP `add_memory` → queue worker calls
  `POST http://localhost:9000/v1/chat/completions` (HTTP 200, ~43s for
  entity + edge extraction at local-model latency).
- MCP `get_episodes` returns the persisted episode (uuid `e54f1cef`,
  name `'TASK-INF-5054 round-trip smoke'`).
- Zero `api.openai.com` references in post-fix logs.
- No regression on the `get_episodes` routing fix
  (`v0.29.5-guardkit.5`): single-group + multi-group reads still PASS.

GuardKit runbook: `docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md`
Phase 8.1b is the operator-facing smoke test for this fix.

## Notes for future work

- The `groq` provider case (same file) was not audited as part of this
  fix. Groq's `/v1/chat/completions` is mature; their Responses-API
  support (if any) was not investigated. If anyone hits a similar
  symptom on `provider: groq`, check the same `responses.parse`
  question.
- The heuristic `api_url.startswith('https://api.openai.com')` is
  intentionally narrow. If OpenAI ever introduces a new cloud hostname
  (e.g. `api.openai-eu.com`), it will be misclassified as a local
  endpoint and routed through `OpenAIGenericClient`, which still works
  but loses the Responses-API + reasoning-model param wiring. Worth
  revisiting then.

## References

- Fix commit: `c8b5a65`
- Tag: `v0.29.5-guardkit.6`
- Companion fix (read path): [`get-episodes-mcp-empty-results.md`](./get-episodes-mcp-empty-results.md) (`v0.29.5-guardkit.5`)
- GuardKit retrospective: `guardkit/docs/fixes/2026-05-07-graphiti-mcp-falkordb-end-to-end.md`
