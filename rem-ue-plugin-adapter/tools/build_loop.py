#!/usr/bin/env python3
"""
build_loop.py — Single-version build → fix → commit loop
===========================================================
For one engine version, repeatedly:
  1. Build the plugin
  2. Parse errors
  3. Apply auto-fixes for known patterns
  4. Git commit each fix
  5. Repeat until build passes or no more auto-fixable errors

When auto-fixes are exhausted, the script reports remaining errors
and waits for manual intervention.

Usage:
    python build_loop.py -n MyPlugin -v 5.7 -p "<build-repo>"

    # With custom paths
    python build_loop.py -n MyPlugin -v 5.8 -p "<build-repo>" \
        --config engines.json --rules fix_rules.json

    # CI mode: exit immediately when manual fix needed
    python build_loop.py -n MyPlugin -v 5.7 -p "<build-repo>" --ci
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parent))
from auto_fixer import (
    BuildError, ErrorParser, FixRule, FixRuleLoader,
    FixResult, Fixer,
)
from build_plugin import (
    load_engine_config, load_plugin_config, resolve_run_uat, resolve_uplugin,
    run_build, write_build_log, write_operation_log, resolve_logs_dir,
)


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════

def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def git_cmd(repo: Path, *args: str) -> Tuple[int, str, str]:
    """Run a git command in the given repo directory."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def git_commit(repo: Path, message: str) -> bool:
    """Stage all changes and commit. Returns True on success."""
    git_cmd(repo, "add", "-A")
    ret, _, stderr = git_cmd(repo, "commit", "-m", message)
    if ret != 0:
        warn(f"Git commit failed: {stderr}")
        return False
    info(f"Committed: {message}")
    return True


def is_git_repo(path: Path) -> bool:
    ret, _, _ = git_cmd(path, "rev-parse", "--git-dir")
    return ret == 0


# ═══════════════════════════════════════════════════════════════════
#  Build loop state
# ═══════════════════════════════════════════════════════════════════

