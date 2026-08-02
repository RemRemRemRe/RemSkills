#!/usr/bin/env python3
"""
build_plugin.py — Multi-engine UE plugin build executor
========================================================
Builds a UE plugin for one or multiple engine versions using RunUAT BuildPlugin.

Usage:
    python build_plugin.py -n MyPlugin -v 5.8
    python build_plugin.py -n MyPlugin -v 5.7 5.8 --output-path "E:/Built"

Output structure:
    {output_path}/{platform}/{engine_version}/{plugin_name}/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════

def die(msg: str, code: int = 1) -> None:
    print(f"\n[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def write_build_log(logs_dir: Path, plugin_name: str, version: str,
                    stdout: str, stderr: str, returncode: int) -> Path:
    """Write a per-build log file. Returns the log path."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = logs_dir / "build"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{plugin_name}_{version}_{ts}.log"

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"===== Build log: {plugin_name} × UE {version} =====\n")
        f.write(f"Timestamp: {ts}\n")
        f.write(f"Exit code: {returncode}\n")
        f.write("=" * 60 + "\n")
        f.write("STDOUT:\n")
        f.write(stdout)
        f.write("\n" + "=" * 60 + "\n")
        f.write("STDERR:\n")
        f.write(stderr)
        f.write("\n" + "=" * 60 + "\n")

    return log_file


def write_operation_log(logs_dir: Path, plugin_name: str, version: str,
                        message: str) -> Path:
    """Append a line to the operation log. Returns the log path."""
    op_dir = logs_dir / "operation"
    op_dir.mkdir(parents=True, exist_ok=True)
    log_file = op_dir / f"{plugin_name}_{version}.log"

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")

    return log_file


def resolve_logs_dir(cfg: Dict[str, Any]) -> Optional[Path]:
    """Resolve the logs directory from config. None if not configured."""
    logs = cfg.get("logs", {})
    if isinstance(logs, dict):
        logs = {k: v for k, v in logs.items() if not k.startswith("_")}
        d = logs.get("dir")
        if d:
            return Path(d)
    return None


# ═══════════════════════════════════════════════════════════════════
#  Config
# ═══════════════════════════════════════════════════════════════════

def load_engine_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        die(f"Config not found: {config_path}\n"
            f"  Create engines.json (see README.md for format).")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def load_plugin_config(config_path: Path, plugin_name: str) -> Dict[str, Any]:
    """
    Load a per-plugin local.json and verify it belongs to the requested plugin.

    The skill itself holds no machine/project data: every plugin has its own
    config file OUTSIDE the skill (e.g. <config-dir>/<Plugin>/local.json),
    passed explicitly via --config. The plugin config references the
    machine-level engines config via its 'engines_config' field.
    """
    if not config_path.exists():
        die(f"Plugin config not found: {config_path}\n"
            f"  Every plugin needs its own local.json OUTSIDE the skill.\n"
            f"  Create one first (see tools/README.md → 'First-time setup').\n"
            f"  Example: python build_plugin.py -n {plugin_name} "
            f"--config <config-dir>/{plugin_name}/local.json")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg_plugin = cfg.get("plugin", {})
    cfg_name = cfg_plugin.get("name")
    if not cfg_name:
        die(f"Plugin config has no 'plugin.name': {config_path}")
    if cfg_name != plugin_name:
        die(f"Config mismatch: {config_path} is for plugin '{cfg_name}', "
            f"but -n was '{plugin_name}'.\n"
            f"  Pass --config <path-to-{plugin_name}/local.json>.")
    return cfg


def resolve_run_uat(engine_root: Path, version: str) -> Path:
    """Find RunUAT.bat (Win) or RunUAT.sh (Unix)."""
    base = engine_root / "Engine" / "Build" / "BatchFiles"
    if sys.platform == "win32":
        path = base / "RunUAT.bat"
    else:
        path = base / "RunUAT.sh"

    if not path.exists():
        die(
            f"RunUAT not found for UE {version}\n"
            f"  Expected: {path}\n"
            f"  Engine root: {engine_root}\n"
            f"  Check engines.json → engines.{version}.root"
        )
    return path


def resolve_uplugin(plugin_path: Path, plugin_name: str) -> Path:
    """Find the .uplugin file."""
    path = plugin_path / plugin_name / f"{plugin_name}.uplugin"
    if not path.exists():
        die(
            f".uplugin not found: {path}\n"
            f"  Check --plugin-name and --plugin-path"
        )
    return path


# ═══════════════════════════════════════════════════════════════════
#  Build
# ═══════════════════════════════════════════════════════════════════

