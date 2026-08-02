#!/usr/bin/env python3
"""
adapter.py — Full multi-engine plugin adaptation orchestrator
===============================================================
Automates the complete adaptation workflow for UE 5.3–5.8:
  1. Branch management (rename old branch, checkout upstream)
  2. Embed dependent plugins
  3. Cascade down: cherry-pick → build → fix → commit → next version

Status: SKELETON — build_loop.py handles the core step (3d).
         Full orchestration is a work in progress; use the individual
         scripts for now.

Planned usage:
    python adapter.py -n MyPlugin -r "<build-repo>" \\
        --versions 5.8 5.7 5.6 5.5 5.4 5.3 \\
        --upstream upstream --old-branch old-20260728
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def die(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


# ═══════════════════════════════════════════════════════════════════
#  Git helpers
# ═══════════════════════════════════════════════════════════════════

def git(repo: Path, *args: str) -> Tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def git_or_die(repo: Path, *args: str) -> str:
    ret, out, err = git(repo, *args)
    if ret != 0:
        die(f"git {' '.join(args)} failed: {err}")
    return out


# ═══════════════════════════════════════════════════════════════════
#  Adapter steps
# ═══════════════════════════════════════════════════════════════════

class AdapterConfig:
    """Configuration for a full adaptation run."""
    def __init__(self, config_path: Path):
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
        else:
            data = {}
        self.data = data

    @property
    def dependencies(self) -> List[dict]:
        """List of dependent plugins to embed."""
        return self.data.get("dependencies", [])

    @property
    def cherry_pick_ranges(self) -> dict:
        """SHA1 ranges for cherry-picks per version."""
        return self.data.get("cherry_pick_ranges", {})


class Adapter:
    """Full multi-engine plugin adaptation orchestrator."""

    def __init__(
        self,
        plugin_name: str,
        repo_path: Path,
        versions: List[str],
        upstream_remote: str = "upstream",
        old_branch: Optional[str] = None,
        config: Optional[AdapterConfig] = None,
    ):
        self.plugin_name     = plugin_name
        self.repo_path       = Path(repo_path).resolve()
        self.versions        = versions  # sorted high→low
        self.upstream_remote = upstream_remote
        self.old_branch      = old_branch
        self.config          = config or AdapterConfig(self.repo_path / "adapt_config.json")

    # ── Step 1: Branch management ────────────────────────────

    def step1_branch_setup(self, dry_run: bool = False) -> None:
        """
        Rename current branch to old_*, checkout upstream/main,
        create new adapt branch.
        """
        print("\n" + "=" * 64)
        print("  STEP 1: Branch Setup")
        print("=" * 64)

        # Get current branch name
        ret, current_branch, _ = git(self.repo_path, "rev-parse", "--abbrev-ref", "HEAD")
        if ret != 0:
            die("Could not determine current branch.")

        # Rename
        old_name = self.old_branch or f"old-{current_branch}"
        print(f"  Current branch: {current_branch}")
        print(f"  Renaming to:    {old_name}")

        if not dry_run:
            git_or_die(self.repo_path, "branch", "-m", old_name)

        # Fetch upstream
        print(f"  Fetching {self.upstream_remote}...")
        if not dry_run:
            git_or_die(self.repo_path, "fetch", self.upstream_remote)

        # Create new branch
        new_branch = f"adapt-{self.versions[-1]}-to-{self.versions[0]}"
        print(f"  Creating branch: {new_branch} from {self.upstream_remote}/main")

        if not dry_run:
            git_or_die(self.repo_path, "checkout", "-b", new_branch,
                        f"{self.upstream_remote}/main")

        info(f"Branch setup complete. New branch: {new_branch}")

    # ── Step 2: Embed dependencies ───────────────────────────

    def step2_embed_dependencies(self, dry_run: bool = False) -> None:
        """
        Copy dependent plugin source code into the plugin directory
        and remove external plugin dependencies from .uplugin.
        """
        print("\n" + "=" * 64)
        print("  STEP 2: Embed Dependencies")
        print("=" * 64)

        deps = self.config.dependencies
        if not deps:
            info("No dependencies configured in adapt_config.json.")
            return

        plugin_dir = self.repo_path / self.plugin_name
        source_dir = plugin_dir / "Source"

        for dep in deps:
            dep_name = dep["name"]
            dep_source = Path(dep["source"])
            target_dir = source_dir / dep_name

            print(f"  Embedding {dep_name}...")
            print(f"    Source: {dep_source}")
            print(f"    Target: {target_dir}")

            if not dry_run:
                # Remove old directory
                import shutil
                if target_dir.exists():
                    shutil.rmtree(target_dir)

                # Copy new source
                shutil.copytree(dep_source, target_dir)

        # Remove external plugin dependencies from .uplugin
        uplugin_path = plugin_dir / f"{self.plugin_name}.uplugin"
        if uplugin_path.exists():
            print(f"  Updating {uplugin_path} — removing external plugin deps...")
            # TODO: parse JSON, remove Plugins entries matching dep names
            if not dry_run:
                # Placeholder — needs JSON manipulation
                pass

        if not dry_run:
            git_or_die(self.repo_path, "add", "-A")
            git_or_die(self.repo_path, "commit", "-m",
                        "Changed: embed dependency plugins")

        info("Dependencies embedded.")

    # ── Step 3: Cascade adaptation ───────────────────────────

    def step3_cascade_adapt(self, dry_run: bool = False) -> None:
        """
        For each engine version (high→low):
          a. Cherry-pick base adaptation commits
          b. Update dependency plugin code
          c. Commit version boundary
          d. Run build loop (build_loop.py)
        """
        print("\n" + "=" * 64)
        print("  STEP 3: Cascade Adaptation")
        print("=" * 64)

        for i, version in enumerate(self.versions):
            print(f"\n{'─' * 64}")
            print(f"  Adapting for UE {version}  ({i+1}/{len(self.versions)})")
            print(f"{'─' * 64}")

            # 3a. Cherry-pick
            self._cherry_pick_version(version, dry_run)

            # 3b. Update dependencies
            self._update_dependencies(version, dry_run)

            # 3c. Version boundary commit
            print(f"  Committing version boundary: Changed: set engine version {version}")
            if not dry_run:
                git(self.repo_path, "commit", "--allow-empty", "-m",
                     f"Changed: set engine version {version}")

            # 3d. Build loop
            print(f"  Running build_loop.py for {version}...")
            if not dry_run:
                self._run_build_loop(version)

            print(f"  UE {version} adaptation complete.")

    def _cherry_pick_version(self, version: str, dry_run: bool) -> None:
        """Cherry-pick adaptation commits for this version."""
        ranges = self.config.cherry_pick_ranges
        if version not in ranges:
            info(f"No cherry-pick range configured for {version}, skipping.")
            return

        sha_range = ranges[version]
        print(f"  Cherry-pick range: {sha_range}")
        # TODO: implement git cherry-pick with conflict handling

    def _update_dependencies(self, version: str, dry_run: bool) -> None:
        """Update embedded dependency code to latest."""
        # Similar to step 2 but incremental
        pass

    def _run_build_loop(self, version: str) -> bool:
        """Invoke build_loop.py via subprocess."""
        script_dir = Path(__file__).resolve().parent
        cmd = [
            sys.executable,
            str(script_dir / "build_loop.py"),
            "-n", self.plugin_name,
            "-v", version,
            "-p", str(self.repo_path),
        ]
        result = subprocess.run(cmd)
        return result.returncode == 0


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="adapter",
        description="Full multi-engine plugin adaptation orchestrator (SKELETON).",
    )
    parser.add_argument("-n", "--plugin-name", required=True)
    parser.add_argument("-r", "--repo-path", required=True,
                        help="Path to build/release git repo")
    parser.add_argument("--versions", nargs="+", required=True,
                        help="Engine versions high→low (e.g., 5.8 5.7 5.6)")
    parser.add_argument("--upstream", default="upstream",
                        help="Git remote name for upstream plugin source")
    parser.add_argument("--old-branch", default=None,
                        help="Custom name for renamed old branch")
    parser.add_argument("--step", type=int, choices=[1, 2, 3],
                        help="Run only a specific step")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without executing")

    args = parser.parse_args()

    print("=" * 64)
    print("  PLUGIN ADAPTER — Multi-Engine Adaptation Orchestrator")
    print("=" * 64)
    print(f"  Plugin:   {args.plugin_name}")
    print(f"  Repo:     {args.repo_path}")
    print(f"  Versions: {' → '.join(args.versions)} (high→low)")
    print("=" * 64)
    print()
    print("  NOTE: This is a SKELETON. For now, use build_loop.py directly")
    print("  for the core single-version build-fix-commit cycle.")
    print()

    adapter = Adapter(
        plugin_name=args.plugin_name,
        repo_path=args.repo_path,
        versions=args.versions,
        upstream_remote=args.upstream,
        old_branch=args.old_branch,
    )

    steps = [args.step] if args.step else [1, 2, 3]

    for step in steps:
        if step == 1:
            adapter.step1_branch_setup(dry_run=args.dry_run)
        elif step == 2:
            adapter.step2_embed_dependencies(dry_run=args.dry_run)
        elif step == 3:
            adapter.step3_cascade_adapt(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