class BuildLoop:
    """Orchestrates the build→fix→commit cycle for a single engine version."""

    def __init__(
        self,
        plugin_name: str,
        engine_version: str,
        repo_path: Path,
        engine_root: Path,
        uplugin: Path,
        output_path: Path,
        platform: str,
        fixer: Fixer,
        *,
        ci_mode: bool = False,
        max_iterations: int = 20,
        quiet: bool = False,
        logs_dir: Optional[Path] = None,
    ):
        self.plugin_name   = plugin_name
        self.engine_version = engine_version
        self.repo_path     = repo_path
        self.engine_root   = engine_root
        self.uplugin       = uplugin
        self.output_path   = output_path
        self.platform      = platform
        self.fixer         = fixer
        self.ci_mode       = ci_mode
        self.max_iterations = max_iterations
        self.quiet         = quiet
        self.logs_dir      = logs_dir

        self.run_uat = resolve_run_uat(engine_root, engine_version)
        self.package_dir = output_path / platform / engine_version / plugin_name

        # Statistics
        self.iteration: int = 0
        self.total_fixes: int = 0
        self.auto_fixes: List[str] = []
        self.manual_fixes: List[str] = []

    # ────────────────────────────────────────────────────────────
    #  Logging
    # ────────────────────────────────────────────────────────────

    def _op_log(self, message: str) -> None:
        """Append to the per-version operation log if configured."""
        if self.logs_dir:
            write_operation_log(self.logs_dir, self.plugin_name,
                                self.engine_version, message)

    # ────────────────────────────────────────────────────────────
    #  Main loop
    # ────────────────────────────────────────────────────────────

    def run(self) -> bool:
        """
        Run the build loop. Returns True if build eventually passes.
        """
        print("=" * 64)
        print(f"  BUILD LOOP: {self.plugin_name} × UE {self.engine_version}")
        print("=" * 64)
        print(f"  Repo:      {self.repo_path}")
        print(f"  Engine:    {self.engine_root}")
        print(f"  .uplugin:  {self.uplugin}")
        print(f"  Package:   {self.package_dir}")
        print(f"  Iterations max: {self.max_iterations}")
        print("=" * 64)
        self._op_log(f"=== Build loop started: {self.plugin_name} × UE {self.engine_version} ===")

        while self.iteration < self.max_iterations:
            self.iteration += 1

            print(f"\n{'─' * 64}")
            print(f"  Iteration {self.iteration}/{self.max_iterations}")
            print(f"{'─' * 64}")
            self._op_log(f"Iteration {self.iteration} — building")

            # 1. Build
            ret, stdout, stderr = run_build(
                self.run_uat, self.uplugin, self.package_dir, self.platform
            )

            # Write full build log
            if self.logs_dir:
                build_log = write_build_log(self.logs_dir, self.plugin_name,
                                            f"{self.engine_version}_it{self.iteration}",
                                            stdout, stderr, ret)
                self._op_log(f"Build log: {build_log.name}")

            if ret == 0:
                print(f"\n  [OK] BUILD PASSED after {self.iteration} iteration(s)!")
                self._op_log(f"BUILD PASSED after {self.iteration} iteration(s)")
                self._print_summary()
                return True

            # 2. Parse errors
            combined_output = stdout + "\n" + stderr
            errors = ErrorParser.parse_output(combined_output)

            if not errors:
                warn("Build failed but no parseable errors found.")
                self._op_log(f"Iteration {self.iteration} — build failed, no parseable errors")
                self._print_raw_tail(stderr, 60)
                return False

            print(f"\n  Parsed {len(errors)} error(s):")
            for e in errors[:20]:
                print(f"    {e}")
            if len(errors) > 20:
                print(f"    ... and {len(errors) - 20} more")
            self._op_log(f"Iteration {self.iteration} — {len(errors)} error(s) parsed")

            # 3. Try auto-fix
            results = self.fixer.fix_errors(errors)

            if not results:
                print(f"\n  No auto-fixable errors. Manual intervention required.")
                if self.ci_mode:
                    print("  [CI MODE] Exiting.")
                    self._print_unmatched(errors)
                    return False
                return self._wait_for_manual(errors)

            # 4. Report fixes applied
            fixed_any = False
            for r in results:
                if r.success:
                    fixed_any = True
                    print(f"  ✓ Fixed: [{r.rule_id}] {r.file}: {r.description}")
                    self.auto_fixes.append(f"[{r.rule_id}] {r.description}")
                    self._op_log(f"Auto-fix applied: [{r.rule_id}] {r.file}: {r.description}")

                    # Commit each fix
                    if is_git_repo(self.repo_path):
                        msg = f"Fixed: {r.description}"
                        if r.note:
                            msg += f" (auto-fix, {r.note})"
                        committed = git_commit(self.repo_path, msg)
                        status = "ok" if committed else "failed"
                        self._op_log(f"Committed: {msg} ({status})")
                else:
                    print(f"  ✗ Failed: [{r.rule_id}] {r.file}: {r.description}")
                    self._op_log(f"Auto-fix failed: [{r.rule_id}] {r.file}: {r.description}")

            if fixed_any:
                self.total_fixes += sum(1 for r in results if r.success)
                continue  # Loop — rebuild with fixes applied

            # No successful fixes — need manual intervention
            print(f"\n  No fixes applied successfully. Manual intervention required.")
            if self.ci_mode:
                print("  [CI MODE] Exiting.")
                self._print_unmatched(errors)
                return False
            return self._wait_for_manual(errors)

        # Max iterations reached
        warn(f"Reached max iterations ({self.max_iterations}) without passing.")
        return False

    # ────────────────────────────────────────────────────────────
    #  Manual intervention
    # ────────────────────────────────────────────────────────────

    def _wait_for_manual(self, errors: List[BuildError]) -> bool:
        """Pause for manual fixes, then restart loop."""
        self._print_unmatched(errors)

        print(f"\n{'─' * 64}")
        print("  ACTION REQUIRED")
        print(f"{'─' * 64}")
        print(f"  Fix the errors above manually in:")
        print(f"    {self.repo_path}")
        print(f"")
        print(f"  After fixing, commit with:  git commit -m \"Fixed: <description>\"")
        print(f"  Then press ENTER to continue the build loop...")
        print(f"  Or type 'done' if you believe the build should now pass")
        print(f"  Or type 'quit' to stop")

        try:
            user_input = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Interrupted.")
            return False

        if user_input == "quit":
            return False

        # Record manual fix
        self.manual_fixes.append(f"Iteration {self.iteration}: manual fix")

        # Continue the loop
        print("  Resuming build loop...")
        return self.run()  # Recursive — restart loop

    # ────────────────────────────────────────────────────────────

    def _print_unmatched(self, errors: List[BuildError]) -> None:
        """Print errors that could not be auto-fixed."""
        unmatched = [e for e in errors if not self.fixer.matcher.find_match(e)]

        if not unmatched:
            print("  All errors matched rules but fixes failed to apply.")
            return

        print(f"\n  {len(unmatched)} UNMATCHED ERROR(S):")
        by_file = ErrorParser.group_by_file(unmatched)
        for file, file_errors in by_file.items():
            print(f"\n  ── {file}  ({len(file_errors)} errors) ──")
            for e in file_errors:
                print(f"    L{e.line}: {e.code} {e.message[:120]}")
                if e.symbol:
                    print(f"             symbol: '{e.symbol}'")

    def _print_raw_tail(self, text: str, n: int) -> None:
        """Print last N lines of raw output."""
        lines = text.strip().splitlines()
        print(f"\n  Last {min(n, len(lines))} lines of output:")
        for line in lines[-n:]:
            print(f"  | {line}")

    def _print_summary(self) -> None:
        print(f"\n{'=' * 64}")
        print(f"  BUILD LOOP SUMMARY")
        print(f"{'=' * 64}")
        print(f"  Iterations:    {self.iteration}")
        print(f"  Auto-fixes:    {len(self.auto_fixes)}")
        for fix in self.auto_fixes:
            print(f"    - {fix}")
        print(f"  Manual fixes:  {len(self.manual_fixes)}")
        print(f"{'=' * 64}")


