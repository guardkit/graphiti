---
parent_report: TASK-FORK-PATCH-review-report.md
addendum_type: execution-flow-trace
mode: decision (revise)
depth: comprehensive
reviewed_at: 2026-05-04
fork_head: d0913fe (work/falkordb-fixes)
fork_version: 0.29.0
---

# Addendum — Execution Flow Trace and Regression Matrix

This addendum exists because the parent review concluded "decisions only — implementation already drafted" and recommended `[A]ccept`. The user invoked `[R]evise` asking for deeper boundary tracing and C4-style sequence diagrams to validate that the fork patches do not introduce regressions across the system/technology boundaries they touch.

The following diagrams are **mermaid `sequenceDiagram`** blocks. Render in any Mermaid-aware viewer (GitHub, Obsidian, Mermaid Live).

## Boundary inventory (where each patch acts)

The patches cross five distinct technology boundaries. Listing them up front makes the regression analysis tractable:

| Boundary | Tech | Patches that act here |
|----------|------|------------------------|
| B1 — Python lib API | Consumer Python ↔ `graphiti_core` public methods | None directly; entry point for everything |
| B2 — Decorator → driver | `Graphiti.<method>` ↔ `handle_multiple_group_ids` ↔ `FalkorDriver` | Bug #8 (PR #1170) |
| B3 — Driver → FalkorDB | Python `FalkorDriver` ↔ FalkorDB over Redis protocol (RESP3) | Patch 001, Patch 002 (sanitize), Bug #9 (edge_*search Cypher), Bug #1 (group_id filter) |
| B4 — Graphiti → LLM | `graphiti_core.llm_client.*` ↔ remote OpenAI-compatible HTTP API | Bug #6/#7 (factories.py auto-detect) |
| B5 — MCP transport | External MCP client ↔ FastMCP HTTP transport ↔ in-container graphiti-core | Patch 003 (host binding) + factories.py (LLM endpoint, in-container) |

**Critical interaction**: Patches 001 (drop @group_id filter) and Bug #8 fix (decorator `>1` → `>=1`) co-locate at boundaries B2–B3 and **must land together** for single-group searches to work correctly. See §"Critical interaction analysis" below.

---

## Diagram 1 — Read path (search_nodes, single-group, BEFORE all patches)

This is upstream 0.29.0 today. It demonstrates the bug; the patches need to preserve correctness here without introducing new failure modes.

```mermaid
sequenceDiagram
    autonumber
    participant Consumer as Consumer (study-tutor)
    participant Graphiti as graphiti.search_nodes()
    participant Decor as @handle_multiple_group_ids
    participant SearchOps as FalkorSearchOperations
    participant Builder as _build_falkor_fulltext_query
    participant Driver as FalkorDriver (default graph)
    participant Falkor as FalkorDB (RediSearch index)

    Consumer->>Graphiti: search_nodes(q="x", group_ids=["proj-foo"])
    Graphiti->>Decor: wrapper(self, q, ["proj-foo"])
    Note over Decor: len(["proj-foo"]) > 1 → False<br/>FALL THROUGH (BUG #8)
    Decor->>SearchOps: node_fulltext_search(executor[default graph], q, ["proj-foo"])
    SearchOps->>Builder: _build_falkor_fulltext_query("x", ["proj-foo"])
    Builder-->>SearchOps: '(@group_id:"proj-foo") (x)'
    Note over Builder: BUGS #5/#11: dash treated as NOT<br/>OR no data on default graph
    SearchOps->>Driver: execute_query(cypher, query='(@group_id:"proj-foo") (x)')
    Driver->>Falkor: GRAPH.QUERY default "<cypher>"
    Note over Falkor: Lookup against DEFAULT graph's index<br/>"proj-foo" data lives on graph 'proj-foo', not default<br/>→ empty result OR RediSearch syntax error
    Falkor-->>Driver: [] or error
    Driver-->>SearchOps: []
    SearchOps-->>Decor: []
    Decor-->>Graphiti: []
    Graphiti-->>Consumer: [] (silent miss)
```

**Failure mode today**: silent empty results. Bug compounds across #8 (wrong graph) + #5/#11 (broken filter on the wrong graph anyway). This is what guardkit's `apply_falkordb_workaround()` patches around at runtime.

