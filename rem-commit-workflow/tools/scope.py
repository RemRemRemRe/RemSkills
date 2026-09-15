#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test-scope candidate set for a change set, from the module dependency graph.

Enumerates which automation test prefixes can reach a change **before** the
symbol-level pruning step - and, just as importantly, which prefixes cannot.
Running the suite without the first half is how a scope turns from too wide
into too narrow; keeping the candidates after pruning is how it turns back into
noise.

Data sources (all on disk, no IDE, stdlib only):

  * ``<...>/Source/<Module>/<Module>.Build.cs`` - the module inventory and its
    Public/Private dependency lists (the graph edges).
  * ``<...>/*.spec.cpp`` - ``DEFINE_SPEC(<type>, "<Prefix>.<Describe>...")``;
    the first two dot-segments of the spec name are the automation prefix, and
    the module owning the file is the test module. The prefix is read from the
    spec name, never guessed from the module name - the two differ in practice
    (a test module may host a prefix that does not repeat its own name, and one
    test module may host several prefixes).

Reach rule: a module can see the changed module's headers when it lists the
changed module directly, or when it lists any module on the changed module's
*public*-dependency closure - the same propagation UBT applies to public
dependencies. ``Private`` edges do not propagate to third parties.

Usage::

    python tools/scope.py --root <plugin-root> [--root <source-root>] --diff [REV]
    python tools/scope.py --root <plugin-root> --changed <file> [--changed <file>]
    python tools/scope.py --root <plugin-root> --changed-from <file|-> [--json]
    python tools/scope.py --root <plugin-root> --module <Module> [--module <Module>]
    python tools/scope.py --root <plugin-root> --list
    python tools/scope.py [--root <plugin-root>] --spec <spec-file> [--spec <spec-file>]

``--diff`` reads ``git diff --name-only [REV]`` (default ``REV`` = HEAD, i.e. the
working tree); ``--module`` seeds the graph directly, for a hypothetical change;
``--spec`` turns a stage-2 hit back into the prefix to run - the prefix comes from
that file's own ``DEFINE_SPEC`` name, never from its module, because one test
module can host several prefixes.

Exit codes: 0 - inventory built; 2 - no module inventory, or not one changed
file could be mapped (a wrong ``--root`` must not read as "nothing to run").

Limits, by design: the dependencies are text-parsed from ``Build.cs`` (a
statement-scoped scan of the two dependency lists, so a list built by a helper
function outside those statements is invisible - check that the parsed list of
the seed module is the one the build uses); a spec module outside the scanned
roots is invisible, so scan every root that can hold a consumer.
"""

import argparse
import json
import os
import re
import subprocess
import sys

SKIP_DIRS = ('Intermediate', 'Binaries', 'ThirdParty', '.git', 'node_modules')
SPEC_RE = re.compile(r'DEFINE_SPEC\(\w+,\s*"([^"]+)"')
QUOTED_RE = re.compile(r'"([^"]+)"')
DEP_KEYS = ('PublicDependencyModuleNames', 'PrivateDependencyModuleNames')


def to_posix(path):
    return os.path.normpath(path).replace(os.sep, '/')


def read_text(path):
    with open(path, encoding='utf-8-sig', errors='replace') as handle:
        return handle.read()


def walk_named(roots, suffix):
    """Yields every file ending in `suffix` under `roots`, skipping build dirs."""
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
            for filename in filenames:
                if filename.endswith(suffix):
                    yield os.path.join(dirpath, filename)


def scan_modules(roots):
    """{module: {'dir', 'public', 'private'}} from every ``*.Build.cs`` under `roots`."""
    modules = {}
    for build_cs in walk_named(roots, '.Build.cs'):
        name = os.path.basename(build_cs)[: -len('.Build.cs')]
        text = read_text(build_cs)
        deps = {}
        for key in DEP_KEYS:
            kind = key[: -len('DependencyModuleNames')]
            found = set()
            start = 0
            while True:
                at = text.find(key, start)
                if at < 0:
                    break
                end = text.find(';', at)
                found.update(QUOTED_RE.findall(text[at : end if end > 0 else len(text)]))
                start = at + len(key)
            deps[kind] = found
        modules[name] = {
            'dir': to_posix(os.path.dirname(build_cs)),
            'public': deps['Public'],
            'private': deps['Private'],
        }
    return modules


def scan_specs(roots):
    """{test module: {prefix: [spec file]}} from every ``*.spec.cpp``."""
    specs = {}
    for spec in walk_named(roots, '.spec.cpp'):
        match = SPEC_RE.search(read_text(spec))
        if not match:
            continue
        parts = match.group(1).split('.')
        prefix = '.'.join(parts[:2]) if len(parts) >= 2 else parts[0]
        posix = to_posix(spec)
        owner = posix.split('/Source/')[-1].split('/')[0] if '/Source/' in posix else '(no Source dir)'
        specs.setdefault(owner, {}).setdefault(prefix, []).append(posix)
    return specs


def plugin_of(module, modules):
    """The plugin/root directory owning a module (its ``Source`` folder's parent)."""
    directory = modules.get(module, {}).get('dir')
    if not directory or '/Source/' not in directory + '/':
        return None
    return directory.rsplit('/Source/', 1)[0]


def resolve_module(path, modules):
    """(module, how) owning `path`, or (None, reason)."""
    posix = to_posix(path)
    absolute = to_posix(os.path.abspath(path)) if os.path.exists(path) else None
    for candidate in (absolute, posix):
        if not candidate:
            continue
        contained = [name for name, entry in modules.items()
                     if candidate == entry['dir'] or candidate.startswith(entry['dir'] + '/')]
        if contained:
            return max(contained, key=lambda name: len(modules[name]['dir'])), 'path'
    # A repo-relative path from another working directory still carries the
    # module layout, so fall back to the '<...>/Source/<Module>/' segment.
    probe = posix if posix.startswith('/') else '/' + posix
    segmented = [name for name in modules if '/Source/%s/' % name in probe]
    if not segmented:
        segmented = [name for name in modules if probe.endswith('/Source/%s' % name)]
    if segmented:
        best = max(segmented, key=lambda name: probe.index('/Source/%s/' % name)
                   if '/Source/%s/' % name in probe else len(probe))
        return best, 'source-segment'
    if absolute and os.path.isdir(path):
        # A submodule/gitlink shows up in the parent repository as a directory,
        # not as the files inside it - the diff has to be taken in the submodule.
        inside = [name for name, entry in modules.items()
                  if entry['dir'].startswith(absolute + '/')]
        if inside:
            return None, ('directory holding %d module(s) - take the diff inside it '
                          '(git -C <path> diff --name-only), or seed --module <name>'
                          % len(inside))
    return None, 'no <...>/Source/<Module>/ segment matching a scanned module'


def public_reach(seed, modules):
    """{module: distance} over public edges from `seed`, plus {module: parent}."""
    distance = {seed: 0}
    parent = {seed: None}
    queue = [seed]
    while queue:
        current = queue.pop(0)
        for dep in sorted(modules.get(current, {}).get('public', ())):
            if dep not in distance:
                distance[dep] = distance[current] + 1
                parent[dep] = current
                queue.append(dep)
    return distance, parent


def consumer_path(module, seed, parent):
    chain = [module]
    while parent.get(chain[-1]) is not None:
        chain.append(parent[chain[-1]])
    return list(reversed(chain))


def find_consumers(seed, modules):
    """Consumers of `seed`, with the shortest public path and the matching edge kind."""
    distance, parent = public_reach(seed, modules)
    distance[seed] = 0
    consumers = []
    for name in sorted(modules):
        if name == seed:
            continue
        own = modules[name]
        matches = []
        for dep in sorted((own['public'] | own['private']) & set(distance)):
            kind = 'public' if dep in own['public'] else 'private'
            matches.append((distance[dep], dep, kind))
        if matches:
            _, dep, kind = min(matches)
            consumers.append({
                'module': name,
                'via': dep,
                'edge': kind,
                'path': consumer_path(dep, seed, parent),
            })
    return consumers, distance


def seed_modules(args, modules):
    """[(module, how)] for this run's seeds, plus the unmapped changed files."""
    seeds = []
    unmapped = []
    if args.module:
        for name in args.module:
            if name in modules:
                seeds.append((name, 'named with --module'))
            else:
                unmapped.append({'path': name, 'reason': 'not a module of the scanned roots'})
    changed = list(args.changed or [])
    if args.diff is not None:
        command = ['git', 'diff', '--name-only']
        if args.diff:
            command.append(args.diff)
        try:
            out = subprocess.run(command, capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as error:
            print('scope.py: git diff failed (%s) - pass --changed instead' % error, file=sys.stderr)
            sys.exit(2)
        changed.extend(out.splitlines())
    if args.changed_from:
        text = sys.stdin.read() if args.changed_from == '-' else read_text(args.changed_from)
        changed.extend(text.splitlines())
    for path in changed:
        path = path.strip()
        if not path:
            continue
        name, how = resolve_module(path, modules)
        if name:
            seeds.append((name, path))
        else:
            unmapped.append({'path': path, 'reason': how})
    seen = set()
    unique = []
    for name, how in seeds:
        if name not in seen:
            seen.add(name)
            unique.append((name, how))
    return unique, unmapped, changed


def collect(seeds, modules, specs):
    """Candidate and unreachable prefixes over every affected module."""
    every_prefix = sorted(prefix_files(specs))
    candidates = {}
    reachable = set()
    for seed, _ in seeds:
        consumers, _ = find_consumers(seed, modules)
        affected = [seed] + [entry['module'] for entry in consumers]
        reachable.update(affected)
        for name in affected:
            for prefix in sorted(specs.get(name, {})):
                record = candidates.setdefault(prefix, {'prefix': prefix, 'reasons': []})
                if name == seed:
                    record['reasons'].append('specs of the seed module %s' % name)
                elif plugin_of(name, modules) and plugin_of(name, modules) == plugin_of(seed, modules):
                    record['reasons'].append('own test module %s' % name)
                else:
                    match = next(e for e in consumers if e['module'] == name)
                    hops = ''.join(' -> ' + step for step in match['path'][:-1])
                    record['reasons'].append('%s --%s--> %s%s'
                                             % (name, match['edge'], match['via'], hops))
    unreachable = [prefix for prefix in every_prefix if prefix not in candidates]
    return candidates, unreachable, reachable, every_prefix


def prefix_files(specs):
    """{prefix: set of spec file paths}."""
    counts = {}
    for entry in specs.values():
        for prefix, files in entry.items():
            counts.setdefault(prefix, set()).update(files)
    return counts


def render(args, modules, specs, seeds, unmapped, candidates, unreachable, total_prefixes):
    out = []
    counts = prefix_files(specs)
    width = max([len(prefix) for prefix in counts] + [10]) + 2
    out.append('scope: %d seed module(s) -> %d candidate prefix(es), %d unreachable prefix(es)'
               % (len(seeds), len(candidates), len(unreachable)))
    out.append('inventory: %d module(s), %d prefix(es), %d spec file(s) from %s'
               % (len(modules), total_prefixes, len({f for files in counts.values() for f in files}),
                  ', '.join(display_roots(args))))
    out.append('')
    out.append('changed files')
    if not seeds and not unmapped:
        out.append('  (none - pass --diff, --changed, --changed-from or --module)')
    for name, how in seeds:
        if how == 'named with --module':
            kind = '(--module)'
        else:
            marker = 'public-header' if '/Public/' in to_posix(how) else (
                'private' if '/Private/' in to_posix(how) else 'other')
            kind = '%s [%s]' % (how, marker)
        out.append('  %-28s <- %s' % (name, kind))
    for entry in unmapped:
        out.append('  %-28s <- %s  (%s)' % ('(unmapped)', entry['path'], entry['reason']))
    out.append('')
    out.append('candidates (these prefixes can reach the change)')
    for prefix in sorted(candidates):
        record = candidates[prefix]
        out.append('  %-*s %3d spec file(s)  %s'
                   % (width, prefix, len(counts.get(prefix, ())),
                      '; '.join(sorted(set(record['reasons'])))))
    out.append('')
    out.append('unreachable (no spec module has a path to the seed)')
    if unreachable:
        for prefix in unreachable:
            out.append('  %-*s %3d spec file(s)' % (width, prefix, len(counts.get(prefix, ()))))
    else:
        out.append('  (none - every prefix is reachable)')
    out.append('')
    out.append('next: search each changed name (IDE text search / find usages), keep a candidate')
    out.append('only while a spec file of that prefix appears in the hits, and give every dropped')
    out.append('candidate one line of reason. The graph proves reachability, never usage.')
    if unmapped:
        out.append('')
        out.append('note: unmapped entries are outside every scanned module - a .uplugin, an .ini or')
        out.append('an asset reference changes behaviour project-wide; widen the scope by hand.')
    return '\n'.join(out)


def spec_prefixes(path):
    """[(prefix, spec name)] declared by one spec file, empty when it declares none."""
    declared = []
    for match in SPEC_RE.finditer(read_text(path)):
        parts = match.group(1).split('.')
        declared.append(('.'.join(parts[:2]) if len(parts) >= 2 else parts[0], match.group(1)))
    return declared


def render_spec(paths, roots, known_prefixes):
    """Stage-2 output: each spec file with the prefix its own DEFINE_SPEC declares."""
    out = ['spec file -> automation prefix']
    prefixes = []
    for path in paths:
        resolved = path if os.path.exists(path) else None
        if resolved is None:
            # A repo-relative path from another working directory: retry under each root.
            for root in roots:
                candidate = os.path.join(root, to_posix(path).lstrip('/'))
                if os.path.exists(candidate):
                    resolved = candidate
                    break
        if resolved is None:
            print('scope.py: %s does not exist (and no --root holds it)' % path, file=sys.stderr)
            sys.exit(2)
        posix = to_posix(os.path.abspath(resolved))
        module = posix.split('/Source/')[-1].split('/')[0] if '/Source/' in posix else '?'
        declared = spec_prefixes(resolved)
        if not declared:
            out.append('  %-24s (no DEFINE_SPEC found)  module %s' % ('-', module))
            out.append('      <- %s' % posix)
            continue
        for prefix, name in declared:
            out.append('  %-24s %s  (module %s)' % (prefix, name, module))
            out.append('      <- %s' % posix)
            prefixes.append(prefix)
    unique = sorted(set(prefixes))
    if not unique:
        print('\n'.join(out))
        print('scope.py: no DEFINE_SPEC prefix in the given spec file(s) - refusing to report an empty '
              'scope', file=sys.stderr)
        sys.exit(2)
    out.append('')
    out.append('filter (one run): ' + '+'.join('StartsWith:%s' % prefix for prefix in unique))
    out.append('every hit in these files belongs to the prefix printed for that file, whatever the')
    out.append('module is named.')
    if known_prefixes is not None:
        unknown = [prefix for prefix in unique if prefix not in known_prefixes]
        if unknown:
            out.append('')
            out.append('warn: %s is not declared by any spec under the scanned roots - check --root'
                       % ', '.join(unknown))
    return '\n'.join(out)


def display_roots(args):
    return args.roots_display or ['.']


def render_list(args, modules, specs):
    counts = prefix_files(specs)
    width = max([len(prefix) for prefix in counts] + [10]) + 2
    out = ['%d module(s) from %s' % (len(modules), ', '.join(display_roots(args))), '']
    out.append('%-*s %5s  %s' % (width, 'prefix', 'specs', 'test module(s)'))
    for prefix in sorted(counts):
        owners = sorted(name for name, entry in specs.items() if prefix in entry)
        out.append('%-*s %5d  %s' % (width, prefix, len(counts[prefix]), ', '.join(owners)))
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', action='append', default=None,
                        help='scan root directory (repeatable); default: current directory')
    parser.add_argument('--changed', action='append', default=None,
                        help='changed file path (repeatable)')
    parser.add_argument('--changed-from', dest='changed_from', default=None,
                        help='file with one changed path per line, or - for stdin')
    parser.add_argument('--diff', nargs='?', const='HEAD', default=None,
                        help='use "git diff --name-only [REV]"; default REV is HEAD (working tree)')
    parser.add_argument('--module', action='append', default=None,
                        help='seed module directly (repeatable), for a hypothetical change')
    parser.add_argument('--spec', action='append', default=None,
                        help='spec file whose own DEFINE_SPEC prefix should be printed (repeatable)')
    parser.add_argument('--list', action='store_true', help='print the prefix inventory and exit')
    parser.add_argument('--json', action='store_true', help='machine-readable output')
    args = parser.parse_args()

    if args.spec:
        spec_roots = [os.path.abspath(root) for root in (args.root or ['.'])]
        known = set(prefix_files(scan_specs(spec_roots))) if args.root else None
        print(render_spec(args.spec, spec_roots, known))
        return 0

    roots_display = args.root or ['.']
    args.roots_display = roots_display
    roots = [os.path.abspath(root) for root in roots_display]
    modules = scan_modules(roots)
    if not modules:
        print('scope.py: no *.Build.cs under %s - wrong --root? refusing to report an empty '
              'scope' % ', '.join(roots_display), file=sys.stderr)
        sys.exit(2)
    specs = scan_specs(roots)
    total_prefixes = len(prefix_files(specs))

    if args.list:
        print(render_list(args, modules, specs))
        return 0

    seeds, unmapped, changed = seed_modules(args, modules)
    if changed and not seeds:
        print('scope.py: none of the %d changed file(s) maps to a scanned module - refusing to '
              'report an empty scope' % len(changed), file=sys.stderr)
        for entry in unmapped:
            print('  %s  (%s)' % (entry['path'], entry['reason']), file=sys.stderr)
        sys.exit(2)

    candidates, unreachable, reachable, every_prefix = collect(seeds, modules, specs)
    if args.json:
        counts = prefix_files(specs)
        print(json.dumps({
            'roots': roots_display,
            'modules': len(modules),
            'seeds': [{'module': name, 'how': how} for name, how in seeds],
            'unmapped': unmapped,
            'candidates': [dict(candidates[p], spec_files=len(counts.get(p, ())))
                           for p in sorted(candidates)],
            'reachable_modules': sorted(reachable),
            'unreachable': [{'prefix': p, 'spec_files': len(counts.get(p, ()))}
                            for p in unreachable],
        }, indent=2))
        return 0
    print(render(args, modules, specs, seeds, unmapped, candidates, unreachable, total_prefixes))
    return 0


if __name__ == '__main__':
    sys.exit(main())
