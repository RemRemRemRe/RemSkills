# Plugin Adapter Tools

Multi-engine UE plugin build and adaptation toolchain. Called by the AI
during the adaptation workflow defined in `../SKILL.md`.

## Scripts

| Script | Purpose |
|--------|---------|
| `build_plugin.py` | Build a plugin for one or multiple UE engine versions |
| `build_loop.py` | Single-version build → fix → commit loop |
| `auto_fixer.py` | Parse build errors and match against known patterns |
| `adapter.py` | Full multi-version adaptation orchestrator (skeleton) |

## First-time setup (per machine + per plugin)

The skill itself holds **no machine or project data**. Before the first use:

1. **Machine-level engine config** — copy the template and fill in real paths:

   ```bash
   cp engines.json <config-dir>/engines.local.json      # <config-dir> = your external config dir
   ```

   ```json
   {
     "engines": {
       "5.8": { "root": "<source-engine-path>", "type": "source" },
       "5.7": { "root": "<binary-engine-path>/UE_5.7", "type": "binary" }
     }
   }
   ```

2. **Per-plugin config** — create `<config-dir>/<PluginName>/local.json`
   (one directory per plugin; see SKILL.md §10 for the full schema):

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
     "engines_config": "<config-dir>/engines.local.json",
     "dependencies": { "<DepA>": "<path-to-DepA-source>" },
     "upstream": { "remote": "upstream", "branch": "main" },
     "logs": { "dir": "<log-dir>" }
   }
   ```

3. **Adaptation notes** (optional but recommended) — keep plugin-specific
   knowledge (dependencies, disabled modules, known regressions, version
   boundaries) in `<config-dir>/<PluginName>/adaptation-notes.md`.

`--config` is **required** by the tools; they error out with usage hints when
it is missing, points to a nonexistent file, or its `plugin.name` does not
match `-n`.

## Quick Start

### 1. Dry-run validation

```bash
python build_plugin.py -n <plugin> --config "<config-dir>/<plugin>/local.json" -v 5.8 --dry-run
```

### 2. Single-version build

```bash
python build_plugin.py -n <plugin> --config "<config-dir>/<plugin>/local.json" -v 5.8
build58.bat   # edit the CONFIG variable inside the .bat first
```

### 3. Build-fix loop (single version)

```bash
python build_loop.py -n <plugin> -v 5.7 -p "<build-repo>" --config "<config-dir>/<plugin>/local.json"
```

Loops: build → parse errors → apply known fixes → git commit → rebuild,
until the build passes or manual intervention is needed.

### 4. Full multi-version adaptation (in development)

```bash
python adapter.py -n <plugin> -r "<build-repo>" -v 5.8 5.7 5.6 5.5 5.4 5.3
```

## Configuration Files

| File | Purpose | Location |
|------|---------|----------|
| `engines.json` | Engine version paths template (source/binary) | skill `tools/` (template only) |
| `engines.local.json` | Real machine engine paths | external, e.g. `<config-dir>/` |
| `<Plugin>/local.json` | Per-plugin config (required by `--config`) | external, e.g. `<config-dir>/<Plugin>/` |
| `<Plugin>/adaptation-notes.md` | Per-plugin knowledge/decisions | external, same dir |
| `fix_rules.json` | Known error → fix pattern mappings | skill `tools/` (generic) |

## Requirements

- Python 3.8+ (stdlib only, no pip packages)
- Git (for `build_loop.py` auto-commit)
- Valid engines config with reachable engine paths
