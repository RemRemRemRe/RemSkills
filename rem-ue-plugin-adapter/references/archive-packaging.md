# Archive Packaging

Detail moved out of `SKILL.md` so the rules stay scannable.

> **Trigger**: this step is **manual and requires explicit user authorization**.
> The AI never runs packaging on its own — it proposes the commands and the user
> approves or executes them. Packaging creates **encrypted** 7z archives with a
> random password; the password must never be written into git, logs, or skill
> files.

### 8.1 Prerequisites

| Item | Check |
|------|-------|
| All versions built & packaged | Output dir exists for every target version: `{output_path}/{platform}/{version}/{PluginName}/` |
| 7-Zip | `7z.exe` location (machine-specific, e.g. `<7zip-install-dir>/7z.exe` — ask the user) |
| `VersionName` | Read from `.uplugin` (e.g. `4.1.0`) — used in the archive name |

### 8.2 Generate a strong random password

```powershell
powershell -NoProfile -Command "$a='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#%^*-_=+'; $r=[System.Security.Cryptography.RandomNumberGenerator]::Create(); $c=New-Object char[] 28; for($i=0;$i -lt 28;$i++){ $b=New-Object byte[] 1; $r.GetBytes($b); $c[$i]=$a[$b[0] % $a.Length] }; -join $c"
```

28 chars, mixed case + digits + symbols, excludes ambiguous chars (`0/O/1/l/I`).
Hand the password to the user for safekeeping; never commit it.

### 8.3 Create one archive per engine version

**Format preference: `.7z` ONLY** — no zip. The reason: 7z supports
**header encryption (`-mhe=on`)** — the file/directory listing is encrypted,
so nothing is visible before decryption. zip cannot hide file names at all
(Fab confirmed `.7z` is accepted; encrypted archives are fine).

For each target version `X.Y` (e.g. `5.3`, `5.8`), run from the plugin's
**output** directory (not the source repo):

```bash
cd {output_path}/{platform}/{version}/{PluginName}
<7z> a -t7z -mhe=on -p"<PASSWORD>" "{output_path}/{platform}/{PluginName}{X}{Y}.{ArchiveVersion}.7z" \
    Config Source LICENSE-ALS-Refactored {PluginName}.uplugin
```

- `-mhe=on` — encrypts the archive header: file/dir names are **not visible
  before decryption** (7z-only feature; zip cannot hide names)
- Add **only** `Config`, `Source`, `LICENSE-ALS-Refactored`, `{PluginName}.uplugin`
  — never `Binaries`/`Intermediate` (source-only packages are accepted)
- **Archive naming (by design)**: `{PluginName}{Major}{Minor}.{ArchiveVersion}.7z` —
  the filename version (`ArchiveVersion`) is an **internal round counter for the
author only** (4.1.0 → 4.1.1 → 4.1.2 … per packaging round). It is intentionally
  decoupled from the `.uplugin` `VersionName` (the user-facing plugin version,
  bumped only on release boundaries) — a new package round does NOT change the
  version users see. Example: `FooPlugin58.4.1.2.7z` for round 3 of FooPlugin 5.8
  whose `VersionName` is still 4.1.1. Sync them only when there is a real
  reason — **feature changes** shipped to users (new/changed functionality):
  bump `VersionName` then (new release). Pure fixes and packaging-only rounds
  keep `VersionName` unchanged — the filename round counter tracks those

### 8.4 Verify

```bash
# Without password: must fail or prompt for password (proves header encryption)
<7z> l {archive}.7z

# With password: top-level entries must be exactly the 4 expected items
<7z> l -p"<PASSWORD>" {archive}.7z
```

Check the top-level entries are only `Config`, `Source`,
`LICENSE-ALS-Refactored`, `{PluginName}.uplugin`, and that no
`Binaries`/`Intermediate` paths appear anywhere in the listing.

### 8.5 Quick patching without rebuild (export → modify → import)

For **small, surgical fixes** to files already inside the archives (e.g. adding
`PlatformAllowList` to `.uplugin` modules, fixing a single source file) when a
full rebuild is NOT required — e.g. the fix is metadata-only, or the target
platform's binaries are unaffected. Requires user authorization like Step 5
itself.

**Rule: always work from the file INSIDE the archive, never overwrite with the
working-tree copy.** Each archive holds the source snapshot of its version's
adaptation endpoint, which may differ from the current working tree (later
version-boundary changes). Overwriting with working-tree files silently mixes
versions into the archive.

```bash
# 1. Export the file(s) from the archive (keep the archive-relative path)
<7z> x -p"<PASSWORD>" -o<tmp-dir> {archive}.7z <archive-relative-path>

# 2. Modify <tmp-dir>/<path> (preserve formatting/line endings where possible)

# 3. Re-import: run 7z from INSIDE <tmp-dir> so the path matches the archive
cd <tmp-dir>
<7z> a -t7z -mhe=on -p"<PASSWORD>" {archive}.7z <archive-relative-path>
```

- Always re-pass `-p` and `-mhe=on` — the archive keeps its header encryption
- Run the `a` command from the directory that mirrors the archive layout, so
  the added path replaces the existing entry instead of adding a new one
- **`7z a` NEVER removes entries that no longer exist in the source** — if the
  fix REMOVES files (e.g. deleting a ThirdParty subdir), `a` keeps the stale
  entries. Delete the old archive first and rebuild from scratch:
  `rm {archive}.7z && <7z> a -t7z -mhe=on -p"<PASSWORD>" {archive}.7z <items...>`
- Verify afterwards: re-export the patched file and diff it, confirm the JSON
  is still valid (for `.uplugin`), confirm passwordless `7z l` still fails, and
  grep the listing to confirm removed paths are actually gone

### 8.6 Fab (marketplace) submission requirements

Fab review enforces a few package-level rules. Check them before uploading
(they are NOT caught by compiling):

| Requirement | Detail |
|-------------|--------|
| Archive format | **`.7z` only** — accepted by Fab after clarification; header-encrypted (`-mhe=on`) with a strong password. No zip needed |
| `PlatformAllowList` / `PlatformDenyList` | EVERY module in the `.uplugin` must carry one, matching `SupportedTargetPlatforms` (Fab errors: "No platform properties found") |
| ThirdParty content | Embedded third-party libs must keep ONLY their `include/` — src/test/doc/support/CI files get rejected (real case: `Source/ThirdParty/fmt/`) |
| No executables/installers | `.exe/.iso/.dmg` etc. are rejected (obvious, but check ThirdParty trees) |
| Binaries in the archive | Not required — source-only archives are accepted (Binaries stay in the build output dir, not in the package) |
| Version bump | Increment `VersionName` for every resubmission round (e.g. 4.1.0 → 4.1.1); commit it early (right after the first version boundary) so every endpoint contains it |

Build-farm note: Fab builds with the engine's **preferred MSVC toolchain**
(e.g. 14.38 for 5.5), which may differ from the toolchain local verification
used (e.g. 14.51). Verify with the preferred toolchain or keep compiler-
sensitive settings (shadow warnings, C# syntax) at their lowest common
denominator to avoid farm-only failures.

---
