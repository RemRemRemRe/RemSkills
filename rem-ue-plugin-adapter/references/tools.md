# Tool Reference

Detail moved out of `SKILL.md` so the rules stay scannable.

---

### Scripts

| Script | Purpose |
|--------|---------|
| `build_plugin.py` | Build a plugin for one or more UE engine versions |
| `build_loop.py` | Single-version build → fix → commit loop |
| `auto_fixer.py` | Parse build errors and match them against known patterns |
| `adapter.py` | Full multi-version adaptation orchestrator (skeleton) |

### First-time setup (per machine + per plugin)

The skill itself holds **no machine or project data**. Before the first use:

1. **Machine-level engine config** — copy the template and fill in real paths:
   `cp <skill-dir>/tools/engines.json <config-dir>/engines.local.json`
   (see "engines.json (shared template)" below for the fields).
2. **Per-plugin config** — create `<config-dir>/<PluginName>/local.json`
   (see "Plugin local.json" below for the schema).
3. **Adaptation notes** (optional, recommended) — keep plugin-specific
   knowledge (dependencies, disabled modules, known regressions, version
   boundaries) in `<config-dir>/<PluginName>/adaptation-notes.md`.

`--config` is **required** by the tools; they error out with usage hints when
it is missing, points to a nonexistent file, or its `plugin.name` does not
match `-n`.

### build_plugin.py

```
python <skill-dir>/tools/build_plugin.py \
  -n <plugin-name>          # required; must match config's plugin.name
  -v <version> [<v2> ...]   # engine version(s); default: all in engines config
  --plugin-path <path>       # override default plugin source dir
  --output-path <path>       # override default output dir
  --config <path>            # REQUIRED: path to the plugin's external local.json
  --dry-run                  # validate paths, skip build
  -q                         # suppress extra output
```

`--config` is **required** — the skill holds no machine/project data. If it
is missing, points to a nonexistent file, or its `plugin.name` does not match
`-n`, the tool errors out with usage hints.

### External config layout (skill stays clean)

The skill directory only contains generic workflow + generic engine knowledge.
All per-plugin data lives **outside** the skill, in a machine-specific config
dir (e.g. `<config-dir>/`):

```
PluginAdapterConfig/   # example name for the external config dir
├── engines.local.json          # machine-level engine paths (shared by all plugins)
└── <PluginName>/               # one directory per external plugin
    ├── local.json              # plugin config (required by --config)
    └── adaptation-notes.md     # plugin-specific knowledge/decisions (read+update each cycle)
```

### Plugin local.json (external, required)

```json
{
  "plugin": {
    "name": "<PluginName>",
    "plugin_path": "<parent-dir-containing-plugin>",
    "output_path": "<output-dir>",
    "platform": "Win64",
    "build_repo": "<path-to-build-repo>",
    "plugin_version": ""
  },
  "engines_config": "<abs-path-to-engines.local.json>",
  "dependencies": {
    "<DepA>": "<path-to-DepA-source>",
    "<DepB>": "<path-to-DepB-source>"
  },
  "upstream": { "remote": "<upstream-remote-name>", "branch": "<upstream-branch>" },
  "logs": { "dir": "<log-dir>" }
}
```

- **plugin.name**: must equal `-n`; mismatch → tool errors out
- **engines_config**: absolute path to the machine-level engines config
- **dependencies**: map of embedded dependency name → its source directory
  (machine-specific paths)
- **plugin_version**: one-shot version bump for this adaptation run (full
  semver, e.g. `"4.1.0"`). Written into `.uplugin` VersionName at the first
  version boundary commit; cleared after the full adaptation completes.
  Empty normally.
- **logs.dir**: where build/operation logs are written for human review

### engines.json (shared template)

`<skill-dir>/tools/engines.json` is the **machine-level shared template** with
placeholder paths. Copy it to the external config dir as `engines.local.json`
and fill in real paths (referenced from the plugin config via
`engines_config`). The template itself contains no personal paths.

```json
{
  "engines": {
    "5.8": { "root": "<source-engine-path>", "type": "source" },
    "5.7": { "root": "<binary-engine-path>/UE_5.7", "type": "binary" }
  }
}
```

- **root**: directory containing `Engine/` subfolder
- **type**: `"source"` (built from source) or `"binary"` (Epic official build)

Pass the plugin config explicitly:

```bash
python <skill-dir>/tools/build_plugin.py -n <plugin> \
  --config "<config-dir>/<plugin>/local.json" -v 5.8
```

### Log files

When `logs.dir` is configured, tools write logs for human review:

| Log | Path | Content |
|-----|------|---------|
| Build log | `{logs.dir}/build/{plugin}_{version}_{timestamp}.log` | Full stdout + stderr of each build invocation |
| Operation log | `{logs.dir}/operation/{plugin}_{version}.log` | Append-only timeline: builds, auto-fixes, commits, manual interventions |

Review the operation log to understand what the adaptation did; inspect
build logs for the full error output of any failing build.

> The `.bat` wrappers in `tools/` already pass `--config` — edit the `CONFIG`
> variable at the top to point to your local file.

### Error parsing script (optional)

For parsing build logs programmatically:

```bash
python <skill-dir>/tools/auto_fixer.py --log build.log --rules <skill-dir>/tools/fix_rules.json
```

This extracts structured errors but does **not** apply fixes automatically.
Use it to quickly identify error locations and match against known patterns.

### build_loop.py

```bash
python <skill-dir>/tools/build_loop.py -n <plugin> -v <version> -p "<build-repo>" \
  --config "<config-dir>/<plugin>/local.json"
```

Loops build → parse errors → apply known fixes → commit → rebuild until the
build passes or manual intervention is needed. It auto-commits in the build
repo (the generated tree — see the adapter's commit step for why staging
wholesale is safe there).

### adapter.py

```bash
python <skill-dir>/tools/adapter.py -n <plugin> -r "<build-repo>" -v 5.8 5.7 5.6 5.5 5.4 5.3
```

Full multi-version orchestration. It is a **skeleton** — the multi-version
driver is still in development; the per-version loop above is the working path.

### Quick start

```bash
# 1. validate paths without building
python <skill-dir>/tools/build_plugin.py -n <plugin> --config "<config-dir>/<plugin>/local.json" -v 5.8 --dry-run

# 2. build one version
python <skill-dir>/tools/build_plugin.py -n <plugin> --config "<config-dir>/<plugin>/local.json" -v 5.8

# 3. single-version build-fix loop (the .bat wrappers call build_plugin.py; edit CONFIG inside first)
python <skill-dir>/tools/build_loop.py -n <plugin> -v 5.7 -p "<build-repo>" --config "<config-dir>/<plugin>/local.json"
```

### Requirements

- Python 3.8+ (stdlib only, no pip packages)
- Git (for `build_loop.py`'s auto-commit)
- A valid engines config with reachable engine paths

---