def run_build(
    run_uat: Path,
    uplugin: Path,
    package_dir: Path,
    platform: str,
) -> Tuple[int, str, str]:
    """
    Execute RunUAT BuildPlugin.
    Returns (exit_code, stdout, stderr).
    """
    cmd = [
        str(run_uat),
        "BuildPlugin",
        f"-plugin={uplugin}",
        f"-package={package_dir}",
        f"-TargetPlatforms={platform}",
    ]

    print(f"  CMD: RunUAT BuildPlugin -plugin=\"{uplugin}\" "
          f"-package=\"{package_dir}\" -TargetPlatforms={platform}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════

HEADER = "=" * 64
SEP   = "-" * 64


def main() -> None:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="build_plugin",
        description="Build a UE plugin for one or multiple engine versions.",
    )
    parser.add_argument(
        "-c", "--config", required=True,
        help="Path to the PLUGIN's local.json (outside the skill, e.g. "
             "<config-dir>/<Plugin>/local.json). Required — the skill holds "
             "no machine/project data.",
    )
    parser.add_argument(
        "-n", "--plugin-name", required=True,
        help="Plugin name (e.g., 'MyPlugin')",
    )
    parser.add_argument(
        "-v", "--versions", nargs="+", metavar="VER",
        help="Engine versions (e.g., 5.7 5.8). Default: all configured.",
    )
    parser.add_argument(
        "--plugin-path",
        help="Plugin source root (overrides config default)",
    )
    parser.add_argument(
        "--output-path",
        help="Output root (overrides config default)",
    )
    parser.add_argument(
        "--platform",
        help="Target platform (overrides config default)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan, skip builds",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress extra output",
    )

    args = parser.parse_args()

    # ── Load config (required) ────────────────────────────────
    # --config must point to the PLUGIN's local.json, which lives OUTSIDE the
    # skill (e.g. <config-dir>/<Plugin>/local.json). It references the
    # machine-level engines config via "engines_config".
    config_path = Path(args.config)
    cfg = load_plugin_config(config_path, args.plugin_name)

    engines_cfg_path = Path(cfg.get("engines_config", ""))
    if not engines_cfg_path.is_absolute():
        engines_cfg_path = config_path.parent / engines_cfg_path
    if not engines_cfg_path.exists():
        die(f"Engines config not found: {engines_cfg_path}\n"
            f"  Set 'engines_config' in {config_path}")
    engines_cfg = load_engine_config(engines_cfg_path)

    engines: Dict[str, dict] = engines_cfg["engines"]
    # Ignore comment keys (e.g., "_comment_engine") in the engines map
    engines = {k: v for k, v in engines.items() if not k.startswith("_")}

    plugin_cfg: dict = cfg.get("plugin", {})
    defaults: dict = {
        "plugin_path": plugin_cfg.get("plugin_path", "."),
        "output_path": plugin_cfg.get("output_path", "."),
        "platform": plugin_cfg.get("platform", "Win64"),
    }
    logs_dir = resolve_logs_dir(cfg)
    if logs_dir:
        print(f"[INFO] Logs dir: {logs_dir}")

    # ── Determine versions ─────────────────────────────────────
    if args.versions:
        requested = [v.strip() for v in args.versions]
        missing = [v for v in requested if v not in engines]
        if missing:
            die(
                f"Version(s) not in config: {', '.join(missing)}\n"
                f"  Available: {', '.join(sorted(engines.keys()))}\n"
                f"  Config:    {config_path}"
            )
        versions = requested
    else:
        versions = sorted(engines.keys())
        info(f"No --versions given; building all: {', '.join(versions)}")

    # ── Resolve paths ──────────────────────────────────────────
    plugin_path = Path(args.plugin_path or defaults.get("plugin_path", "."))
    output_path = Path(args.output_path or defaults.get("output_path", "."))
    platform    = args.platform or defaults.get("platform", "Win64")
    plugin_name = args.plugin_name

    uplugin = resolve_uplugin(plugin_path, plugin_name)

    # ── Print plan ─────────────────────────────────────────────
    print(HEADER)
    print(f"  Plugin:         {plugin_name}")
    print(f"  Source:         {uplugin}")
    print(f"  Versions:       {', '.join(versions)}")
    print(f"  Platform:       {platform}")
    print(f"  Output base:    {output_path}")
    print(f"  Config:         {config_path}")
    print(HEADER)

    # ── Build ──────────────────────────────────────────────────
    results: Dict[str, int] = {}

    for version in versions:
        eng = engines[version]
        engine_root = Path(eng["root"])
        engine_type = eng.get("type", "?")
        run_uat = resolve_run_uat(engine_root, version)
        package_dir = output_path / platform / version / plugin_name

        print(f"\n{HEADER}")
        print(f"  UE {version}  ({engine_type})")
        print(f"  Engine root:   {engine_root}")
        print(f"  RunUAT:        {run_uat}")
        print(f"  Package:       {package_dir}")
        print(SEP)

        if args.dry_run:
            print("  [DRY-RUN] Skipped")
            results[version] = 0
            continue

        package_dir.mkdir(parents=True, exist_ok=True)
        ret, stdout, stderr = run_build(run_uat, uplugin, package_dir, platform)
        results[version] = ret

        # ── Write logs for human review ────────────────────────
        if logs_dir:
            build_log = write_build_log(logs_dir, plugin_name, version,
                                        stdout, stderr, ret)
            write_operation_log(logs_dir, plugin_name, version,
                                f"Build UE {version}: {'PASS' if ret == 0 else f'FAIL ({ret})'} — log: {build_log.name}")
            print(f"  [LOG] Build log: {build_log}")

        if ret == 0:
            print(f"  [PASS] UE {version}")
        else:
            print(f"  [FAIL] UE {version} — exit code {ret}")
            if stderr and not args.quiet:
                # Print last 40 lines of error output
                lines = stderr.strip().splitlines()
                print(f"  --- last {min(40, len(lines))} lines of stderr ---")
                for line in lines[-40:]:
                    print(f"  | {line}")

    # ── Summary ────────────────────────────────────────────────
    print(f"\n{HEADER}")
    print(f"  BUILD SUMMARY")
    print(HEADER)
    passed = sum(1 for r in results.values() if r == 0)
    failed = sum(1 for r in results.values() if r != 0)
    for v in versions:
        r = results.get(v, -1)
        print(f"  UE {v}:  {'PASS' if r == 0 else f'FAIL ({r})'}")
    print(f"\n  {passed} passed, {failed} failed, {len(versions)} total")
    print(HEADER)

    if logs_dir:
        write_operation_log(logs_dir, plugin_name, "all",
                            f"Build summary: {passed} passed, {failed} failed, {len(versions)} total")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
