---
name: rem-no-disk-scanning
description: Permanently forbid rg.exe (ripgrep), grep.exe (grep), fd.exe (fd) or simillar disk scanning/pure string searching tool for finding file or code symbol. Use Rider MCP text search tools instead. If Rider MCP unavailable, halt and report error.
---

# no-rg

**rg.exe (ripgrep), grep.exe (grep), fd.exe (fd) or simillar disk scanning/pure string searching tool are banned.** Never invoke it — not via Grep, not via bash, not directly. It hangs scanning entire drives.

**Always** use Rider MCP text search tools for content search.

If Rider MCP tools are unavailable, **stop immediately** and report the error. Do not fall back to rg.exe or any ripgrep variant.
