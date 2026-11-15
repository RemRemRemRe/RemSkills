# Search Mechanics Pitfalls

Bounded search through the project's MCP server is the only sanctioned retrieval path
(`rem-no-disk-scanning`). Three of its mechanics bite before you notice, and each has a cheap
control that turns a silent wrong answer into a visible one.

## 1. An over-escaped pattern returns empty without an error

A regex with more escaping than the tool expects matches nothing and reports no error — the result
is indistinguishable from "the symbol does not exist". **Never conclude from a zero-hit result
without a control**: run the same call shape for a word you know exists (the enclosing file's own
name, a namespace). If the control is also empty, the query is malformed, not the codebase.

## 2. The result set is capped and the truncation flag is unreliable

A search has a maximum number of results, and at that cap the "there is more" flag may still read
false — a truncated set then looks complete. **Partition instead of trusting it**: when a result
approaches the cap, re-run split by type prefix, by directory, or by alphabetical segment, so each
sub-query stays well under the limit. The set is complete only when every partition is.

## 3. A scripted batch path can return empty where a direct call succeeds

Single observation, 2026-09, one server build: when several queries are issued through one
scripted/batched call, an empty result from that path was not evidence — the same query issued
directly returned results. **Re-run any empty answer from a batch path as a direct call** before
believing it. Treat it as a suspicion to re-test, not as a tool invariant; this deployment's
measurement belongs in the skill's `local/` overlay (machine-local values), not here.

Exact caps, flag names and path-filter syntax are properties of a particular server build — treat
them as deployment values, not as tool invariants.

## 4. The tool follows the question

Measured 2026-11 on one IDE build and tree, same queries:

| the question | the tool | the cost |
|---|---|---|
| where is this symbol/type/function declared or defined | `search_symbol` | 3-4 s, one hit per file |
| where does this literal, comment or config key appear | `search_text`, bounded by `--paths` | reached its 10 s timeout and returned a partial result |

A `search_text` that times out is a signal to narrow the paths or to switch to the symbol search,
never to repeat the same query; and neither replaces a structural query (`lint_files`,
`get_file_problems`) or a whole-file read.

## 5. Exemptions (moved from SKILL.md to keep the always-loaded card small)

The ban is on unbounded recursive content search, not on reading or filtering: pipe filtering
(`git show <file> | grep`, `git log --grep=...`), a single named file, a bounded directory, a log tail;
build or cleanup commands whose paths are explicit. Rider MCP refuses paths outside its solution root,
so a bounded read there is the documented fallback, not a scanner. Counts and sizes may come from a
bounded script over an **explicit path list** — never a scan from a drive root or home directory — and
the substitution used is stated, so the evidence's origin stays visible.
