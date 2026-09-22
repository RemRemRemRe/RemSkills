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

When several queries are issued through one scripted/batched call, an empty result from that path is
not evidence: the same query issued directly can return results. **Re-run any empty answer from a
batch path as a direct call** before believing it.

Exact caps, flag names and path-filter syntax are properties of a particular server build — treat
them as deployment values, not as tool invariants.
