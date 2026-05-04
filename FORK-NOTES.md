# guardkit fork — FORK-NOTES.md

## What this fork is

This is a fork of [getzep/graphiti](https://github.com/getzep/graphiti) at version
**0.29.0** (commit [`56cf7b3`](https://github.com/getzep/graphiti/commit/56cf7b3))
with bug-fix patches applied for the guardkit deployment stack
([study-tutor](https://github.com/appmilla/study-tutor),
[guardkit](https://github.com/appmilla/guardkit), jarvis).

- **Repo**: <https://github.com/guardkit/graphiti>
- **Working branch**: `guardkit-fixes-0.29`
- **First release tag**: `v0.29.5-guardkit.1` (cut 2026-05-04)
- **Tag scheme**: `v{upstream-version}-guardkit.{n}` — bump `n` for each new shipping
  moment off the same upstream base; bump `{upstream-version}` when re-basing onto a
  new upstream release.
- **Maintained by**: guardkit. Source-of-truth task that drove the initial fork is
  [`tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md`](tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md).

Consumers should pin to a tag, not the branch tip:

```toml
# pyproject.toml
"graphiti-core @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1#subdirectory=graphiti_core"
```

## Why this fork exists

Counting bugs across the guardkit graphiti integration surfaced **13 distinct
upstream defects** across graphiti-core 0.28.x → 0.29.x and graphiti-mcp. Bugs
#1-#3 are consumer-side wiring choices and stay patched in consumer code; bug #4
was fixed upstream in 0.29.0 (see [bug-numbering note](#bug-numbering-note-4-vs-5)
below); the rest live in this fork. Patches sitting in consumer code (study-tutor /
guardkit / jarvis venvs + the GB10 graphiti-mcp container) don't propagate — bugs
do. Forking is the lowest-risk way to ship one source of truth for the fixes
without blocking on upstream-PR responsiveness.

## Patches in this fork

Applied as four bisect-safe commits on `guardkit-fixes-0.29`. Each commit wraps
one or more pre-drafted patches under [`patches/`](patches/) (see
[`patches/README.md`](patches/README.md) for the unified diffs and apply-order
rationale).

| # | Commit | Subject | Patches | Bugs fixed |
|---|--------|---------|---------|------------|
| 1 | [`94a2e6d`](https://github.com/guardkit/graphiti/commit/94a2e6d) | `fix(falkordb,mcp): drop @group_id filter, strip backtick, bind FastMCP host` | `001-drop-fulltext-group-filter.patch`, `002-extend-sanitize-strip-backtick.patch`, `003-mcp-early-host-binding.patch` | #5, #10, #11, #12, #13 |
| 2 | [`85ec55b`](https://github.com/guardkit/graphiti/commit/85ec55b) | `fix(factories): auto-detect non-OpenAI endpoints, route to OpenAIGenericClient` | `006-factories-auto-detect.patch` | #6, #7 |
| 3 | [`7a914ec`](https://github.com/guardkit/graphiti/commit/7a914ec) | `fix(decorator): handle single-group FalkorDB calls` | `004-handle-multiple-group-ids-decorator.patch` | #8 |
| 4 | [`9198756`](https://github.com/guardkit/graphiti/commit/9198756) | `fix(search): direct endpoint access via startNode/endNode` | `005-edge-search-direct-endpoints.patch` | #9 |

Tag [`v0.29.5-guardkit.1`](https://github.com/guardkit/graphiti/releases/tag/v0.29.5-guardkit.1)
points at commit 4 (`9198756`).

### Bug index

| Bug | Symptom | Fix | Pre-fork home |
|-----|---------|-----|---------------|
| **#5** | RediSearch dashes-as-NOT — upstream's double-quote wrap of `@group_id` doesn't actually escape dashes; queries against dashed group_ids return zero hits or syntax-error | Drop the `@group_id` filter entirely from `build_fulltext_query`; group isolation is already enforced by the multi-graph driver clone (bug #8 fix path) plus the Cypher `WHERE` clause | `guardkit/knowledge/falkordb_workaround.py:287-309` (runtime monkey-patch) |
| **#6** | `mcp_server/src/services/factories.py` `case 'openai':` arm ignores `api_url`, falls through to `api.openai.com` and 401s when pointed at a local OpenAI-compatible server | Auto-detect non-OpenAI endpoints from `base_url` and route to `OpenAIGenericClient` (Decision 6, Approach A) | guardkit `TASK-INF-5054` (uncommitted local patch on dev Mac) |
| **#7** | `OpenAIClient` calls `responses.parse()` (Responses API) instead of `chat.completions.create` → 404 against vLLM / llama-swap / most OpenAI-compatible servers | Same fix as #6: routing to `OpenAIGenericClient` (Chat Completions API) avoids the Responses API call | bundled with #6 |
| **#8** | `handle_multiple_group_ids` decorator uses `len(group_ids) > 1` instead of `>= 1`; single-group searches skip the FalkorDB driver-clone and select the wrong named graph | Change condition to `>= 1` so single-group calls also fan out via per-group driver clones (mirrors upstream PR [#1170](https://github.com/getzep/graphiti/pull/1170) / issue [#1161](https://github.com/getzep/graphiti/issues/1161)) | `guardkit/knowledge/falkordb_workaround.py:97-176` (runtime monkey-patch) |
| **#9** | `edge_fulltext_search` and `edge_bfs_search` re-MATCH on `rel.uuid` to re-find edge endpoints — O(n×m) full-edge scan per result (1500 results × 5000 edges = 7.5M comparisons → 26-118s per query) | Replace re-MATCH with `startNode(e)` / `endNode(e)` direct-endpoint access (mirrors upstream issue [#1272](https://github.com/getzep/graphiti/issues/1272)) | `guardkit/knowledge/falkordb_workaround.py:380-635` (runtime monkey-patch) |
| **#10** | Upstream `sanitize()` in 0.29.0 omits backticks from its character-strip list; markdown corpora with `` `path/to/file.md` `` references break RediSearch syntax during fulltext-index writes. (Slashes/pipes/backslashes were added upstream in 0.29.0; backtick is the only remaining gap.) | Add backtick to the strip set in `FalkorDriver.sanitize()` and `_SEPARATOR_MAP` | `guardkit/knowledge/falkordb_workaround.py:280-292` (runtime monkey-patch); root cause: guardkit `TASK-REV-661E` |
| **#11** | `@group_id` filter is broken on FalkorDB regardless of dash-escape: group_ids tokenise at index time (underscores split tokens), and group isolation is **already** enforced by the driver clone + Cypher `WHERE` | Same fix as #5 — dropping the filter eliminates #11 and #12 in the same diff | `guardkit/knowledge/falkordb_workaround.py:287-309` |
| **#12** | `build_fulltext_query` produces invalid `'()'` or `''` syntax when input is empty after stopword removal → RediSearch syntax error on every all-stopword query | Same fix as #5 — patch additionally returns `'*'` (match-all) when post-stopword query is empty | `guardkit/knowledge/falkordb_workaround.py:303-305` |
| **#13** | graphiti-mcp's `main()` mutates `mcp.settings.host = "0.0.0.0"` **after** FastMCP has frozen `transport_security` with the localhost-only allow-list; non-loopback clients (Tailscale hostnames) get `421 Invalid Host header` | Read `MCP_SERVER_HOST` env var at module load and pass it to FastMCP construction so `transport_security` freezes against the right allow-list (`graphiti-mcp.sh` exports `MCP_SERVER_HOST=0.0.0.0` for the bootstrap shim to be retirable) | `guardkit/scripts/graphiti-mcp-bootstrap.py:38-39` (TransportSecurityMiddleware no-op patch) |

Bugs #1-#4 are not in this table because they're either consumer-side wiring
(#1-#3) or fixed upstream before the fork was cut (#4 — see below).

## Locked decisions (from TASK-FORK-PATCH)

Six decisions were locked on 2026-05-04 before patching started. Rationale and
alternatives are in
[`tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md`](tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md);
short form here:

1. **Upstream version** — fork from **0.29.x** (not 0.28.x). Single-version policy
   across study-tutor / guardkit / jarvis is operationally simpler than maintaining
   two parallel fork branches; study-tutor's pin is already `>=0.29,<0.30`.
2. **Visibility** — **public** fork. Enables a credible "we use a fork of graphiti"
   narrative (e.g. for the DDD South West talk in mid-May 2026), and
   `pip install git+https://...` works without GitHub-token plumbing across two
   CI surfaces.
3. **Location** — **`guardkit` GitHub org** (now: <https://github.com/guardkit/graphiti>).
   URL stability favours an org over a personal account; engineering-equivalent
   either way.
4. **Tag-and-pin (not branch-and-pin)** — consumers pin to immutable tags
   (`v0.29.5-guardkit.1`); active development happens on `guardkit-fixes-0.29`;
   each shipping moment cuts a fresh tag. The branch tip is mutable and is never
   what consumers should pin to.
5. **RediSearch fulltext fix shape — drop the filter** (not escape-and-keep).
   This matches the production-tested behaviour of
   `guardkit/knowledge/falkordb_workaround.py` (in service for several months),
   fixes bugs #5 + #11 + #12 in one diff, and is backstopped by the Cypher
   `WHERE n.group_id IN $group_ids` clause on every fulltext call site.
6. **Factory routing shape — auto-detect on `api_url`** (Approach A, not the
   explicit `case 'openai_generic':` arm of Approach B). Zero config-schema
   churn on consumers; matches the established pattern from 2026-04-03 (recorded
   in the guardkit Graphiti knowledge graph). The cost is implicit behaviour
   (operators reading `provider: openai` may not realise the runtime swaps to
   `OpenAIGenericClient`); mitigated by the `INFO Using OpenAIGenericClient for
   non-OpenAI endpoint: ...` log line on first LLM call.

## Important semantic changes

These are the patch effects that a future reader (especially an upstream-merge
maintainer) is most likely to be surprised by. Both are intentional:

### `edge_bfs_search` no longer double-counts edges

Patch [`005-edge-search-direct-endpoints.patch`](patches/005-edge-search-direct-endpoints.patch)
replaces an undirected `MATCH (n)-[e]-(m)` (which returned each edge twice with
swapped endpoints) with a directed `(n)-[e]->(m)` form using `startNode(e)` /
`endNode(e)`. Result count for `edge_bfs_search` calls **drops by ~2×** for
graphs with no inverse edges — that is a **latent-bug fix, not a regression**.
Downstream consumers that were expecting the double-count are buggy and should be
fixed.

### `build_fulltext_query` returns `*` for empty post-stopword queries

Patch [`001-drop-fulltext-group-filter.patch`](patches/001-drop-fulltext-group-filter.patch)
rewrites `build_fulltext_query` so that an input query consisting entirely of
stopwords (which used to produce `'()'` or `''` and crash RediSearch) now returns
`'*'` — a match-all. This is **a crash → match-all transition**, not a no-op.
Downstream callers that were relying on the crash to short-circuit empty searches
should add an explicit empty-string check.

## Bug-numbering note: #4 vs #5

Confusion is easy here, so calling it out explicitly:

- **Bug #4** is the `GroupIdValidationError` rejection of colons in group_ids.
  This was **fixed UPSTREAM in 0.29.0**, before this fork was cut. The fork
  inherits the fix; there is no patch for #4 in
  [`patches/`](patches/). Consumer code that previously did
  colon→dash format migration (e.g. study-tutor commit `a210472`) can stay in
  place but is no longer load-bearing on graphiti-core ≥ 0.29.0.
- **Bug #5** is the RediSearch dash-tokenisation defect (dashes treated as the NOT
  operator). This is fixed **in this fork** by patch
  [`001`](patches/001-drop-fulltext-group-filter.patch) — see commit
  [`94a2e6d`](https://github.com/guardkit/graphiti/commit/94a2e6d).

If a future reader is searching the bug numbers and finds no patch for #4, that
is correct: it is upstream's fix, not ours.

## Cross-references

These are the source tasks that surfaced each defect — all in the appmilla repos,
not in this fork.

- **study-tutor `TASK-GR-SEED`** — surfaced bugs #5 / #11 / #12 during Wave 5
  retry on 2026-05-03 (risk-register entry **R-WAVE5-03**); evidence in
  `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry — TASK-GR-SEED
  run 5".
- **guardkit `TASK-INF-5054`** — full spec for bugs #6 / #7; the originally-drafted
  patch shape (explicit `openai_generic` provider) was Decision 6's Approach B,
  rejected in favour of auto-detect.
- **guardkit `TASK-INF-5053`** — parent investigation that ruled out the alleged
  `group_id` coercion bug and surfaced bugs #6 (`api_url` ignored) and #7
  (`responses.parse` 404). Located at
  `guardkit/tasks/completed/2026-05/TASK-INF-5053-graphiti-mcp-http-server-group-id-fix.md`.
- **guardkit `TASK-REV-661E`** — root cause for bug #10 (sanitize gaps for
  backticks / slashes / pipes / backslashes). Slashes / pipes / backslashes
  landed upstream in 0.29.0; backtick is the residual gap that this fork closes.
- **guardkit `TASK-REV-84A7`** — `llm_max_tokens: 4096` cap rationale (graphiti-core
  default 16384 exceeds the 32K context window of the GB10 vLLM/llama-swap
  deployment). **Not patched here** — it's a config recommendation, not a defect.
  Recorded in graphiti-mcp-config.yaml in guardkit, not in this fork.
- **`guardkit/knowledge/falkordb_workaround.py`** — the runtime monkey-patch
  module that this fork supersedes for bugs #5 / #8 / #9 / #10 / #11 / #12. Once
  all consumers (study-tutor / guardkit / jarvis) are pinned to a fork tag and
  the GB10 graphiti-mcp container is rebuilt against the fork, the workaround
  module can be retired (tracked as guardkit `TASK-GK-RETIRE-WORKAROUND`).

## Maintenance plan

### Cadence

Cut a fresh `v{upstream}-guardkit.{n}` tag at each shipping moment (i.e. when a
consumer needs a new pin). Don't bump tag numbers speculatively — branch tips
move freely on `guardkit-fixes-0.29`, only tags are stable contracts.

Re-base onto a new upstream release (e.g. 0.30.x) **at most quarterly** during the
expected lifetime of the fork. The merge process is:

1. `git remote add upstream https://github.com/getzep/graphiti.git` (one-off)
2. `git fetch upstream`
3. Branch off the current fork tip: `git checkout -b guardkit-fixes-{new-version}-rebase`
4. `git merge upstream/main` (or the new release tag) — expect conflicts in
   `falkordb_driver.py`, `search_utils.py`, `decorators.py`, `factories.py`,
   `graphiti_mcp_server.py`. The patches under [`patches/`](patches/) are
   structured so each one is independently re-applicable; if a conflict cannot
   be resolved cleanly, drop the patch's commit and re-apply the patch under
   `patches/` as a fresh commit on the rebased branch.
5. Re-run AC-FORK-08 verification (study-tutor seed, MCP probes, container
   logs) before cutting `v{new-version}-guardkit.1`.
6. Update [`patches/README.md`](patches/README.md) and this file with the new
   patch SHAs and any newly-surfaced upstream-fixed bugs (move them out of the
   bug index into a "fixed upstream in {version}" footnote).

### Cutting a new tag

```bash
# On guardkit-fixes-0.29, after the fix-commits have landed:
git tag -a v0.29.5-guardkit.{n+1} -m "guardkit fork release: ..."
git push origin v0.29.5-guardkit.{n+1}
```

Annotated tags only (never lightweight). Tag message should list the bug numbers
fixed since the previous tag and reference any new patches added under
[`patches/`](patches/).

### When to consider proposing fixes upstream

Once the fork has been stable in production for several months and the underlying
bug is reproducible against unpatched upstream, consider opening a PR back to
[getzep/graphiti](https://github.com/getzep/graphiti) using the patch under
[`patches/`](patches/) as the reference implementation. Priority candidates:

- Bugs **#8** and **#9** already have upstream issues filed (PR #1170 / issue
  #1272) — relatively low-cost to push our diffs as PRs against those threads.
- Bugs **#5 / #11 / #12** (the RediSearch fulltext rewrite) are FalkorDB-specific
  and upstream's previous attempted fix shipped broken — engage carefully and
  expect a longer review cycle.
- Bug **#13** (graphiti-mcp host binding) is a small, self-contained change to
  the MCP server's startup sequence — good upstream-PR candidate.

Don't block consumer migration on upstream merge. The fork is the canonical
deployment target until upstream has all of the above merged and released.

### Releases

`v0.29.5-guardkit.1` was published as a GitHub Release on 2026-05-04 — see
<https://github.com/guardkit/graphiti/releases/tag/v0.29.5-guardkit.1>. Future
tags should also be published as Releases with the tag annotation copied into
the release body, plus a "Patches in this release" table mirroring the one in
this file.
