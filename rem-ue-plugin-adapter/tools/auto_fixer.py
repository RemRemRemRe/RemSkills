#!/usr/bin/env python3
"""
auto_fixer.py — Build error parser & rule-based auto-fixer
============================================================
Parses MSVC/UBT compilation errors and attempts to fix known patterns
using rules defined in fix_rules.json.

Usage (standalone test):
    python auto_fixer.py --log build_errors.log --rules fix_rules.json

Usage (as library):
    from auto_fixer import ErrorParser, Fixer
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
#  Error parsing
# ═══════════════════════════════════════════════════════════════════

@dataclass
class BuildError:
    """A single parsed compilation error."""
    file: str
    line: int
    column: int
    code: str
    message: str
    raw: str  # original line

    # Extracted from message
    symbol: Optional[str] = None  # e.g., 'Modulo' from "is not a member of 'FMath'"

    def __str__(self) -> str:
        return f"{self.file}({self.line}): error {self.code}: {self.message}"


class ErrorParser:
    """
    Parse MSVC and UBT error output into structured BuildError objects.

    MSVC format:
        file(line): error CXXXX: message
        file(line,col): error CXXXX: message
        file(line): fatal error CXXXX: message

    UBT format:
        <path>(line): error: <message>
    """

    # ── MSVC patterns ──────────────────────────────────────────
    # file(line): error C1234: message
    RE_MSVC = re.compile(
        r'^(.+?)\((\d+)(?:,(\d+))?\)\s*:\s*(?:fatal\s+)?error\s+(C\d+|LNK\d+)\s*:\s*(.+)$',
        re.IGNORECASE,
    )

    # ── UBT patterns ───────────────────────────────────────────
    RE_UBT = re.compile(
        r'^(.+?)\((\d+)\)\s*:\s*error\s*:\s*(.+)$',
        re.IGNORECASE,
    )

    # ── "is not a member of 'Class'" extraction ────────────────
    RE_MEMBER = re.compile(r"'([^']+)'\s*:\s*is not a member of\s*'([^']+)'")
    RE_IDENTIFIER = re.compile(r"'([^']+)'\s*:\s*identifier not found")
    RE_UNDECLARED = re.compile(r"'([^']+)'\s*:\s*undeclared identifier")

    @classmethod
    def parse_output(cls, text: str) -> List[BuildError]:
        """Parse combined stdout+stderr from a build into errors."""
        errors: List[BuildError] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()

            # Try MSVC format first
            m = cls.RE_MSVC.match(line)
            if not m:
                m = cls.RE_UBT.match(line)
            if not m:
                continue

            file_path = m.group(1).strip()
            line_no   = int(m.group(2))
            col       = int(m.group(3)) if m.group(3) else 0
            code      = m.group(4) if m.lastindex and m.lastindex >= 4 else ""
            msg       = m.group(m.lastindex).strip() if m.lastindex else ""

            if not code and m.lastindex:
                # UBT format: groups are file, line, message; no error code
                code = "UBT"
                msg  = m.group(m.lastindex).strip() if m.lastindex else ""

            err = BuildError(
                file=file_path,
                line=line_no,
                column=col,
                code=code,
                message=msg,
                raw=raw_line,
            )

            # Try to extract symbol
            for pattern in [cls.RE_MEMBER, cls.RE_IDENTIFIER, cls.RE_UNDECLARED]:
                sm = pattern.search(msg)
                if sm:
                    err.symbol = sm.group(1)
                    break

            errors.append(err)

        return errors

    @classmethod
    def group_by_file(cls, errors: List[BuildError]) -> Dict[str, List[BuildError]]:
        """Group errors by source file."""
        result: Dict[str, List[BuildError]] = {}
        for e in errors:
            result.setdefault(e.file, []).append(e)
        return result


# ═══════════════════════════════════════════════════════════════════
#  Fix rules
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FixRule:
    """A single auto-fix rule loaded from fix_rules.json."""
    id: str
    description: str
    enabled: bool

    # Match criteria
    error_codes: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    file_pattern: Optional[re.Pattern] = None
    message_pattern: Optional[re.Pattern] = None

    # Fix configuration
    fix_type: str = ""
    fix_pattern: Optional[re.Pattern] = None
    fix_replacement: str = ""
    fix_include: str = ""
    fix_note: str = ""


class FixRuleLoader:
    """Load and compile fix rules from JSON."""

    @classmethod
    def load(cls, path: Path) -> List[FixRule]:
        if not path.exists():
            print(f"[WARN] fix_rules.json not found at {path}, no auto-fix rules loaded.")
            return []

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        rules: List[FixRule] = []
        for entry in data.get("rules", []):
            if not entry.get("enabled", True):
                continue

            match_cfg = entry.get("match", {})
            fix_cfg   = entry.get("fix", {})

            rule = FixRule(
                id=entry["id"],
                description=entry.get("description", ""),
                enabled=True,
                error_codes=match_cfg.get("error_code", "").split("|") if match_cfg.get("error_code") else [],
                symbols=match_cfg.get("symbol", "").split("|") if match_cfg.get("symbol") else [],
                file_pattern=cls._compile(match_cfg.get("file_pattern")),
                message_pattern=cls._compile(match_cfg.get("message_pattern")),
                fix_type=fix_cfg.get("type", ""),
                fix_pattern=cls._compile(fix_cfg.get("pattern")),
                fix_replacement=fix_cfg.get("replacement", ""),
                fix_include=fix_cfg.get("include", ""),
                fix_note=fix_cfg.get("note", ""),
            )
            rules.append(rule)

        return rules

    @staticmethod
    def _compile(pattern: Optional[str]) -> Optional[re.Pattern]:
        if not pattern:
            return None
        try:
            return re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            print(f"[WARN] Invalid regex pattern '{pattern}': {e}")
            return None


# ═══════════════════════════════════════════════════════════════════
#  Rule matching
# ═══════════════════════════════════════════════════════════════════

class RuleMatcher:
    """Match build errors against known fix rules."""

    def __init__(self, rules: List[FixRule]):
        self.rules = rules

    def find_match(self, error: BuildError) -> Optional[FixRule]:
        """Find the first matching rule for a build error."""
        for rule in self.rules:
            if self._matches(rule, error):
                return rule
        return None

    def _matches(self, rule: FixRule, error: BuildError) -> bool:
        # Error code match
        if rule.error_codes and error.code not in rule.error_codes:
            return False

        # Symbol match
        if rule.symbols and error.symbol:
            if not any(s.lower() == error.symbol.lower() for s in rule.symbols):
                return False

        # File pattern match
        if rule.file_pattern and not rule.file_pattern.search(error.file):
            return False

        # Message pattern match
        if rule.message_pattern and not rule.message_pattern.search(error.message):
            return False

        return True


# ═══════════════════════════════════════════════════════════════════
#  Fix application
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FixResult:
    """Result of applying a fix."""
    rule_id: str
    file: str
    success: bool
    description: str
    note: str = ""


class Fixer:
    """Apply fix rules to source files."""

    def __init__(self, rules: List[FixRule]):
        self.rules = rules
        self.matcher = RuleMatcher(rules)

    def fix_error(self, error: BuildError) -> Optional[FixResult]:
        """Try to fix a single error. Returns result if fixed, None if no rule matches."""
        rule = self.matcher.find_match(error)
        if not rule:
            return None

        file_path = Path(error.file)

        if not file_path.exists():
            return FixResult(
                rule_id=rule.id,
                file=error.file,
                success=False,
                description=f"File not found: {error.file}",
            )

        try:
            if rule.fix_type == "regex_replace":
                return self._apply_regex_replace(file_path, rule)
            elif rule.fix_type == "include_add":
                return self._apply_include_add(file_path, rule)
            elif rule.fix_type == "include_replace":
                return self._apply_include_replace(file_path, rule)
            else:
                return FixResult(
                    rule_id=rule.id, file=error.file, success=False,
                    description=f"Unknown fix type: {rule.fix_type}",
                )
        except Exception as e:
            return FixResult(
                rule_id=rule.id, file=error.file, success=False,
                description=str(e),
            )

    def fix_errors(self, errors: List[BuildError]) -> List[FixResult]:
        """Try to fix a batch of errors. Deduplicates by file+rule."""
        results: List[FixResult] = []
        seen: set = set()

        for error in errors:
            rule = self.matcher.find_match(error)
            if not rule:
                continue

            key = (error.file, rule.id)
            if key in seen:
                continue
            seen.add(key)

            result = self.fix_error(error)
            if result:
                results.append(result)

        return results

    # ── Private fix methods ────────────────────────────────────

    def _apply_regex_replace(self, file_path: Path, rule: FixRule) -> FixResult:
        if not rule.fix_pattern:
            return FixResult(rule_id=rule.id, file=str(file_path),
                             success=False, description="No regex pattern in rule")

        content = file_path.read_text(encoding="utf-8", errors="replace")
        new_content, count = rule.fix_pattern.subn(rule.fix_replacement, content)

        if count == 0:
            return FixResult(
                rule_id=rule.id, file=str(file_path), success=False,
                description=f"Pattern not found in file: {rule.fix_pattern.pattern}",
            )

        file_path.write_text(new_content, encoding="utf-8")
        return FixResult(
            rule_id=rule.id, file=str(file_path), success=True,
            description=f"Applied {count} replacement(s): {rule.description}",
            note=rule.fix_note,
        )

    def _apply_include_add(self, file_path: Path, rule: FixRule) -> FixResult:
        if not rule.fix_include:
            return FixResult(rule_id=rule.id, file=str(file_path),
                             success=False, description="No include specified")

        content = file_path.read_text(encoding="utf-8", errors="replace")
        include_line = f'#include "{rule.fix_include}"'

        if include_line in content:
            return FixResult(
                rule_id=rule.id, file=str(file_path), success=False,
                description=f"Include already present: {rule.fix_include}",
            )

        # Insert after the last existing #include
        lines = content.splitlines()
        last_include_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'\s*#include\s', line):
                last_include_idx = i

        if last_include_idx >= 0:
            lines.insert(last_include_idx + 1, include_line)
            new_content = "\n".join(lines) + "\n"
        else:
            # No existing includes — insert at top after copyright header
            # Find first non-comment line
            insert_at = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith("//") and not line.strip().startswith("/*"):
                    insert_at = i
                    break
            lines.insert(insert_at, include_line + "\n")
            new_content = "\n".join(lines) + "\n"

        file_path.write_text(new_content, encoding="utf-8")
        return FixResult(
            rule_id=rule.id, file=str(file_path), success=True,
            description=f"Added include: {rule.fix_include}",
        )

    def _apply_include_replace(self, file_path: Path, rule: FixRule) -> FixResult:
        # Same as regex_replace for include changes
        return self._apply_regex_replace(file_path, rule)


# ═══════════════════════════════════════════════════════════════════
#  Standalone mode (for testing)
# ═══════════════════════════════════════════════════════════════════

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse build errors and apply auto-fix rules."
    )
    parser.add_argument("--log", required=True, help="Build error log file (or '-' for stdin)")
    parser.add_argument("--rules", default="fix_rules.json", help="Path to fix_rules.json")
    parser.add_argument("--apply", action="store_true", help="Apply fixes (default: parse only)")

    args = parser.parse_args()

    # Load rules
    rules_path = Path(args.rules)
    if not rules_path.is_absolute():
        rules_path = Path(__file__).resolve().parent / rules_path
    rules = FixRuleLoader.load(rules_path)

    if not rules:
        print("No rules loaded. Nothing to do.")
        sys.exit(0)

    print(f"Loaded {len(rules)} rule(s) from {rules_path}\n")

    # Read log
    if args.log == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.log).read_text(encoding="utf-8", errors="replace")

    # Parse
    errors = ErrorParser.parse_output(text)
    print(f"Parsed {len(errors)} error(s).")

    # Group and print
    by_file = ErrorParser.group_by_file(errors)
    for file, file_errors in by_file.items():
        print(f"\n-- {file}  ({len(file_errors)} errors) --")
        for e in file_errors:
            rule = RuleMatcher(rules).find_match(e)
            matched = f" -> rule: {rule.id}" if rule else " -> (no rule)"
            print(f"  L{e.line}: {e.code} {e.message[:100]}{matched}")

    # Apply fixes
    if args.apply:
        print("\n" + "=" * 60)
        print("Applying fixes...")
        print("=" * 60)
        fixer = Fixer(rules)
        results = fixer.fix_errors(errors)
        for r in results:
            status = "[OK]" if r.success else "[FAIL]"
            print(f"  {status} [{r.rule_id}] {r.file}: {r.description}")
            if r.note:
                print(f"    NOTE: {r.note}")

    # Summary
    matched = sum(1 for e in errors if RuleMatcher(rules).find_match(e))
    unmatched = len(errors) - matched
    print(f"\n{'=' * 60}")
    print(f"  {matched} matched, {unmatched} unmatched, {len(errors)} total")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