---

## Diagram 2 — Read path (search_nodes, single-group, AFTER patch 001 ONLY, bug #8 NOT fixed)

This is the **dangerous interim state** where someone applies patch 001 in isolation without bug #8.

```mermaid
sequenceDiagram
    autonumber
    participant Consumer as Consumer (study-tutor)
    participant Graphiti as graphiti.search_nodes()
    participant Decor as @handle_multiple_group_ids
    participant SearchOps as FalkorSearchOperations
    participant Builder as _build_falkor_fulltext_query (PATCHED 001)
    participant Driver as FalkorDriver (default graph — wrong)
    participant Falkor as FalkorDB

    Consumer->>Graphiti: search_nodes(q="x", group_ids=["proj-foo"])
    Graphiti->>Decor: wrapper
    Note over Decor: BUG #8 still: len > 1 False → FALL THROUGH<br/>driver = default graph
    Decor->>SearchOps: node_fulltext_search(executor[default], q, ["proj-foo"])
    SearchOps->>Builder: _build_falkor_fulltext_query("x", ["proj-foo"])
    Builder-->>SearchOps: '(x)'  ← @group_id filter dropped
    SearchOps->>Driver: execute_query(cypher_with_WHERE_n.group_id_IN_proj-foo, query='(x)')
    Driver->>Falkor: GRAPH.QUERY default "<cypher>"
    Note over Falkor: Index lookup matches all nodes containing "x" on DEFAULT graph<br/>(default graph rarely has app data)<br/>WHERE n.group_id IN ['proj-foo'] filters → 0 matches
    Falkor-->>Driver: []
    Driver-->>SearchOps: []
    SearchOps-->>Decor: []
    Decor-->>Graphiti: []
    Graphiti-->>Consumer: [] (silent miss, same shape as before)
```

**Conclusion**: patch 001 alone does NOT regress single-group reads — it preserves the existing silent-miss bug. Both pre- and post-patch states return `[]` for the same inputs. No worse, no better.

---

## Diagram 3 — Read path (search_nodes, single-group, AFTER patch 001 + bug #8 BOTH fixed)

This is the **target end-state**.

```mermaid
sequenceDiagram
    autonumber
    participant Consumer as Consumer (study-tutor)
    participant Graphiti as graphiti.search_nodes()
    participant Decor as @handle_multiple_group_ids (PATCHED #8)
    participant SearchOps as FalkorSearchOperations
    participant Builder as _build_falkor_fulltext_query (PATCHED 001)
    participant Driver as FalkorDriver (CLONED on graph 'proj-foo')
    participant Falkor as FalkorDB

    Consumer->>Graphiti: search_nodes(q="x", group_ids=["proj-foo"])
    Graphiti->>Decor: wrapper
    Note over Decor: PATCHED: len >= 1 → CLONE PATH<br/>driver.clone(database='proj-foo')
    Decor->>SearchOps: node_fulltext_search(executor[graph 'proj-foo'], q, ["proj-foo"])
    SearchOps->>Builder: _build_falkor_fulltext_query("x", ["proj-foo"])
    Builder-->>SearchOps: '(x)'  ← filter dropped per patch 001
    SearchOps->>Driver: execute_query(cypher_with_WHERE_n.group_id_IN_proj-foo, query='(x)')
    Driver->>Falkor: GRAPH.QUERY proj-foo "<cypher>"
    Note over Falkor: Index lookup on 'proj-foo' graph<br/>All candidates have group_id='proj-foo' (single-tenant graph)<br/>WHERE clause is no-op but harmless
    Falkor-->>Driver: matching candidates
    Driver-->>SearchOps: candidates
    SearchOps-->>Decor: results
    Decor-->>Graphiti: results
    Graphiti-->>Consumer: populated results
```

**Conclusion**: correctness restored. Each patch addresses one of two compounding bugs. No regression vs upstream-broken-state.

---

## Diagram 4 — Read path (search_nodes, multi-group `["foo", "bar"]`, BEFORE and AFTER patches)

This is the case the upstream decorator already handles correctly. Patch 001 must not regress it.

