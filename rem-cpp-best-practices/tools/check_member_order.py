#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Member ordering inside a type declaration: data members before functions.

The rule: inside a ``struct``/``class``/``union`` body every data-member group
comes before the function-member groups - public data, protected data, private
data, then public/protected/private functions. A data member declared after any
function member (constructors included) is a violation. Labels are optional in
the sense that the first group of a ``struct``/``union`` may run without a
``public:`` (it is that type's default accessibility); nothing in the check
depends on an explicit leading label. Ordering is judged per body: a nested type
is checked on its own, never inside its parent's report.

How one body is read: comments, string/char literals and preprocessor lines are
blanked first (``#if`` blocks are transparent - their content still counts),
then the braces are walked. Members are split on ``;`` and on inline ``{``
bodies, tolerating parentheses (a ``(`` inside a declaration never ends a
member). Access labels, ``GENERATED_BODY()``, ``using``/``typedef`` aliases,
``friend`` declarations, nested types, ``enum`` bodies and bare upper-case macro
invocations are neutral - they never decide an order. A member is a FUNCTION
when its declaration, after attributes and trailing
``const``/``override``/``= 0``/``= default``/``= delete``/``noexcept``/trailing
return type, ends in ``)`` and has no top-level ``=`` before that parameter list
(so ``int32 X = Compute();`` stays data, and so does a lambda initializer); a
member whose whole declaration matches ``--function-macro`` is a function as
well, because such a macro expands to member functions. Everything else is data.

Usage::

    python check_member_order.py --path <file-or-dir> [--path <path> ...]
    python check_member_order.py --path <dir> [--exclude <glob> ...]
    python check_member_order.py --path <dir> [--exclude-from <file> ...]
    python check_member_order.py --changed <file> [--changed <file> ...]
    python check_member_order.py --diff [REV]
    python check_member_order.py --json
    python check_member_order.py --self-test

``--path`` recurses into a directory for ``*.h``/``*.hpp``/``*.inl`` (skipping
``Intermediate``, ``Binaries``, ``ThirdParty``, ``.git``, ``node_modules`` and
dot directories); ``--changed`` takes an explicit file list (an agent round);
``--diff`` reads ``git diff --name-only [REV]`` (default ``REV`` = HEAD, i.e. the
working tree) and keeps the headers.

``--exclude`` and ``--exclude-from`` drop paths before they are read, for every
input mode. A pattern is matched case-insensitively against the absolute path
and the path relative to the scanned root; ``*``/``?``/``**`` behave as in a
shell, a pattern also covers everything below the directory it names, and it may
begin at any path-component boundary, so a bare directory name works from any
root. A matching directory prunes the walk. A list file holds one glob per line
(``#`` starts a comment, blank lines are ignored), and a relative pattern also
resolves against the list file's own directory.

Exit codes: 0 - every header was read and no violation was found; 1 - at least
one violation; 2 - bad input: an unknown path, a failing ``git diff``, --exclude-from
not readable, or not one header reached (a wrong argument must never read as clean;
"I checked nothing" is never 0, and every path excluded counts as checked nothing).
``--self-test`` reports the same pairs: 0 - every fixture behaved as expected; 1 - a
fixture failed, i.e. the checker itself is wrong.

Limits, by design: this is a declaration-order reader, not a compiler. Braces
produced by a ``#define``, or a brace opened in one ``#if`` branch and closed in
another, are not understood; a type declared inside a function body is a local
type, not a member, and is skipped; a brace belonging to a constructor's
initializer list is told from a function body by the text in front of it (``=``
or ``)``/``}``), so an unusual spelling of that list may be read as data; a
macro-generated declaration is data unless it matches ``--function-macro``. The
exclude list is a local value, not a built-in one: which directory holds vendored
third-party code is not knowable from the filesystem.
"""

import argparse
import bisect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HEADER_SUFFIXES = ('.h', '.hpp', '.inl')
SKIP_DIRS = ('Intermediate', 'Binaries', 'ThirdParty', '.git', 'node_modules')
RULE = 'data members precede function members in every visibility group'

# --------------------------------------------------------------------------
# Lexical cleaning: same length as the input, so offsets stay line-accurate.
# --------------------------------------------------------------------------

_LITERAL_OR_COMMENT_RE = re.compile(
    r'//[^\n]*'
    r'|/\*.*?\*/'
    r'|(?:u8|u|U|L)?R"(?P<raw>[^()\\\s]{0,16})\(.*?\)(?P=raw)"'
    r'|(?:u8|u|U|L)?"(?:\\.|[^"\\])*"'
    r"|(?:u8|u|U|L)?'(?:\\.|[^'\\])*'",
    re.S)

_DIRECTIVE_RE = re.compile(r'^[ \t]*#')


def _blank(match):
    text = match.group(0)
    return ''.join('\n' if char == '\n' else ' ' for char in text)


def clean_text(text):
    """`text` with comments, literals and preprocessor lines blanked out.

    Newlines survive, every other blanked character becomes a space, so an
    offset in the result is an offset in the input.
    """
    masked = _LITERAL_OR_COMMENT_RE.sub(_blank, text)
    lines = masked.split('\n')
    continuing = False
    for index, line in enumerate(lines):
        if continuing or _DIRECTIVE_RE.match(line):
            continuing = line.rstrip('\r').endswith('\\')
            lines[index] = ' ' * len(line)
        else:
            continuing = False
    return '\n'.join(lines)


def read_text(path):
    with open(path, encoding='utf-8-sig', errors='replace') as handle:
        return handle.read()


# --------------------------------------------------------------------------
# Declaration classification
# --------------------------------------------------------------------------

_ATTRIBUTE_MACRO_RE = re.compile(r'[A-Z][A-Z0-9_]*[ \t]*\(')
_TRAILING_STRIP = (
    re.compile(r'[\s;]+$'),
    re.compile(r'\s*\{\s*\}\s*$'),
    re.compile(r'\s*=\s*(?:0|default|delete)\s*$'),
    re.compile(r'\s*noexcept\s*\([^()]*\)\s*$'),
    re.compile(r'\s*requires\b.*$'),
    re.compile(r'\s*(?:const|volatile|override|final|noexcept|mutable|'
               r'constexpr|consteval|inline|static)\s*$'),
    re.compile(r'\s*(?:&&|&)\s*$'),
    re.compile(r'\s*->\s*[\w:]+(?:\s*<.*>)?\s*[&*]?\s*$'),
)
_BARE_MACRO_RE = re.compile(r'^[A-Z][A-Z0-9_]*\s*\(.*\)$')
_NEUTRAL_HEAD_RE = re.compile(
    r'^(?:using|typedef|friend|static_assert|enum|class|struct|union)\b')
_TEMPLATE_HEAD_RE = re.compile(r'^template\s*<.*>\s*')
_OPERATOR_NAME_RE = re.compile(
    r'\boperator\b\s*(?:[=!<>+\-*/%^&|~]{1,3}|\[\s*\]|\(\s*\))')
_ASSIGN_NEIGHBOURS = '=!<>+-*/%^&|'


def _matching_close(text, open_index):
    """Index of the ``)`` closing the ``(`` at `open_index`, or -1."""
    depth = 0
    for index in range(open_index, len(text)):
        char = text[index]
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                return index
    return -1


def _matching_open(text, close_index):
    """Index of the ``(`` opening the ``)`` at `close_index`, or -1."""
    depth = 0
    for index in range(close_index, -1, -1):
        char = text[index]
        if char == ')':
            depth += 1
        elif char == '(':
            depth -= 1
            if depth == 0:
                return index
    return -1


def _skip_attributes(text, start=0):
    """First index of the declaration after leading attributes/macros."""
    index = start
    length = len(text)
    while True:
        while index < length and text[index] in ' \t\r\n':
            index += 1
        if index >= length:
            return length
        if text.startswith('[[', index):
            end = text.find(']]', index + 2)
            if end < 0:
                return index
            index = end + 2
            continue
        match = _ATTRIBUTE_MACRO_RE.match(text, index)
        if match:
            close = _matching_close(text, match.end() - 1)
            if close < 0 or not text[close + 1:].strip():
                return index
            index = close + 1
            continue
        return index


def _one_line(text):
    """Collapse to a single line, and a blanked inline body to ``{}``."""
    return re.sub(r'\s*\{\s*\}', '{}', ' '.join(text.split()))


def _strip_trailing(text):
    previous = None
    while previous != text:
        previous = text
        for pattern in _TRAILING_STRIP:
            text = pattern.sub('', text)
        text = text.rstrip()
    return text


def _has_assignment(text):
    """True when `text` carries a top-level ``=`` that assigns rather than compares."""
    operator_spans = [(match.start(), match.end())
                      for match in _OPERATOR_NAME_RE.finditer(text)]
    depth = 0
    for index, char in enumerate(text):
        if char == '(':
            depth += 1
            continue
        if char == ')':
            depth = max(0, depth - 1)
            continue
        if char != '=' or depth:
            continue
        if any(start <= index < end for start, end in operator_spans):
            continue
        following = text[index + 1] if index + 1 < len(text) else ''
        preceding = text[index - 1] if index else ''
        if following == '=' or preceding in _ASSIGN_NEIGHBOURS:
            continue
        return True
    return False


def is_function_like(text):
    """True when the declaration `text` declares (or defines) a function."""
    stripped = _strip_trailing(text)
    if not stripped.endswith(')'):
        return False
    open_index = _matching_open(stripped, len(stripped) - 1)
    if open_index < 0:
        return False
    before = stripped[:open_index].rstrip()
    if not before or before.endswith(')'):
        # No declarator in front, or a function-pointer declarator: data.
        return False
    # A member template's head may carry ``= void``-style default arguments; they
    # assign nothing, so they must not make the declaration look like data.
    declarator = _TEMPLATE_HEAD_RE.sub('', before) or before
    return not _has_assignment(declarator)


def member_kind(text, function_macro):
    """'data', 'function' or 'neutral' for one member declaration."""
    line = _one_line(text)
    if not line:
        return 'neutral'
    if function_macro.match(line):
        return 'function'
    if _NEUTRAL_HEAD_RE.match(line):
        return 'neutral'
    if _BARE_MACRO_RE.match(line):
        return 'neutral'
    return 'function' if is_function_like(line) else 'data'


_TYPE_KEYWORD_RE = re.compile(r'\b(?:struct|class|union)\b')
_TYPE_PREFIX_RE = re.compile(
    r'^(?:(?:typedef|friend|export)\s+)?(?:template\s*<.*>\s*)?(?:requires\b.*)?$', re.S)
_ENUM_RE = re.compile(r'^enum\b')
_NAMESPACE_RE = re.compile(r'^(?:inline\s+)?namespace\b|^extern\b')
_TYPE_NAME_RE = re.compile(r'\b(?:struct|class|union)\b\s+((?:[A-Za-z_]\w*\s+)*[A-Za-z_]\w*)')


def _declaration_head(head):
    """`head` without leading attributes/macro invocations, on one line."""
    return _one_line(head[_skip_attributes(head):])


def type_keyword(head):
    """The ``struct``/``class``/``union`` keyword opening the body after `head`."""
    line = _declaration_head(head)
    if not line:
        return None
    # The last type keyword of the head opens the body, and only when the text in
    # front of it is a template head, a requires-clause or nothing at all.
    found = None
    for match in _TYPE_KEYWORD_RE.finditer(line):
        found = match
    if not found:
        return None
    before = line[:found.start()].strip()
    if not before:
        # ``struct FFoo* GetFoo()`` declares a function, not a type body.
        return None if line.endswith(')') else found.group()
    return found.group() if _TYPE_PREFIX_RE.match(before) else None


def type_name(head):
    match = _TYPE_NAME_RE.search(_one_line(head))
    if not match:
        return '(anonymous)'
    words = [word for word in match.group(1).split() if word != 'final']
    return words[-1] if words else '(anonymous)'


def brace_role(head, function_macro):
    """'function' when the ``{`` opens a function body, 'init' for an initializer."""
    line = _declaration_head(head)
    if is_function_like(line):
        return 'function'
    if _has_assignment(line) or member_kind(line, function_macro) == 'function':
        return 'init'
    if line.endswith(')') or line.endswith('}'):
        return 'function'
    return 'init'


# --------------------------------------------------------------------------
# Body walk
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r'(?P<label>^[ \t]*(?:public|protected|private)[ \t]*:)'
    r'|(?P<macro>^[ \t]*[A-Z][A-Z0-9_]*(?:[ \t]*\([^;{}]*\))?[ \t]*$)'
    r'|(?P<ch>[{}();])',
    re.M)

_LABEL_RE = re.compile(r'[ \t]*(\w+)')
_MACRO_NAME_RE = re.compile(r'[A-Z][A-Z0-9_]*')
_GENERATED_RE = re.compile(r'^GENERATED_[A-Z_]+$')
_CLASS_DEFAULT_ACCESS = {'class': 'private', 'struct': 'public', 'union': 'public'}


class _Frame(object):
    __slots__ = ('kind', 'depth', 'paren', 'buf', 'access', 'role', 'start',
                 'name', 'last_function', 'data_run', 'members')

    def __init__(self, kind, start, access='private', name='(anonymous)'):
        self.kind = kind
        self.depth = 1
        self.paren = 0
        self.buf = start
        self.access = access
        self.role = None
        self.start = start
        self.name = name
        self.last_function = None
        self.data_run = False
        self.members = 0


class _Scan(object):
    def __init__(self, text, function_macro):
        self.text = text
        self.display = list(text)
        self.function_macro = function_macro
        self.frames = [_Frame('file', 0, name='(file)')]
        self.bodies = []
        self.violations = []
        self.line_starts = [0]
        position = text.find('\n')
        while position >= 0:
            self.line_starts.append(position + 1)
            position = text.find('\n', position + 1)

    # -- helpers ---------------------------------------------------------
    def location(self, position):
        line = bisect.bisect_right(self.line_starts, position) - 1
        return line + 1, position - self.line_starts[line] + 1

    def shown(self, start, end):
        return _one_line(''.join(self.display[start:end]))

    def finish(self, end, forced=None, resume=None):
        """Close the pending member of the top frame at offset `end`."""
        frame = self.frames[-1]
        start = frame.buf
        frame.buf = end if resume is None else resume
        if start >= end:
            return
        decl_start = start + _skip_attributes(self.text[start:end])
        if decl_start >= end:
            return
        text = self.text[decl_start:end]
        if not text.strip():
            return
        shown = self.shown(decl_start, end)
        if not shown:
            return
        kind = forced or member_kind(text, self.function_macro)
        if frame.kind != 'type':
            return
        frame.members += 1
        line, column = self.location(decl_start)
        if kind == 'function':
            frame.last_function = (shown, line)
            frame.data_run = False
        elif kind == 'data':
            if frame.last_function is not None and not frame.data_run:
                frame.data_run = True
                self.violations.append({
                    'line': line,
                    'column': column,
                    'member': shown,
                    'after_member': frame.last_function[0],
                    'after_line': frame.last_function[1],
                    'visibility': frame.access,
                    'type': frame.name,
                })

    def open_frame(self, position, role, kind, access, name):
        child = _Frame(kind, position + 1, access=access, name=name)
        child.role = role
        child.start = position
        self.frames.append(child)

    def close_frame(self, position):
        if len(self.frames) == 1:
            return
        child = self.frames.pop()
        parent = self.frames[-1]
        start = child.start + 1
        if position > start:
            self.display[start:position] = [' '] * (position - start)
        if child.kind == 'type':
            self.bodies.append({'type': child.name, 'members': child.members})
        if child.role == 'init':
            return
        if child.role in ('function', 'nested_type', 'nested_enum'):
            self.finish(position + 1, forced='function' if child.role == 'function'
                        else 'neutral')
            return
        parent.buf = position + 1

    # -- main loop -------------------------------------------------------
    def run(self):
        for match in _TOKEN_RE.finditer(self.text):
            frame = self.frames[-1]
            group = match.lastgroup
            position = match.start()
            if frame.kind in ('skip', 'enum', 'init'):
                if group != 'ch':
                    continue
                char = match.group()
                if char == '{':
                    frame.depth += 1
                elif char == '}':
                    frame.depth -= 1
                    if frame.depth <= 0:
                        self.close_frame(position)
                continue
            if group == 'label':
                if frame.kind == 'type' and frame.paren == 0:
                    self.finish(position, resume=match.end())
                    frame.access = _LABEL_RE.match(match.group()).group(1)
                continue
            if group == 'macro':
                self.macro_line(match)
                continue
            char = match.group()
            if char == '(':
                frame.paren += 1
            elif char == ')':
                if frame.paren:
                    frame.paren -= 1
            elif char == ';':
                if frame.paren == 0:
                    if frame.kind == 'type':
                        self.finish(position, resume=position + 1)
                    else:
                        frame.buf = position + 1
            elif char == '}':
                self.close_frame(position)
            else:
                self.open_body(position)
        return self.violations, self.bodies

    def macro_line(self, match):
        """A whole upper-case line: a member only when it is a body macro."""
        frame = self.frames[-1]
        if frame.kind != 'type' or frame.paren != 0:
            return
        if self.text[frame.buf:match.start()].strip():
            return
        line = match.group().strip()
        name_match = _MACRO_NAME_RE.match(line)
        if not name_match:
            return
        name = name_match.group()
        if self.function_macro.match(line):
            self.finish(match.end(), forced='function')
        elif _GENERATED_RE.match(name):
            self.finish(match.end(), forced='neutral')

    def open_body(self, position):
        frame = self.frames[-1]
        head = self.shown(frame.buf, position)
        if frame.paren:
            self.open_frame(position, 'init', 'init', frame.access, frame.name)
            return
        keyword = type_keyword(head)
        if keyword:
            role = 'nested_type' if frame.kind == 'type' else 'file_type'
            self.open_frame(position, role, 'type', _CLASS_DEFAULT_ACCESS[keyword],
                            type_name(head))
            return
        if _ENUM_RE.match(_declaration_head(head)):
            role = 'nested_enum' if frame.kind == 'type' else 'file_enum'
            self.open_frame(position, role, 'enum', frame.access, type_name(head))
            return
        if frame.kind in ('file', 'namespace'):
            if _NAMESPACE_RE.match(_declaration_head(head)):
                self.open_frame(position, 'namespace', 'namespace', frame.access,
                                type_name(head))
            else:
                self.open_frame(position, 'skip', 'skip', frame.access, frame.name)
            return
        if brace_role(head, self.function_macro) == 'function':
            self.open_frame(position, 'function', 'skip', frame.access, frame.name)
        else:
            self.open_frame(position, 'init', 'init', frame.access, frame.name)


def analyze(text, function_macro):
    """(violations, body count) for one header text."""
    scan = _Scan(clean_text(text), function_macro)
    violations, bodies = scan.run()
    return violations, len(bodies)


def check_source(text, path_label, function_macro):
    violations, body_count = analyze(text, function_macro)
    for violation in violations:
        violation['path'] = path_label
    return violations, body_count


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

def is_header(path):
    return path.lower().endswith(HEADER_SUFFIXES)


# --------------------------------------------------------------------------
# Exclusions
# --------------------------------------------------------------------------

EXCLUDED_REASON = 'excluded by --exclude/--exclude-from'


def _slashed(text):
    """`text` with forward slashes, the form the matcher compares paths in."""
    return text.replace('\\', '/').strip()


def _normalize_pattern(text):
    """A pattern in matcher form: forward slashes, no leading ``./``, no trailing ``/``."""
    pattern = _slashed(text)
    while pattern.startswith('./'):
        pattern = pattern[2:]
    return pattern.rstrip('/')


def _is_absolute(pattern):
    return os.path.isabs(pattern) or re.match(r'^[A-Za-z]:/', pattern) is not None


def glob_regex(pattern):
    """The regex of one exclude pattern, anchored on path-component boundaries."""
    body = []
    index = 0
    length = len(pattern)
    while index < length:
        char = pattern[index]
        if char == '*':
            if pattern.startswith('**', index):
                index += 2
                if index < length and pattern[index] == '/':
                    index += 1
                    body.append('(?:.*/)?')
                else:
                    body.append('.*')
                continue
            index += 1
            body.append('[^/]*')
            continue
        if char == '?':
            index += 1
            body.append('[^/]')
            continue
        body.append(re.escape(char))
        index += 1
    # A pattern may begin at any component boundary, and it also covers every path
    # below the one it names, so a bare directory name prunes its whole subtree.
    return re.compile('(?:^|/)' + ''.join(body) + r'(?:/.*)?$', re.IGNORECASE)


def read_exclude_file(path):
    """The glob patterns of a list file: one per line, ``#`` starts a comment."""
    patterns = []
    with open(path, encoding='utf-8-sig', errors='replace') as handle:
        for line in handle:
            pattern = line.split('#', 1)[0].strip()
            if pattern:
                patterns.append(pattern)
    return patterns


def _relative_to(path, root):
    """`path` relative to `root`, forward slashed, or '' across drives."""
    try:
        return _normalize_pattern(os.path.relpath(path, root))
    except ValueError:
        return ''


class Excluder(object):
    """The compiled `--exclude` patterns; without one, nothing is excluded."""

    def __init__(self):
        self.rules = []

    def add(self, pattern, base_dir=None):
        text = _normalize_pattern(pattern)
        if not text:
            return
        forms = [text]
        if base_dir and not _is_absolute(text):
            resolved = _normalize_pattern(os.path.normpath(os.path.join(base_dir, text)))
            if resolved and resolved != text:
                forms.append(resolved)
        for form in forms:
            self.rules.append(glob_regex(form))

    def add_file(self, path):
        """Read a list file; its relative patterns also resolve against its directory."""
        base_dir = os.path.dirname(os.path.abspath(path))
        for pattern in read_exclude_file(path):
            self.add(pattern, base_dir)

    def __bool__(self):
        return bool(self.rules)

    def matches(self, candidates):
        """True when any candidate path is covered by any pattern."""
        if not self.rules:
            return False
        for candidate in candidates:
            text = _slashed(candidate) if candidate else ''
            if not text:
                continue
            for rule in self.rules:
                if rule.search(text):
                    return True
        return False


def collect_paths(entries, excluder=None):
    """(headers, skipped, excluded count) for `--path` entries, recursing into directories.

    An exclude pattern is tested against the path as given, its path relative to the
    scanned root and its absolute form, so one pattern works from any root.
    """
    excluder = excluder or Excluder()
    headers = []
    skipped = []
    excluded = 0
    for entry in entries:
        if excluder.matches([entry, os.path.abspath(entry)]):
            skipped.append({'path': entry, 'reason': EXCLUDED_REASON})
            excluded += 1
            continue
        if os.path.isdir(entry):
            found = []
            excluded_before = excluded
            for dirpath, dirnames, filenames in os.walk(entry):
                kept = []
                for name in sorted(dirnames):
                    if name in SKIP_DIRS or name.startswith('.'):
                        continue
                    child = os.path.join(dirpath, name)
                    if excluder.matches([child, _relative_to(child, entry),
                                         os.path.abspath(child)]):
                        skipped.append({'path': child, 'reason': EXCLUDED_REASON})
                        excluded += 1
                        continue
                    kept.append(name)
                dirnames[:] = kept
                for filename in sorted(filenames):
                    if not is_header(filename):
                        continue
                    path = os.path.join(dirpath, filename)
                    if excluder.matches([path, _relative_to(path, entry),
                                         os.path.abspath(path)]):
                        excluded += 1
                        continue
                    found.append(path)
            if not found:
                skipped.append({'path': entry,
                                'reason': EXCLUDED_REASON if excluded > excluded_before
                                else 'no header under this directory'})
            headers.extend(found)
        elif os.path.exists(entry):
            if is_header(entry):
                headers.append(entry)
            else:
                skipped.append({'path': entry, 'reason': 'not a header (.h/.hpp/.inl)'})
        else:
            skipped.append({'path': entry, 'reason': 'does not exist'})
    return headers, skipped, excluded


def git_diff(rev):
    command = ['git', 'diff', '--name-only']
    if rev:
        command.append(rev)
    try:
        completed = subprocess.run(command, capture_output=True, text=True)
    except OSError as error:
        raise SystemExit('check_member_order.py: git diff failed (%s) - pass --changed instead'
                         % error)
    if completed.returncode != 0:
        message = completed.stderr.strip() or 'exit %d' % completed.returncode
        raise SystemExit('check_member_order.py: git diff failed (%s) - pass --changed instead'
                         % message)
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def render_text(paths, violations, skipped, body_count, elapsed):
    by_path = {}
    for violation in violations:
        by_path.setdefault(violation['path'], []).append(violation)
    summary = 'check_member_order: %d header(s), %d type body(ies)' % (len(paths), body_count)
    if violations:
        summary += ' - %d violation(s) in %d file(s)' % (len(violations), len(by_path))
    else:
        summary += ' - clean, no data member follows a function member'
    out = [summary]
    for skipped_entry in skipped:
        out.append('  skipped %s (%s)' % (skipped_entry['path'], skipped_entry['reason']))
    for path in paths:
        found = by_path.get(path)
        if not found:
            continue
        out.append('')
        out.append('%s' % path)
        out.append('  rule: %s' % RULE)
        for violation in found:
            out.append('  %s:%d:%d   data member \'%s\' is declared after function member '
                       '\'%s\' (line %d)'
                       % (path, violation['line'], violation['column'],
                          violation['member'], violation['after_member'],
                          violation['after_line']))
    if not violations:
        out.append('every label group is ordered data first, then functions')
    out.append('')
    out.append('%.3fs' % elapsed)
    return '\n'.join(out)


def render_json(paths, violations, skipped, body_count, elapsed):
    return json.dumps({
        'rule': RULE,
        'checked': paths,
        'skipped': skipped,
        'bodies': body_count,
        'violations': violations,
        'counts': {'files': len(paths), 'bodies': body_count,
                   'violations': len(violations)},
        'seconds': round(elapsed, 3),
    }, indent=2)


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

FIXTURES = [
    # (name, source, expected displays of the flagged data members, in order)
    ('violation: data after a function in one access group',
     'struct FFoo\n{\n    void Bar();\n    int32 Count;\n};\n', ['int32 Count']),
    ('violation: data after an inline definition',
     'struct FFoo\n{\n    void Bar() { int32 Local = 0; (void)Local; }\n    int32 Count;\n};\n',
     ['int32 Count']),
    ('violation: cross access group',
     'struct FFoo\n{\n    void Bar();\n\nprotected:\n    float Speed;\n};\n', ['float Speed']),
    ('violation: protected group after a public function group in a class',
     'class FFoo\n{\npublic:\n    void Bar();\n\nprotected:\n    int32 Count;\n};\n',
     ['int32 Count']),
    ('violation: after a macro-generated function member',
     'struct FFoo\n{\n    REM_DEFINE_THE_RULE_OF_FIVE(FFoo)\n\n    int32 Count;\n};\n',
     ['int32 Count']),
    ('violation: inside a nested type, not in the outer type',
     'struct FOuter\n{\n    struct FInner\n    {\n        void Bar();\n        int32 Count;\n    };\n\n'
     '    void Baz();\n};\n', ['int32 Count']),
    ('violation: two separate data runs after functions',
     'struct FFoo\n{\n    void Bar();\n    int32 A;\n    void Baz();\n    int32 B;\n};\n',
     ['int32 A', 'int32 B']),
    ('violation: data after a pure virtual function',
     'struct IFoo\n{\n    virtual void Bar() = 0;\n    int32 Count;\n};\n', ['int32 Count']),
    # clean cases: the classic false positives
    ('clean: template argument holding parens',
     'struct FFoo\n{\n    TFunction<void(const APawn*)> Predicate;\n    void Bar();\n};\n', []),
    ('clean: call in a default initializer',
     'struct FFoo\n{\n    FMyType Alias = Make();\n    void Bar();\n};\n', []),
    ('clean: bitfields',
     'struct FFoo\n{\n    uint8 bCached : 1{false};\n    uint8 bOther : 3;\n    void Bar();\n};\n', []),
    ('clean: multi-line UPROPERTY data then functions',
     'struct FFoo\n{\n    UPROPERTY(EditAnywhere, Category = "Rem",\n        meta = (ClampMin = 0))\n'
     '    float Speed{};\n\n    void Bar();\n};\n', []),
    ('clean: using alias after data',
     'struct FFoo\n{\n    int32 Count{};\n    using ThisClass = FFoo;\n    void Bar();\n};\n', []),
    ('clean: enum class enumerators are not members',
     'struct FFoo\n{\n    enum class EMode : uint8\n    {\n        First,\n        Second\n    };\n\n'
     '    EMode Mode{};\n    void Bar();\n};\n', []),
    ('clean: lambda in an in-class initializer',
     'struct FFoo\n{\n    TFunction<void(int32)> Callback = [](int32 Value) { (void)Value; };\n'
     '    void Bar();\n};\n', []),
    ('clean: data first, then a pure virtual',
     'struct IFoo\n{\n    int32 Count{};\n    virtual void Bar() = 0;\n};\n', []),
    ('clean: first label omitted in a struct',
     'struct FFoo\n{\n    int32 Count{};\n\n    void Bar();\n};\n', []),
    ('clean: generated body, attributes, defaults',
     'struct FFoo\n{\n    GENERATED_BODY()\n\n    int32 Count{};\n\n    [[nodiscard]] int32 Get() const;\n'
     '    void Set(int32 InCount);\n};\n', []),
    ('clean: function pointer member is data',
     'struct FFoo\n{\n    void (*Callback)(int32);\n    void Bar();\n};\n', []),
    ('clean: operators and rule of five after data',
     'struct FFoo\n{\n    int32 Count{};\n\n    bool operator==(const FFoo& Other) const;\n'
     '    FFoo() = default;\n    FFoo(const FFoo&) = delete;\n    ~FFoo() noexcept = default;\n'
     '};\n', []),
    ('clean: trailing return type definition after data',
     'struct FFoo\n{\n    int32 Count{};\n    auto Get() const -> int32 { return Count; }\n};\n', []),
    ('clean: constructor with an initializer list and a body after data',
     'struct FFoo\n{\n    int32 Count{};\n    FFoo() : Count{0} { }\n};\n', []),
    ('clean: member template function after data',
     'struct FFoo\n{\n    int32 Count{};\n    template <typename T = void>\n    TArray<T> Make(T Value) const;\n};\n', []),
    ('violation: after a member template function',
     'struct FFoo\n{\n    template <typename T>\n    void Set(T Value);\n    int32 Count{};\n};\n',
     ['int32 Count{}']),
]

EXCLUDE_FIXTURES = [
    # (name, patterns, path, expected)
    ('exclude: a wildcard file name',
     ['**/*.generated.h'], '/Tree/Plugins/Game/Source/Foo.generated.h', True),
    ('exclude: a directory name covers everything below it',
     ['ue5coro'], '/Tree/Plugins/ue5coro/Source/Private/UE5Coro.h', True),
    ('exclude: ** crosses several directories',
     ['**/ThirdParty/**'], '/Tree/Plugins/Foo/Source/ThirdParty/Lib/Include/Bar.h', True),
    ('exclude: a case difference still matches',
     ['ue5coro'], '/Tree/Plugins/UE5Coro/Source/UE5Coro.h', True),
    ('exclude: a shared prefix is not a match',
     ['Game'], '/Tree/Plugins/Gameplay/Source/AGameplay.h', False),
    ('exclude: an unrelated path is not a match',
     ['ue5coro', 'FlowGraph/**'], '/Tree/Plugins/Game/Source/AGame.h', False),
    ('exclude: a path prefix written with a trailing slash',
     ['FlowGraph/'], '/Tree/Plugins/FlowGraph/Source/AFlow.h', True),
    ('exclude: a multi-component prefix starts mid-path',
     ['Runtime/ECS'], '/Tree/Plugins/Runtime/ECS/Public/ECS.h', True),
]


def _excludes(path, patterns, base_dir=None):
    excluder = Excluder()
    for pattern in patterns:
        excluder.add(pattern, base_dir)
    return excluder.matches([path])


def _exclude_file_fixtures():
    """(name, ok) pairs for patterns read from a list file, then the file is gone."""
    directory = tempfile.mkdtemp(prefix='check_member_order_')
    try:
        lists = os.path.join(directory, 'lists')
        os.makedirs(lists)
        list_file = os.path.join(lists, 'excludes.txt')
        with open(list_file, 'w', encoding='utf-8') as handle:
            handle.write('# vendored plugins, one glob per line\n'
                         '\n'
                         'ue5coro   # the coroutine library\n'
                         '../Vendored/**\n')
        excluder = Excluder()
        excluder.add_file(list_file)
        return [
            ('exclude: a pattern read from a list file',
             excluder.matches(['/Tree/Plugins/ue5coro/Source/UE5Coro.h'])),
            ('exclude: a list-file pattern relative to the file directory',
             excluder.matches([os.path.join(directory, 'Vendored', 'Lib', 'AVendored.h')])),
            ('exclude: a list file leaves unrelated paths alone',
             not excluder.matches(['/Tree/Plugins/Game/Source/AGame.h'])),
        ]
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def self_test(function_macro):
    failures = []
    for name, source, expected in FIXTURES:
        violations, _ = check_source(source, '<fixture>', function_macro)
        found = [violation['member'] for violation in violations]
        if found != expected:
            failures.append('%s: expected %r, got %r' % (name, expected, found))
    exclude_cases = 0
    for name, patterns, path, expected in EXCLUDE_FIXTURES:
        exclude_cases += 1
        got = _excludes(path, patterns)
        if got != expected:
            failures.append('%s: expected %r, got %r' % (name, expected, got))
    for name, ok in _exclude_file_fixtures():
        exclude_cases += 1
        if not ok:
            failures.append('%s: unexpected result' % name)
    total = len(FIXTURES) + exclude_cases
    if failures:
        print('check_member_order.py: SELF-TEST FAILED - %d of %d fixture(s) wrong'
              % (len(failures), total), file=sys.stderr)
        for failure in failures:
            print('  ' + failure, file=sys.stderr)
        return 1
    print('check_member_order.py: self-test passed - %d fixture(s): %d parsing case(s) '
          '(%d violation, %d clean), %d exclude case(s)'
          % (total, len(FIXTURES), sum(1 for item in FIXTURES if item[2]),
             sum(1 for item in FIXTURES if not item[2]), exclude_cases))
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--path', action='append', default=None,
                        help='header or directory to check (repeatable); directories recurse')
    parser.add_argument('--changed', action='append', default=None,
                        help='explicit changed-file list (repeatable), non-headers skipped')
    parser.add_argument('--diff', nargs='?', const='HEAD', default=None,
                        help='use "git diff --name-only [REV]"; default REV is HEAD')
    parser.add_argument('--exclude', action='append', default=None, metavar='GLOB',
                        help='path glob to skip (repeatable); a matching directory prunes '
                             'the walk, a bare name matches at any depth')
    parser.add_argument('--exclude-from', dest='exclude_from', action='append', default=None,
                        metavar='FILE',
                        help='file of exclude globs, one per line (# starts a comment, blank '
                             'lines ignored, a relative pattern also resolves against its '
                             'own directory); repeatable')
    parser.add_argument('--function-macro', dest='function_macro', default=r'^REM_DEFINE_',
                        help='regex of a macro that expands to member functions '
                             '(default: ^REM_DEFINE_)')
    parser.add_argument('--json', action='store_true', help='machine-readable output')
    parser.add_argument('--self-test', dest='self_test', action='store_true',
                        help='run the built-in fixtures and exit')
    args = parser.parse_args(argv)

    try:
        function_macro = re.compile(args.function_macro)
    except re.error as error:
        print('check_member_order.py: --function-macro is not a regex (%s)' % error,
              file=sys.stderr)
        return 2

    if args.self_test:
        return self_test(function_macro)

    if not (args.path or args.changed or args.diff is not None):
        print('check_member_order.py: no input - pass --path, --changed or --diff '
              '(accepting nothing is never a clean result)', file=sys.stderr)
        return 2

    excluder = Excluder()
    for pattern in args.exclude or []:
        excluder.add(pattern)
    for list_file in args.exclude_from or []:
        try:
            excluder.add_file(list_file)
        except (OSError, UnicodeError) as error:
            print('check_member_order.py: cannot read --exclude-from %s (%s)'
                  % (list_file, error), file=sys.stderr)
            return 2

    given = list(args.path or [])
    given.extend(args.changed or [])
    entries = list(given)
    diff_lines = []
    if args.diff is not None:
        try:
            diff_lines = git_diff(args.diff)
        except SystemExit as error:
            print(error, file=sys.stderr)
            return 2
        for line in diff_lines:
            if is_header(line) and os.path.exists(line):
                entries.append(line)

    headers, skipped, excluded = collect_paths(entries, excluder)
    missing = [entry for entry in skipped if entry['reason'] == 'does not exist']
    if missing:
        for entry in missing:
            print('check_member_order.py: %s does not exist' % entry['path'], file=sys.stderr)
        return 2
    # A diff names files relative to the repository root; a file of the diff that
    # vanished (deleted) is not an error, but nothing readable is.
    unique = []
    seen = set()
    for header in headers:
        key = os.path.normcase(os.path.abspath(header))
        if key not in seen:
            seen.add(key)
            unique.append(header)
    if not unique:
        detail = ''
        if excluded:
            detail = (' - %d path(s) dropped by --exclude/--exclude-from'
                      % excluded)
        print('check_member_order.py: no header reached (%d path(s) given, %d from the diff, '
              '%d skipped)%s - refusing to report a clean result'
              % (len(given), len(diff_lines), len(skipped), detail), file=sys.stderr)
        return 2

    started = time.monotonic()
    violations = []
    body_count = 0
    for header in unique:
        try:
            text = read_text(header)
        except OSError as error:
            print('check_member_order.py: cannot read %s (%s)' % (header, error),
                  file=sys.stderr)
            return 2
        found, bodies = check_source(text, header, function_macro)
        violations.extend(found)
        body_count += bodies
    elapsed = time.monotonic() - started

    if args.json:
        print(render_json(unique, violations, skipped, body_count, elapsed))
    else:
        print(render_text(unique, violations, skipped, body_count, elapsed))
    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main())
