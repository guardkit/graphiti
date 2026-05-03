The right pattern uses git checkout <branch> -- <paths> to path-scope the transfer from your working branch to a clean PR branch:


# 1. Working branch off guardkit-tooling
git checkout -b work/falkordb-fixes guardkit-tooling
# ...run /task-review, /task-work, commit freely (mixed commits are fine)...

# 2. When ready to PR — create clean branch off main
git checkout -b pr/falkordb-fixes main

# 3. Pull ONLY source-code paths from working branch
git checkout work/falkordb-fixes -- graphiti_core/ mcp_server/src/ server/ tests/

# 4. Inspect, commit, push
git status                 # verify nothing tooling-related crept in
git diff --cached
git commit -m "fix(falkordb): drop unreliable fulltext group_id filter"
git push -u origin pr/falkordb-fixes
gh pr create --repo getzep/graphiti --base main \
  --head guardkit:pr/falkordb-fixes
Why this works: git checkout <branch> -- <paths> only updates those paths — .claude/, .guardkit/, patches/, docs/reviews/, task-status files all stay absent on pr/... because they're never selected. No commit discipline required on the working branch.

One PR per logical fix: instead of one big PR, run step 3 with narrower paths per fix (e.g., just graphiti_core/driver/falkordb_driver.py and graphiti_core/driver/falkordb/operations/search_ops.py for the fulltext filter fix). Each upstream PR stays small and reviewable — matching how the patches/ README already breaks them up.

Optional refinement — keep patches/ in sync: if you also want patches/NNN.patch on guardkit-tooling to reflect what actually got merged, regenerate after the PR lands:


git checkout guardkit-tooling
git diff main..pr/falkordb-fixes -- graphiti_core/ > patches/001-...patch
git add patches/ && git commit -m "sync patches with merged PR"
The list of "source paths" worth knowing for this repo: graphiti_core/, mcp_server/src/, server/, tests/, examples/. Anything else (.claude/, .guardkit/, patches/, docs/, tasks/, root-level config you've added like .mcp.json) is fork-only.





For TASK-FORK-PATCH specifically:


cd /Users/richardwoollcott/Projects/appmilla_github/graphiti
/task-review TASK-FORK-PATCH --mode=decision --depth=standard
Why --mode=decision: the task has 6 explicit unresolved DECISION: _TBD_ placeholders (versions, public/private, owner, tag/branch, drop-filter-vs-escape, auto-detect-vs-explicit). decision mode is purpose-built to surface and lock those before any patching starts — which is exactly what AC-FORK-01 + AC-FORK-13 + AC-FORK-15 require.

Why --depth=standard (not comprehensive): the audit itself was already comprehensive — the task body has the full bug inventory, the in-flight diff details, the production-wiring analysis, and the stale-config warnings. Standard depth is enough to lock the decisions and validate the punchlist; comprehensive would re-derive things that are already in writing.

Alternatives worth considering
--mode=architectural — defensible if you want the review to also re-litigate the strategic call (fork vs shrink vs replace). I wouldn't — that decision is solid and re-opening it before mid-May burns the time you saved by choosing the fork. Save architectural mode for the post-DDD "what next" review.
--mode=technical-debt — also defensible since the whole task IS consolidating accumulated graphiti debt. But decision is more action-forcing right now; technical-debt framing is better for the post-DDD retrospective.
--depth=comprehensive — only worth it if you want a full structured report you can hand to someone else (e.g., a co-presenter for the DDD talk). For your own use, standard is faster.
Caveats
Skip --capture-knowledge for now. That flag would try to write the review findings into the Graphiti knowledge graph via MCP — and the MCP write path is exactly what's broken (bugs #6/#7 in the audit). It would silently drop the capture. Re-enable it after TASK-FORK-PATCH lands and AC-FORK-08 verifies MCP writes work.
Run from the graphiti fork directory, not from study-tutor — the task file lives in the fork's tasks/backlog/ and /task-review looks in the current working directory's task tree.
Consider --no-questions if you don't want the clarification phase prompting you on review scope (the task is already extensively scoped); the standard prompt would mostly be redundant.
So my one-liner pick: /task-review TASK-FORK-PATCH --mode=decision --depth=standard --no-questions from the graphiti fork dir.