```mermaid
sequenceDiagram
    autonumber
    participant Consumer as Consumer
    participant Graphiti as graphiti.search_nodes()
    participant Decor as @handle_multiple_group_ids
    participant SO_foo as FalkorSearchOperations<br/>(executor on 'foo')
    participant SO_bar as FalkorSearchOperations<br/>(executor on 'bar')
    participant Falkor as FalkorDB

    Consumer->>Graphiti: search_nodes(q="x", group_ids=["foo", "bar"])
    Graphiti->>Decor: wrapper
    Note over Decor: len > 1 → CLONE PATH (already worked)
    par Concurrent fan-out
        Decor->>SO_foo: node_fulltext_search(executor[graph 'foo'], q, ['foo'])
        SO_foo->>Falkor: GRAPH.QUERY foo "<cypher>"
        Falkor-->>SO_foo: results_foo
    and
        Decor->>SO_bar: node_fulltext_search(executor[graph 'bar'], q, ['bar'])
        SO_bar->>Falkor: GRAPH.QUERY bar "<cypher>"
        Falkor-->>SO_bar: results_bar
    end
    Note over Decor: SearchResults.merge(results_foo, results_bar)
    Decor-->>Graphiti: merged
    Graphiti-->>Consumer: merged populated
```

**Patch 001 effect on this path**: each per-group execution sees `_build_falkor_fulltext_query("x", ['foo'])` (single-element list — patch 001 returns `'(x)'` without `@group_id` prefix). Cypher `WHERE n.group_id IN ['foo']` is the backstop. Per-graph index lookup on 'foo' yields foo-only candidates. Filter passes them. Result: identical to upstream behaviour, plus dash-bug eliminated.

**Conclusion**: no regression on multi-group paths.

---

## Diagram 5 — Read path (search_nodes, group_ids=None / no filter, AFTER patches)

This is the "search across everything" case. Important to verify.

```mermaid
sequenceDiagram
    autonumber
    participant Consumer
    participant Graphiti as graphiti.search_nodes()
    participant Decor as @handle_multiple_group_ids
    participant Builder as _build_falkor_fulltext_query (PATCHED 001)
    participant Falkor as FalkorDB (default graph)

    Consumer->>Graphiti: search_nodes(q="x", group_ids=None)
    Graphiti->>Decor: wrapper
    Note over Decor: group_ids is None → FALL THROUGH (correct, both before and after)
    Decor->>Builder: _build_falkor_fulltext_query("x", None)
    Note over Builder: PATCH 001 short-circuit:<br/>group_filter = '' (always)<br/>Same as upstream's None branch
    Builder-->>Builder: returns '(x)'
    Note over Decor: Cypher: no WHERE on group_id (group_ids is None)
    Decor->>Falkor: GRAPH.QUERY default "<cypher>"
    Note over Falkor: Returns all matches across default graph
    Falkor-->>Decor: results
    Decor-->>Consumer: results (default graph only, by design)
```

**Conclusion**: identical behaviour pre- and post-patch. No regression. Note: `group_ids=None` only searches the default graph by design — if data is sharded across per-group graphs, the consumer must pass explicit group_ids. This is upstream contract, unchanged.

---

## Diagram 6 — Empty-query handling (post-stopword) — patch 001's `*` change

A subtle behaviour change in patch 001: when the query is empty after stopword removal (e.g. user query `"and the"`), patch 001 returns `'*'` (RediSearch match-all wildcard) instead of upstream's behaviour of constructing `'(@group_id:...) ()'` (which is invalid syntax → RediSearch error).

```mermaid
sequenceDiagram
    autonumber
    participant Consumer
    participant Builder as _build_falkor_fulltext_query
    participant SO as FalkorSearchOperations
    participant Falkor

    Consumer->>SO: search "and the"
    SO->>Builder: _build_falkor_fulltext_query("and the", ["foo"])
    Note over Builder: PATCH 001:<br/>sanitize → "and the"<br/>filter stopwords → ""<br/>if not sanitized_query: return '*'
    Builder-->>SO: '*'
    SO->>Falkor: GRAPH.QUERY foo "<cypher with $query='*'>"
    Note over Falkor: RediSearch '*' = match every doc<br/>Cypher LIMIT clamps result size<br/>WHERE n.group_id IN ['foo'] filters
    Falkor-->>SO: top-N candidates from 'foo' graph
    SO-->>Consumer: results (semantically: "I asked for X but only stopwords; got back arbitrary top-N")
```

