#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BDD test case tree generator (UE automation specs).

Parses *.spec.cpp files (DEFINE_SPEC / Describe / It) and renders a
hierarchical markdown index with [file:line] anchors on every leaf.

Usage:
    python gen_test_tree.py [--root <dir> ...] [--output <path>]

Defaults: scans 'Plugins' and 'Source' under the current directory; writes a
uniquely-named file under Intermediate/Test/. Stdlib only, Python 3.x.
"""
import argparse
import os
import random
import re
import string
import time

SPEC_LINE = re.compile(r'DEFINE_SPEC\(\w+,\s*"([^"]+)"')
NODE_LINE = re.compile(r'\b(Describe|It)\(TEXT\("([^"]*)"')
SKIP_DIRS = ('Intermediate', 'Binaries', 'ThirdParty')


def parse_spec(path):
    """Returns (spec_name, items) where items are (indent, kind, name, line)."""
    with open(path, encoding='utf-8-sig') as file:
        lines = file.read().split('\n')

    spec_name = None
    items = []

    def extract_name(line, index):
        match = NODE_LINE.search(line)
        if not match:
            return None
        name = match.group(2)
        # the name may continue on the following lines (multi-line literal)
        if not match.group(0).rstrip().endswith('"'):
            for extra in range(1, 4):
                if index + extra >= len(lines):
                    break
                continuation = lines[index + extra].split('"')[0]
                name += continuation
                if '"' in lines[index + extra]:
                    break
        return match.group(1), name

    for index, line in enumerate(lines):
        match = SPEC_LINE.search(line)
        if match and spec_name is None:
            spec_name = match.group(1)
            continue
        node = extract_name(line, index)
        if node:
            kind, name = node
            indent = len(line) - len(line.lstrip())
            items.append((indent, kind, name, index + 1))

    return spec_name, items


def build_tree(items):
    """Builds [kind, name, line, children] nodes keyed by indentation."""
    root = []
    stack = [(root, -1)]
    for indent, kind, name, line in items:
        while len(stack) > 1 and stack[-1][1] >= indent:
            stack.pop()
        node = [kind, name, line, []]
        stack[-1][0].append(node)
        stack.append((node[3], indent))
    return root


def render(nodes, depth, out, rel):
    for node in nodes:
        kind, name, line, children = node
        if kind == 'Describe':
            out.append('  ' * depth + '- ' + name)
        else:
            out.append('  ' * depth + '- ' + name + '  `[' + rel + ':' + str(line) + ']`')
        render(children, depth + 1, out, rel)


def collect_specs(roots):
    """Returns {module: [(spec_name, full_path, items)]}."""
    modules = {}
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for filename in filenames:
                if not filename.endswith('.spec.cpp'):
                    continue
                full = os.path.join(dirpath, filename)
                spec_name, items = parse_spec(full)
                if not spec_name:
                    continue
                parts = spec_name.split('.')
                module = '.'.join(parts[:2]) if len(parts) >= 2 else parts[0]
                modules.setdefault(module, []).append((spec_name, full, items))
    return modules


def make_output_path(explicit):
    if explicit:
        return explicit
    out_dir = os.path.join('Intermediate', 'Test')
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime('%Y%m%d_%H%M%S', time.gmtime())
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return os.path.join(out_dir, 'test_tree_' + stamp + '_' + suffix + '.md')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', default=None,
                        help='scan root directory (repeatable); default: Plugins and Source')
    parser.add_argument('--output', default=None,
                        help='explicit output path; default: Intermediate/Test/<unique>.md')
    args = parser.parse_args()

    roots = args.root or ['Plugins', 'Source']
    out = [
        '# BDD 测试用例树（自动生成，勿手改）',
        '',
        '> 生成方式：解析 `*.spec.cpp` 的 `DEFINE_SPEC` / `Describe` / `It` 结构；',
        '> 用例数为静态解析近似值。重新生成：`python gen_test_tree.py`。',
        '> 用途：测试审查索引——叶子挂 [文件:行号] 锚点，从树直接跳转源码。',
        '',
    ]

    modules = collect_specs(roots)
    total = 0
    for module in sorted(modules):
        module_total = sum(sum(1 for item in items if item[1] == 'It')
                           for _, _, items in modules[module])
        total += module_total
        out.append('## ' + module + '  (' + str(module_total) + ' 个用例)')
        out.append('')
        for spec_name, full, items in sorted(modules[module], key=lambda entry: entry[0]):
            rel = full.replace(os.sep, '/')
            it_count = sum(1 for item in items if item[1] == 'It')
            out.append('### ' + spec_name + '  (' + str(it_count) + ' 个用例)  `[' + rel + ']`')
            out.append('')
            render(build_tree(items), 0, out, rel)
            out.append('')

    out.append('')
    out.append('**总计：' + str(total) + ' 个用例（静态解析，与运行器计数可能略有出入）**')
    out.append('')

    output_path = make_output_path(args.output)
    with open(output_path, 'w', encoding='utf-8', newline='\n') as file:
        file.write('\n'.join(out))
    print('wrote', output_path, '| total =', total)


if __name__ == '__main__':
    main()