# ═══════════════════════════════════════════════════════════════════
#  CLI entry point
# ═══════════════════════════════════════════════════════════════════

def main() -> None:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="build_loop",
        description="Build-fix-commit loop for a single UE engine version.",
    )
    parser.add_argument("-n", "--plugin-name", required=True,
                        help="Plugin name (e.g., MyPlugin)")
    parser.add_argument("-v", "--version", required=True,
                        help="Engine version (e.g., 5.7)")
    parser.add_argument("-p", "--repo-path", required=True,
                        help="Path to the build/git repo containing the plugin")
    parser.add_argument("-c", "--config", required=True,
                        help="Path to the PLUGIN's local.json (outside the skill). "
                             "Required — the skill holds no machine/project data.")
    parser.add_argument("-r", "--rules", default=str(script_dir / "fix_rules.json"),
                        help="Path to fix_rules.json")
    parser.add_argument("--output-path",
                        help="Override output root directory")
    parser.add_argument("--platform", default="Win64",
                        help="Target platform")
    parser.add_argument("--ci", action="store_true",
                        help="CI mode: exit immediately when manual intervention needed")
    parser.add_argument("--max-iterations", type=int, default=20,
                        help="Max build-fix iterations (default: 20)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress extra output")

    args = parser.parse_args()

    # Validate repo
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"[ERROR] Repo path does not exist: {repo_path}")
        sys.exit(1)
    if not is_git_repo(repo_path):
        print(f"[WARN] Not a git repository: {repo_path}")
        print(f"       Auto-commit will be disabled.")

    # Load plugin config (required) + referenced engines config
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path
    cfg = load_plugin_config(config_path, args.plugin_name)

    engines_cfg_path = Path(cfg.get("engines_config", ""))
    if not engines_cfg_path.is_absolute():
        engines_cfg_path = config_path.parent / engines_cfg_path
    if not engines_cfg_path.exists():
        print(f"[ERROR] Engines config not found: {engines_cfg_path}")
        print(f"        Set 'engines_config' in {config_path}")
        sys.exit(1)
    engines_cfg = load_engine_config(engines_cfg_path)

    engines = {k: v for k, v in engines_cfg["engines"].items() if not k.startswith("_")}
    if args.version not in engines:
        print(f"[ERROR] Version {args.version} not found in engines config")
        print(f"        Available: {', '.join(sorted(engines.keys()))}")
        sys.exit(1)

    engine_info = engines[args.version]
    engine_root = Path(engine_info["root"])
    plugin_cfg: dict = cfg.get("plugin", {})
    defaults = {
        "output_path": plugin_cfg.get("output_path", "."),
        "platform": plugin_cfg.get("platform", "Win64"),
    }
    logs_dir = resolve_logs_dir(cfg)
    if logs_dir:
        print(f"[INFO] Logs dir: {logs_dir}")

    # Resolve paths
    # NOTE: repo_path IS the plugin path in the build context
    # The .uplugin is at repo_path/<plugin_name>/<plugin_name>.uplugin
    uplugin = repo_path / args.plugin_name / f"{args.plugin_name}.uplugin"
    if not uplugin.exists():
        # Try repo_path as plugin path too (if repo IS the plugin dir)
        uplugin = repo_path / f"{args.plugin_name}.uplugin"
        if not uplugin.exists():
            print(f"[ERROR] .uplugin not found at {repo_path / args.plugin_name / f'{args.plugin_name}.uplugin'}")
            print(f"        or {repo_path / f'{args.plugin_name}.uplugin'}")
            sys.exit(1)

    output_path = Path(args.output_path or defaults.get("output_path", "."))
    platform = args.platform

    # Load fix rules
    rules_path = Path(args.rules)
    if not rules_path.is_absolute():
        rules_path = script_dir / rules_path
    rules = FixRuleLoader.load(rules_path)
    fixer = Fixer(rules)

    print(f"[INFO] Loaded {len(rules)} fix rule(s)")

    # Run loop
    loop = BuildLoop(
        plugin_name=args.plugin_name,
        engine_version=args.version,
        repo_path=repo_path,
        engine_root=engine_root,
        uplugin=uplugin,
        output_path=output_path,
        platform=platform,
        fixer=fixer,
        ci_mode=args.ci,
        max_iterations=args.max_iterations,
        quiet=args.quiet,
        logs_dir=logs_dir,
    )

    success = loop.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