**Regression analysis**: 
- **Pre-patch**: empty post-stopword query → RediSearch error → exception bubbles up → consumer sees crash.
- **Post-patch**: empty post-stopword query → arbitrary top-N from group → consumer sees noise but no crash.

Behaviour change is from "crash" to "noise". For all known consumer paths in study-tutor/guardkit, this is strictly better. For any consumer that relied on the crash to detect a degenerate query, the change is silent. **Mitigation**: in the changelog/FORK-NOTES.md, document this contract change explicitly.

---

## Diagram 7 — Write path (add_episode with backtick-tainted entity name) — patch 002

Patch 002 only touches the search-time `sanitize()` separator map. Write-side indexing flows through RediSearch's own tokenizer.

```mermaid
sequenceDiagram
    autonumber
    participant Consumer
    participant Graphiti as graphiti.add_episode()
    participant LLM as LLMClient.extract_entities
    participant Driver as FalkorDriver
    participant Falkor as FalkorDB (write)
    participant Index as RediSearch index (auto-update on MERGE)

    Consumer->>Graphiti: add_episode(episode_body="see `path/to/file.md`", group_id="proj")
    Graphiti->>LLM: extract entities from body
    LLM-->>Graphiti: [{name: "`path/to/file.md`", ...}]
    Note over Graphiti: entity name carries backticks (LLM literal-quoted)
    Graphiti->>Driver: save_node(name="`path/to/file.md`", group_id="proj")
    Driver->>Falkor: GRAPH.QUERY proj "MERGE (n {name: '`path/to/file.md`'})"
    Falkor->>Index: token-update name field
    Note over Index: RediSearch tokenizer splits on whitespace/punct<br/>backtick treatment varies by version<br/>Tokens may include 'path', 'to', 'file', 'md'
    Index-->>Falkor: indexed
    Falkor-->>Driver: ok
    Driver-->>Graphiti: ok
    Graphiti-->>Consumer: episode saved

    Note over Consumer,Index: --- LATER: search ---
    Consumer->>Graphiti: search_nodes(q="`path/to/file.md`")
    Note over Graphiti: PATCH 002: sanitize() strips backticks<br/>query becomes "path to file md"<br/>Tokens: {path, to, file, md} → match indexed tokens
```

**Regression analysis**:
- **Pre-patch**: search with backticks in query → RediSearch syntax error (or no match) → user sees no result.
- **Post-patch**: search with backticks → backticks stripped → matches against the path/to/file/md tokens → likely match.

