---
name: rem-no-disk-scanning
description: >
  Disk text search (rg, grep, find, ripgrep, findstr) is banned; search goes
  through the project's MCP server (Rider MCP). Use whenever you search files.
metadata:
  category: meta
  trigger: always
---

# No Disk Scanning

**Disk-scanning text searchers — `rg`, `grep`, `find`, `fd`, `ripgrep`,
`findstr`, any editor "search in files" — are banned.** They are unbounded recursive content
searches, removed from the agent toolsets by configuration; never invoke one, through a tool or a shell.

Use **Rider MCP** only: `search_symbol` / find-usages first, then a bounded
`search_text` / `search_regex` / `search_file` (`maxResults` + a path or glob);
`get_file_problems` for diagnostics. Empty results, over-escaping and result
caps are traps — `references/search-mechanics.md`. Command map:
`ue-code-authoring` ("Tool split" table); degraded-mode notes: `ue-live-debugging`.
The tool follows the question, and a text search that times out is a signal to narrow, not to retry;
measured costs and the choice table live in `references/search-mechanics.md` §4.

## When Rider MCP is unavailable

Rider MCP unavailable, or a search you cannot bound → stop: a subagent
reports `rider-unavailable`, the main session tells the user. Never fall back to
a scanner.

## Exemptions

Reading or filtering one named file, a bounded directory or a log tail is not a scan, and a count may
come from a bounded script over an explicit path list — the full list: `references/search-mechanics.md` §5.
