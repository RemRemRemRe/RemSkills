#!/usr/bin/env python3
"""Flag non-static member functions whose body touches no member of their type.

The IDE reports this as "member function can be made static", and that hint does not
arrive through the MCP diagnostics interface (measured 2026-11: `get_file_problems` and
`lint_files` both return nothing for a file the IDE flags), so this checker is the
mechanical half of the `rem-cpp-best-practices` checklist item.

    python tools/check_static_members.py --cpp <Type.cpp> [--header <Type.h>] [--verbose]
    python tools/check_static_members.py --path <dir> [--verbose]

Header resolution, in order: `--header`, then `Type.h` next to the `.cpp`, then the same
relative path with `/Private/` replaced by `/Public/`.

What it does: parses the header for the type's member names (data members and functions),
then for every out-of-line `Type::Method(...)` definition in the `.cpp` asks whether the
body mentions `this`, any member name, or the type itself (a nested type or a static call
is a use of the type, not of the instance). A body that mentions nothing is a candidate.

Skipped, because the instance is used by something the body cannot name: `static`, `virtual`,
`override`, `final`, `constexpr`, and anything UHT grabs (`UFUNCTION`, `BlueprintCallable`,
`BlueprintImplementableEvent`, `BlueprintNativeEvent`, `RPC`, `Exec`).

A function addressed as a **member function pointer** (`.AddRaw(this, &Type::Handler)`,
`BindUObject`) must stay non-static even when its body only reads its parameters. The checker
skips a name it finds as `&Type::Name` / `&ThisClass::Name` anywhere in the .cpp; a binding
from another file still reaches the output, and then the reader checks it. Measured 2026-11:
one module sweep produced eight candidates and all eight were either an override or a
delegate handler.

Known false positives, which is why the output says "candidate":
  - an inherited member used unqualified (base members are not in this header);
  - a member reached through a macro that expands to an access;
  - a body that only calls another member function whose name matches a local variable.

Exit code 1 when at least one candidate is printed, 0 otherwise, so it can gate a sweep.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TYPE_DECL = re.compile(r"^\s*(?:class|struct)\s+(?:\w+_API\s+)?(\w+)\b", re.MULTILINE)
UHT_MARKERS = (
    "UFUNCTION",
    "BlueprintCallable",
    "BlueprintImplementableEvent",
    "BlueprintNativeEvent",
    "BlueprintPure",
    "Exec",
    "RPC",
)
# `void Name(` / `Type Name(` / `Type* Name(` at the start of a declaration line.
FUNCTION_DECL = re.compile(r"^\s*(?:static\s+|virtual\s+|FORCEINLINE\s+|inline\s+)*"
                           r"(?:[\w:<>,\s\*&]+?)\b(\w+)\s*\(", re.MULTILINE)
DATA_DECL = re.compile(r"^\s*(?:UPROPERTY\([^)]*\)\s*)?(?:mutable\s+)?"
                       r"(?:[\w:<>,\s\*&]+?)\b(\w+)\s*(?:\{[^}]*\}|=\s*[^;]+)?;\s*$",
                       re.MULTILINE)
NOT_A_NAME = {"return", "if", "for", "while", "switch", "sizeof", "decltype", "static_assert",
              "else", "do", "case", "catch", "throw", "new", "delete", "operator", "alignof"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def type_body(header: str) -> tuple[str, str] | None:
    """Return (type name, body) of the first reflected type in the header."""
    found = None
    depth = 0
    for match in TYPE_DECL.finditer(header):
        name = match.group(1)
        open_at = header.find("{", match.end())
        if open_at == -1:
            continue
        depth = 0
        for index in range(open_at, len(header)):
            char = header[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    if found is None:
                        found = (name, header[open_at + 1:index])
                    break
        if found is not None:
            return found
    return found


def members(body: str) -> set[str]:
    """Data members and declared functions of one type body."""
    names = {m.group(1) for m in FUNCTION_DECL.finditer(body)}
    names |= {m.group(1) for m in DATA_DECL.finditer(body)}
    return {name for name in names if name not in NOT_A_NAME and not name.startswith("GENERATED")}


SKIP_KEYWORDS = ("virtual", "override", "final", "constexpr", "static")


def skipped_names(body: str) -> set[str]:
    """Functions that cannot be static: virtual/override/final/constexpr/static declarations.

    Declarations are split at `;` so a qualifier on a later line (`override` after the
    parameter list) still lands in the same segment.
    """
    skipped: set[str] = set()
    for segment in body.split(";"):
        if "(" not in segment:
            continue
        if not any(keyword in segment for keyword in SKIP_KEYWORDS):
            continue
        for match in FUNCTION_DECL.finditer(segment):
            skipped.add(match.group(1))
        else:
            match = re.search(r"(\w+)\s*\(", segment)
            if match:
                skipped.add(match.group(1))
    # UFUNCTION-declared functions are reflected: never free to become static.
    block: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("UFUNCTION"):
            block = [stripped]
            continue
        if block and any(marker in " ".join(block) for marker in UHT_MARKERS):
            match = FUNCTION_DECL.match(line)
            if match:
                skipped.add(match.group(1))
            block = []
        elif block:
            block = []
    return skipped


def definitions(source: str, type_name: str):
    """Yield (method name, line number, body) for out-of-line definitions of one type."""
    pattern = re.compile(rf"^[\w:<>,\s\*&]*\b{re.escape(type_name)}::(\w+)\s*\(", re.MULTILINE)
    for match in pattern.finditer(source):
        name = match.group(1)
        brace = source.find("{", match.end())
        if brace == -1:
            continue
        depth = 0
        for index in range(brace, len(source)):
            char = source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    yield name, source.count("\n", 0, match.start()) + 1, source[brace + 1:index]
                    break


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpp", help="source file with the definitions")
    parser.add_argument("--header", help="header with the type; derived when omitted")
    parser.add_argument("--path", help="directory to sweep for pairs of Type.cpp/Type.h")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    pairs: list[tuple[Path, Path]] = []
    if args.cpp:
        cpp = Path(args.cpp)
        header = Path(args.header) if args.header else (
            cpp.with_suffix(".h") if cpp.with_suffix(".h").exists() else
            Path(str(cpp).replace("\\Private\\", "\\Public\\").replace("/Private/", "/Public/")).with_suffix(".h")
        )
        pairs.append((cpp, header))
    elif args.path:
        for cpp in sorted(Path(args.path).rglob("*.cpp")):
            header = Path(str(cpp).replace("\\Private\\", "\\Public\\").replace("/Private/", "/Public/")).with_suffix(".h")
            if header.exists():
                pairs.append((cpp, header))
    else:
        parser.error("pass --cpp or --path")

    candidates = 0
    for cpp, header in pairs:
        if not header.exists():
            if args.verbose:
                print(f"skip {cpp}: no header next to it")
            continue
        header_text = read(header)
        parsed = type_body(header_text)
        if parsed is None:
            if args.verbose:
                print(f"skip {cpp}: no type in {header.name}")
            continue
        type_name, body = parsed
        declared = members(body)
        grabbed = skipped_names(body)
        source = read(cpp)

        # a member function pointer (a delegate binding) pins the method to the instance
        bound = {match.group(1) for match in re.finditer(
            rf"&\s*(?:{re.escape(type_name)}|ThisClass)::(\w+)", source)}

        for name, line, definition in definitions(source, type_name):
            if name in grabbed or name in bound:
                continue
            if re.search(r"\bthis\b", definition) or type_name in definition:
                continue
            if any(re.search(rf"\b{re.escape(member)}\b", definition) for member in declared):
                continue
            candidates += 1
            print(f"{cpp}:{line} {type_name}::{name} - no member reference; consider static")

    if args.verbose:
        print(f"checked {len(pairs)} pair(s), {candidates} candidate(s)")
    return 1 if candidates else 0


if __name__ == "__main__":
    sys.exit(main())
