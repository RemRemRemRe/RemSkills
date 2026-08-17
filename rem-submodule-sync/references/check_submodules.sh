#!/usr/bin/env bash
# check_submodules.sh — report every submodule's local HEAD vs each remote's
# default branch, as behind/ahead commit counts.
#
# Usage:
#   check_submodules.sh --root <project-dir> [--exclude-prefix <prefix>]... [--remote <name>]...
#
#   --root             path to the parent git repo (required)
#   --exclude-prefix   skip submodules whose path starts with this prefix
#                      (repeatable; e.g. --exclude-prefix Plugins/Rem)
#   --exclude-basename skip submodules whose last path segment starts with
#                      this prefix (repeatable; e.g. --exclude-basename Rem
#                      matches Plugins/Runtime/Gameplay/RemFoo and Content/Rem)
#   --remote           only compare the named remote(s) (repeatable; default: all)
#   -h, --help         show this help
#
# Notes:
#   - A submodule's .git is a FILE (gitdir pointer), not a directory — probe
#     existence with -e, not -d.
#   - The default branch is resolved per remote via symbolic-ref (or
#     ls-remote --symref fallback); it is NOT assumed to be "main".
#   - behind=N, ahead=M means: N commits on the remote branch missing from
#     HEAD, M commits on HEAD missing from the remote branch.

set -uo pipefail

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

ROOT=""
EXCLUDE_PREFIXES=()
EXCLUDE_BASENAMES=()
REMOTES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)            ROOT="${2:-}"; shift 2 ;;
    --exclude-prefix)  EXCLUDE_PREFIXES+=("${2:-}"); shift 2 ;;
    --exclude-basename) EXCLUDE_BASENAMES+=("${2:-}"); shift 2 ;;
    --remote)          REMOTES+=("${2:-}"); shift 2 ;;
    -h|--help)         usage 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage 1 ;;
  esac
done

[[ -n "$ROOT" ]] || { echo "error: --root is required" >&2; usage 1; }
[[ -d "$ROOT/.git" ]] || { echo "error: not a git repo: $ROOT" >&2; exit 1; }
[[ -f "$ROOT/.gitmodules" ]] || { echo "error: no .gitmodules in $ROOT" >&2; exit 1; }

# Parse submodule paths from .gitmodules.
mapfile -t ALL_PATHS < <(git -C "$ROOT" config --file "$ROOT/.gitmodules" \
  --get-regexp '^submodule\..*\.path$' | sed 's/^submodule\.[^.]*\.path //')

PATHS=()
for p in "${ALL_PATHS[@]}"; do
  skip=0
  for ex in "${EXCLUDE_PREFIXES[@]}"; do
    [[ "$p" == "$ex"* ]] && skip=1
  done
  base="${p##*/}"
  for ex in "${EXCLUDE_BASENAMES[@]}"; do
    [[ "$base" == "$ex"* ]] && skip=1
  done
  [[ $skip -eq 0 ]] && PATHS+=("$p")
done

echo "Checking ${#PATHS[@]}/${#ALL_PATHS[@]} submodules in $ROOT"
echo

for s in "${PATHS[@]}"; do
  d="$ROOT/$s"
  if [[ ! -e "$d/.git" ]]; then
    echo "== $s : NOT INITIALIZED (run 'git submodule update --init' if the parent needs it)"
    echo
    continue
  fi

  git -C "$d" fetch --all --prune --quiet 2>/dev/null
  echo "== $s"
  echo "   local   : $(git -C "$d" log -1 --format='%h %s' | cut -c1-90)"

  if [[ ${#REMOTES[@]} -gt 0 ]]; then
    mapfile -t RE < <(printf '%s\n' "${REMOTES[@]}")
  else
    mapfile -t RE < <(git -C "$d" remote)
  fi

  for r in "${RE[@]}"; do
    def="$(git -C "$d" symbolic-ref -q "refs/remotes/$r/HEAD" 2>/dev/null | sed 's|refs/remotes/||')"
    if [[ -z "$def" ]]; then
      def="$(git -C "$d" ls-remote --symref "$r" HEAD 2>/dev/null | head -1 \
             | awk '{print $2}' | sed 's|refs/heads/||')"
    fi
    if [[ -n "$def" ]] && git -C "$d" rev-parse -q --verify "refs/remotes/$def" >/dev/null 2>&1; then
      behind="$(git -C "$d" rev-list --count "HEAD..refs/remotes/$def" 2>/dev/null)"
      ahead="$(git -C "$d" rev-list --count "refs/remotes/$def..HEAD" 2>/dev/null)"
      tip="$(git -C "$d" log -1 --format='%h' "refs/remotes/$def" 2>/dev/null)"
      printf "   %-18s: behind=%-4s ahead=%-4s tip=%s\n" "$def" "$behind" "$ahead" "$tip"
    else
      echo "   $r : default branch not resolvable (fetch first?)"
    fi
  done
  echo
done