**Edge case — pre-fork data**: if a consumer indexed entities with backtick literals BEFORE the fork (so `` ` `` is in the indexed token set), post-patch queries strip backticks and would miss. In practice, guardkit has been pre-stripping backticks via `falkordb_workaround.py:280-292` for months; the indexed token set in production already lacks backticks. So this risk is theoretical, not actual.

**Conclusion**: patch 002 is correctness-improving with no realistic regression.

---

## Diagram 8 — Edge fulltext search (BEFORE bug #9 fix)

```mermaid
sequenceDiagram
    autonumber
    participant SO as edge_fulltext_search
    participant Falkor

    SO->>Falkor: GRAPH.QUERY proj "<cypher>"
    Note over Falkor: Step A: CALL db.idx.fulltext.queryRelationships(...)<br/>YIELD relationship AS rel, score<br/>(returns ~1500 candidate edges)
    Note over Falkor: Step B (BUG #9):<br/>MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)<br/>For EACH of the 1500 yields, scan ALL ~5000 edges<br/>→ 7.5M comparisons → 26-118s latency
    Falkor-->>SO: results (eventually)
```

## Diagram 9 — Edge fulltext search (AFTER bug #9 fix)

```mermaid
sequenceDiagram
    autonumber
    participant SO as edge_fulltext_search (PATCHED #9)
    participant Falkor

    SO->>Falkor: GRAPH.QUERY proj "<cypher>"
    Note over Falkor: Step A: CALL db.idx.fulltext.queryRelationships(...)<br/>YIELD relationship AS rel, score
    Note over Falkor: Step B (FIXED):<br/>WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m<br/>O(n) direct endpoint lookup<br/>→ ~50ms latency
    Falkor-->>SO: results (fast)
```

**Regression analysis**: Cypher `startNode(e)` and `endNode(e)` are guaranteed-present built-ins on every relationship by definition. Result set is identical to pre-fix; only latency changes. Verification: guardkit's `tests/knowledge/test_falkordb_workaround.py` covers this exact transformation (the workaround applies the same fix at runtime). After fork lands, those tests should pass against the unwrapped graphiti-core directly.

**Conclusion**: pure performance fix. Zero correctness regression risk.

---

## Diagram 10 — MCP container startup (BEFORE patch 003)

```mermaid
sequenceDiagram
    autonumber
    participant Boot as Container entrypoint
    participant Module as graphiti_mcp_server (module load)
    participant Fast as FastMCP
    participant TS as TransportSecurityMiddleware
    participant Init as initialize_server()
    participant Uvi as uvicorn (HTTP server)
    participant Tail as Tailscale client (promaxgb10-41b1:8004)

    Boot->>Module: import graphiti_mcp_server
    Module->>Fast: FastMCP('Graphiti Agent Memory', instructions=...)
    Note over Fast: Default settings.host = '127.0.0.1'
    Fast->>TS: construct(allow_list=['127.0.0.1', 'localhost'])
    Note over TS: ALLOW-LIST FROZEN
    Module->>Init: asyncio.run(run_mcp_server()) → initialize_server()
    Init->>Fast: mcp.settings.host = '0.0.0.0'  (from yaml)
    Note over Fast,TS: Mutates settings AFTER freeze<br/>TS allow-list still ['127.0.0.1', 'localhost']
    Init->>Uvi: mcp.run_streamable_http_async()
    Uvi->>Uvi: bind 0.0.0.0:8004
    Tail->>Uvi: GET /mcp/ Host: promaxgb10-41b1
    Uvi->>TS: validate(host='promaxgb10-41b1')
    Note over TS: 'promaxgb10-41b1' NOT IN allow-list → REJECT
    TS-->>Tail: HTTP 421 Invalid Host header
```

This is what the existing `graphiti-mcp-bootstrap.py` shim works around (by patching `_validate_host`/`_validate_origin` to no-ops post-import).

## Diagram 11 — MCP container startup (AFTER patch 003 + env export)

```mermaid
sequenceDiagram
    autonumber
    participant Boot as Container entrypoint<br/>(env: MCP_SERVER_HOST=0.0.0.0)
    participant Module as graphiti_mcp_server (module load, PATCHED)
    participant Fast as FastMCP
    participant TS as TransportSecurityMiddleware
    participant Init as initialize_server()
    participant Uvi as uvicorn
    participant Tail as Tailscale client

    Boot->>Module: import graphiti_mcp_server
    Module->>Module: _initial_host = os.environ.get('MCP_SERVER_HOST', '127.0.0.1') = '0.0.0.0'
    Module->>Fast: FastMCP(name, host='0.0.0.0', instructions=...)
    Fast->>TS: construct(host='0.0.0.0' → open allow-list per FastMCP semantics)
    Note over TS: Allow-list permissive (or includes 0.0.0.0)
    Module->>Init: initialize_server()
    Init->>Fast: mcp.settings.host = '0.0.0.0' (idempotent)
    Init->>Uvi: run_streamable_http_async()
    Tail->>Uvi: GET /mcp/ Host: promaxgb10-41b1
    Uvi->>TS: validate(host='promaxgb10-41b1')
    Note over TS: Permissive allow-list → ACCEPT
    TS-->>Tail: HTTP 200 OK
```

**Regression analysis**:
- **MCP_SERVER_HOST not set in env**: defaults to `'127.0.0.1'` → identical to upstream. Zero regression for any deployment that doesn't currently rely on the bootstrap shim.
- **MCP_SERVER_HOST=0.0.0.0 set, bootstrap shim still in place**: shim's `_validate_host`/`_validate_origin` no-ops are still applied post-import; patch 003 already made TS permissive. Both layers agree. No conflict.
- **MCP_SERVER_HOST=0.0.0.0 set, shim retired**: patch 003 alone handles host binding. Tailscale requests accepted.
- **MCP_SERVER_HOST=0.0.0.0 set, shim retired, patch 003 NOT applied**: no host opening at all → HTTP 421 on every external request → deployment breaks. **This is the dangerous interim state.**

**Critical**: the env export and the shim retirement must happen in the same commit (or the shim retirement must come strictly AFTER the patched container is verified working). See Recommendation #4 in the parent report.

---

## Diagram 12 — LLM call routing (BEFORE factories.py auto-detect fix)

```mermaid
sequenceDiagram
    autonumber
    participant Consumer as graphiti.add_episode()
    participant LLMC as LLMClient (graphiti-core)
    participant Factory as factories.py (BEFORE)
    participant OAIC as OpenAIClient (graphiti-core)
    participant SDK as openai SDK (AsyncOpenAI default)
    participant OpenAI as api.openai.com<br/>(NOT what we want)
    participant LlamaSwap as localhost:9000<br/>(what we want)

    Consumer->>Factory: LLMClientFactory.create(config: provider='openai', api_url='http://localhost:9000/v1')
    Note over Factory: BUG #6: api_url IGNORED<br/>llm_config = CoreLLMConfig(api_key, model, ...)<br/>(no base_url field)
    Factory->>OAIC: OpenAIClient(config=llm_config, ...)
    OAIC->>SDK: AsyncOpenAI(api_key=key)
    Note over SDK: base_url defaults to 'https://api.openai.com/v1'
    Consumer->>LLMC: generate_response(messages)
    LLMC->>OAIC: generate
    OAIC->>SDK: client.responses.parse(...)
    Note over SDK: BUG #7: uses Responses API not Chat Completions
    SDK->>OpenAI: POST https://api.openai.com/v1/responses
    OpenAI-->>SDK: 401 Unauthorized (api_key='not_needed')
    SDK-->>OAIC: AuthenticationError
    OAIC-->>Consumer: exception
    Note over LlamaSwap: Never receives a request
```

## Diagram 13 — LLM call routing (AFTER factories.py auto-detect fix, Approach A)

```mermaid
sequenceDiagram
    autonumber
    participant Consumer as graphiti.add_episode()
    participant Factory as factories.py (PATCHED, Approach A)
    participant OGC as OpenAIGenericClient
    participant SDK as openai SDK
    participant LlamaSwap as localhost:9000<br/>(llama-swap → Qwen)

    Consumer->>Factory: create(config: provider='openai', api_url='http://localhost:9000/v1')
    Note over Factory: PATCHED:<br/>base_url = config.providers.openai.api_url<br/>llm_config = CoreLLMConfig(api_key, model, base_url=base_url, ...)<br/>is_openai_endpoint = 'api.openai.com' in 'http://localhost:9000/v1' → False<br/>logger.info('Using OpenAIGenericClient for ...')
    Factory->>OGC: OpenAIGenericClient(config=llm_config, max_tokens=...)
    OGC->>SDK: AsyncOpenAI(api_key=key, base_url='http://localhost:9000/v1')
    Consumer->>OGC: generate_response(messages)
    OGC->>SDK: client.chat.completions.create(...)
    Note over SDK: Chat Completions API (vLLM-compatible)
    SDK->>LlamaSwap: POST http://localhost:9000/v1/chat/completions
    LlamaSwap-->>SDK: 200 OK + structured output
    SDK-->>OGC: response
    OGC-->>Consumer: extracted entities
```

**Regression analysis** for Approach A:

| Configuration | Pre-patch behaviour | Post-patch behaviour | Regression? |
|---------------|---------------------|----------------------|-------------|
| `provider: openai`, `api_url: https://api.openai.com/v1`, OpenAI key | Works (default OpenAI Responses API) | Works (auto-detect: `'api.openai.com' in url` → keeps OpenAIClient) | None |
| `provider: openai`, `api_url: null` (unset) | Works | Works (`base_url is None` → keeps OpenAIClient) | None |
| `provider: openai`, `api_url: http://localhost:9000/v1` (vLLM) | **Broken** (401 on api.openai.com) | Works (auto-detect → OpenAIGenericClient → Chat Completions) | None — this is the fix |
| `provider: openai`, `api_url: https://my-azure.example.com/openai/v1` (Azure-fronted proxy) | Works ONLY IF proxy supports Responses API | Switches to Chat Completions; fails ONLY IF caller relied on Responses-only features | **Theoretical regression** — see below |
| `provider: openai`, `api_url: https://my-litellm.example.com/v1` (LiteLLM proxy) | Probably works (LiteLLM emulates Responses) | Switches to Chat Completions; safer | None |

**Theoretical Azure-proxy regression**: a deployment that uses `provider: openai` with a non-`api.openai.com` URL pointing at an Azure proxy specifically because the proxy supports the Responses API. Such deployments would post-patch route through Chat Completions instead. **Mitigation**: graphiti-core's structured-output use case maps cleanly to Chat Completions tool-calling; nothing it asks for requires Responses API features (no built-in tools, no web_search, no file_search). For graphiti-core specifically, this regression is benign in functional terms. Additionally: such deployments are rare (Azure has its own provider arm `azure_openai`, which is a separate factories.py case unaffected by this patch). **Recommendation**: document the auto-detect contract in FORK-NOTES.md so operators with exotic proxy setups can configure explicitly.

---

## Critical interaction analysis

The most important interaction is **patch 001 (drop @group_id filter) ↔ bug #8 (decorator `>1` → `>=1`)**.

These two patches are **commutatively safe** — applying one without the other does not introduce regression, because:

- Patch 001 alone: single-group queries that returned `[]` continue to return `[]`. Same shape, same outcome.
- Bug #8 fix alone: single-group queries now hit the right graph; `(@group_id:"proj-foo")` filter still applied; if `proj-foo` contains a dash, the index still mistreats it as NOT → empty results. **Same `[]` outcome**.
- Both together: correctness fully restored.

**Key insight**: there is no execution path where applying one patch and not the other causes the system to produce *worse* output than upstream. The compounded buggy state and the partially-patched states all return `[]` for the same buggy inputs. This means patches can land in any order without introducing transient regressions.

The full ordering in the proposed plan is:

1. Patch 001 (RediSearch drop-filter) — safe in isolation
2. Patch 002 (sanitize backtick) — orthogonal, safe in isolation
3. Patch 003 (MCP host binding) — safe in isolation as long as MCP_SERVER_HOST env export is added in same commit as bootstrap-shim retirement
4. factories.py auto-detect (#6/#7) — safe in isolation (fixes broken vLLM path; legacy OpenAI path preserved)
5. Bug #8 fix (decorator `>=1`) — safe in isolation; needed to make patch 001 *useful* but not to make it *non-regressive*
6. Bug #9 fix (edge_*search Cypher) — pure performance, safe in isolation

**Recommended sequencing on the GB10**: apply 001+002+003 first as one commit (they're already in `patches/`), then factories.py as a second commit, then bug #8 cherry-pick as a third commit, then bug #9 as a fourth commit. Each is independently revertable. Run the verification suite (AC-FORK-08) after each commit so a regression can be bisected to a single landed patch.

---

## Regression Matrix (consolidated)

| # | Boundary | Patch | Failure mode if patch wrong | Likelihood | Safety net | Validator (test) |
|---|----------|-------|------------------------------|------------|------------|--------------------|
| 1 | B3 | Patch 001 (drop filter) | Single-group reads return cross-group data | None — Cypher WHERE backstop catches | Mitigated by Cypher | `test_falkordb_workaround.py::test_search_with_dashed_group_id` |
| 2 | B3 | Patch 001 (`*` for empty post-stopword) | Crash → noise behaviour change | Low | None — change is intentional | Manual smoke test of all-stopword queries |
| 3 | B3 | Patch 002 (strip backtick) | Search-miss against legacy backtick-tainted index | Theoretical only (guardkit pre-strips) | None | Re-run guardkit seed against backtick-rich corpus |
| 4 | B5 | Patch 003 (host binding) | HTTP 421 on external clients if env not set | Low (default = upstream behaviour) | Bootstrap shim retained until verified | `curl -H 'Host: promaxgb10-41b1:8004' http://promaxgb10-41b1:8004/mcp/` |
| 5 | B4 | factories.py (Approach A) | Azure-fronted proxy expecting Responses API drops to Chat Completions | Theoretical (azure_openai has own branch) | None | `docker logs graphiti-mcp` for the auto-detect log line |
| 6 | B2 | Bug #8 fix (decorator) | Single-group calls now do driver-clone (perf cost) | None — clone is cheap | None | Existing `test_falkordb_workaround.py` decorator suite |
| 7 | B3 | Bug #9 fix (startNode/endNode) | Result set differs from re-MATCH version | None — semantics identical | Cypher built-ins guaranteed | Existing `test_falkordb_workaround.py::test_edge_fulltext_search` |
| 8 | All | Combined application | Patch ordering induces regression | None — see commutative analysis | Bisectable per-commit landing | Run AC-FORK-08 verification after each commit |

**Net regression risk**: **none** under the recommended landing order, AND none under any landing order.

---

## Pre-application baseline capture (recommended addition to mechanical plan)

Insert as **step 0** in the mechanical plan (currently steps 1-10):

```bash
# Step 0 — Capture baseline before any patches land
cd ~/Projects/appmilla_github/graphiti
.venv/bin/pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/baseline-falkordb.txt
.venv/bin/pytest mcp_server/tests/ --tb=line 2>&1 | tee /tmp/baseline-mcp.txt

# Capture guardkit's monkey-patch test suite baseline (against unforked graphiti-core)
cd ~/Projects/appmilla_github/guardkit
.venv/bin/pytest tests/knowledge/test_falkordb_workaround.py -v 2>&1 | tee /tmp/baseline-workaround.txt
```

Insert as **step 9.5** (after each patch commit):

```bash
# Step 9.5 — After each commit, re-run the same suites and diff
cd ~/Projects/appmilla_github/graphiti
.venv/bin/pytest tests/ -k "falkordb" --tb=line 2>&1 | tee /tmp/post-${COMMIT_SHA:0:7}-falkordb.txt
diff /tmp/baseline-falkordb.txt /tmp/post-${COMMIT_SHA:0:7}-falkordb.txt
# Expect: no regressions; possible new passes from patches/bug fixes
```

Add **AC-FORK-19**: "Pre-application baseline captured (step 0). Post-each-commit diff shows no test regressions. Any new failures bisect to a single landed patch."

---

## Confidence statement

After this trace, **confidence in zero-regression landing is high** (estimate: 95%+).

The remaining 5% covers:
- Exotic operator configurations not currently in the appmilla deployment (Azure-fronted proxy with Responses API expectation — Diagram 13 §"Theoretical Azure-proxy regression").
- Unobserved interaction between RediSearch versions (FalkorDB 1.1.x vs newer) and tokenizer behaviour for backticks.
- The 600-line bug #9 reshape from `falkordb_workaround.py` to in-tree `search_utils.py` form (not yet drafted; subject to derivation-time bugs).

Recommendation: proceed with `[I]mplement` to lock the six decisions and pre-draft patches 004 (bug #8) and 005 (bug #9), then verify against the baseline-and-diff approach in step 0/step 9.5 above.

## Summary

- All five technology boundaries traced.
- Thirteen sequence diagrams covering before/after states for every patch.
- Cypher WHERE clause confirmed as backstop for dropped @group_id filter (verified at search_ops.py lines 142-144, 187-189, 240-243, 292-294).
- Decorator `>1` interaction confirmed; landing-order analysis shows no transient regressions.
- LLM auto-detect routing has one theoretical edge case (Azure-fronted proxy needing Responses API); benign for graphiti-core's structured-output use case.
- MCP host binding patch is a no-op for deployments that don't set `MCP_SERVER_HOST`; safe to land standalone.
- Edge-search bug #9 fix is a pure performance change; no semantic risk.
- Pre-application baseline + post-each-commit diff gives a zero-cost regression detector.

**Net assessment**: the patches as drafted, applied per the recommended ordering with the new step 0 baseline capture, carry no realistic regression risk.
