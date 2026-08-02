---
name: rem-no-disk-scanning
description: >
  Bans disk-scanning tools (rg.exe, grep.exe, fd.exe and similar pure string
  searchers) — they hang scanning entire drives — and requires Rider MCP text
  search instead, with a bounded fallback when Rider MCP is unavailable. Use
  this constraint in every session, not on demand.
metadata:
  category: meta
  trigger: always
---

# No Disk Scanning

**`rg.exe`, `grep.exe`, `fd.exe` and similar disk-scanning / pure string
searching tools are banned.** Never invoke them — not through a Grep tool, not
through a shell, not directly. They walk entire drives and hang.

The description above states the ban itself, not just a pointer to this file:
it is the only surface guaranteed to be in context every session, so an agent
that never loads this file must still know those tools are banned. The fallback
detail below is deliberately not duplicated there.

**Use Rider MCP text search** (symbol lookup, find usages, text search) for
content search.

## When Rider MCP is unavailable

Do not halt, and do not fall back to a banned scanner. In order of preference:

1. Read the files you already know are relevant.
2. For an aggregate question (counts, sizes, cross-references), run a bounded
   script over an **explicit path list** — never a recursive scan from a drive
   root or a home directory.
3. Say which substitution you used, so the reader knows the evidence came from
   a targeted read rather than a full search.

The ban is on unbounded scanning, not on reading files.
