---
name: rem-no-disk-scanning
description: >
  Bans disk-scanning text searchers (rg, grep, find, fd, ripgrep, findstr and any
  editor "search in files" equivalent) - they walk entire trees and hang - and
  requires search through the project's MCP server (Rider MCP) instead. The tools
  are removed from the project's agent toolsets by configuration, so their absence
  is expected. Use this constraint in every session, not on demand.
metadata:
  category: meta
  trigger: always
---

# No Disk Scanning

**Disk-scanning text searchers — `rg`, `grep`, `find`, `fd`, `ripgrep`,
`findstr`, and any editor "search in files" equivalent — are banned.** They are
unbounded recursive content searches over huge trees, and are removed from the
agent toolsets by configuration, so their absence is expected. Never invoke
them — not through a tool, not through a shell.

Use **Rider MCP** only: `search_symbol` / find-usages first, then a bounded
`search_text` / `search_regex` / `search_file` (`maxResults` + a path or glob);
`get_file_problems` for diagnostics. Command map: `ue-code-authoring` ("Tool
split" table); degraded-mode notes: `ue-live-debugging`.

## When Rider MCP is unavailable

Rider MCP unavailable, or a search you cannot bound → stop: a subagent
reports `rider-unavailable`, the main session tells the user. Never fall back to
a scanner.

## Exemptions

The ban is on unbounded recursive content search, not on reading or filtering:
text filtering in a pipe (`git show <file> | grep`, `git log --grep=...`), a
single named file, a bounded directory, or a log tail; build or cleanup commands
whose paths are explicit.

## Aggregates (main session)

Counts and sizes may come from a bounded script over an **explicit path list**
— never a scan from a drive root or home directory. Say which substitution was
used, so the reader knows the evidence came from a targeted read. The description
states the ban itself — it is in context every session.
