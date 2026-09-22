#!/usr/bin/env node
// Outgoing-commit-message leak lint — zero dependencies, node built-ins only.
//
//   node tools/lint-commit-messages.mjs --repo <path> --range <git-range> [--terms <file>] [--json] [--allow-empty]
//
// Scans the commit messages of a git range for leaks before a public push:
// generic machine-path shapes plus every term in the terms file. The rules are
// owned by rem-public-material-generalization §4; the message discipline itself
// by rem-commit-workflow. The default terms file is that skill's ignored
// `local/forbidden-commit-terms.txt` overlay, linked in from the private
// repository that tracks the values — the term list must never live in a public
// file, so it is read, never printed.
//
// Terms file format: one term per line; blank lines and lines starting with `#`
// are ignored. Matching is case-insensitive substring.
//
// The file ships, so it carries no private term and no machine path.
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
/** The owning skill's overlay file: private terms, linked in from the private repo. */
const DEFAULT_TERMS = join(ROOT, "rem-public-material-generalization", "local", "forbidden-commit-terms.txt");

const USAGE = [
  "Usage: node tools/lint-commit-messages.mjs --repo <path> --range <git-range> [--terms <file>] [--json] [--allow-empty]",
  "",
  "  --repo        repository to read the commits from (required)",
  "  --range       git range to scan, e.g. origin/main..HEAD (required)",
  "  --terms       term file, one term per line (default: the owning skill's",
  "                local/forbidden-commit-terms.txt when it exists)",
  "  --json        print a JSON array of findings instead of text lines",
  "  --allow-empty accept a range that selects 0 commits (otherwise it is an error)",
].join("\n");

const argv = process.argv.slice(2);
const AS_JSON = argv.includes("--json");
const ALLOW_EMPTY = argv.includes("--allow-empty");
const warned = [];

function valueOf(flag) {
  const index = argv.indexOf(flag);
  if (index < 0) return null;
  const value = argv[index + 1];
  return value && !value.startsWith("--") ? value : null;
}

const repo = valueOf("--repo");
const range = valueOf("--range");
const termsFlag = valueOf("--terms");

if (!repo || !range) {
  console.error(`lint-commit-messages: --repo and --range are required\n\n${USAGE}`);
  process.exit(2);
}

/**
 * Machine-path shapes no commit message may contain, copied from the skill
 * collection lint so both halves of the check report the same leaks.
 */
const GENERIC_PATTERNS = [
  { re: /(?:^|[\s("'`\[])[A-Za-z]:[\\/]/m, what: "drive-letter path" },
  { re: /(?:^|[\s("'`\[])\/home\//m, what: "posix home directory" },
  { re: /(?:^|[\s("'`\[])\/Users\//m, what: "macOS home directory" },
];

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** A path safe to print: repo-relative when it is inside the repository, else
 * cwd-relative, else the bare file name — never an absolute drive-letter path. */
function displayPath(file) {
  const cwdRel = relative(process.cwd(), file);
  if (cwdRel && !cwdRel.startsWith("..")) return cwdRel;
  const repoRel = relative(resolve(repo), file);
  if (repoRel && !repoRel.startsWith("..")) return repoRel;
  return basename(file);
}

/** Load the terms file; `required` decides whether a missing file is fatal. */
function loadTerms(file, required) {
  if (!existsSync(file)) {
    if (required) {
      console.error(`lint-commit-messages: terms file not found: ${displayPath(file)}`);
      process.exit(2);
    }
    warned.push(
      `no terms file at ${displayPath(file)} — only the generic machine-path patterns ran; ` +
        "link the owning skill's local/ overlay or pass --terms <file>",
    );
    return [];
  }
  let text;
  try {
    text = readFileSync(file, "utf8");
  } catch (error) {
    console.error(
      `lint-commit-messages: cannot read terms file ${displayPath(file)} (${error.code ?? "read failed"})`,
    );
    process.exit(2);
  }
  const terms = [];
  for (const line of text.split(/\r?\n/)) {
    const term = line.trim();
    if (!term || term.startsWith("#")) continue;
    if (!terms.some((known) => known.toLowerCase() === term.toLowerCase())) terms.push(term);
  }
  return terms;
}

const termsFile = termsFlag ? resolve(termsFlag) : existsSync(DEFAULT_TERMS) ? DEFAULT_TERMS : null;
const terms = termsFile ? loadTerms(termsFile, Boolean(termsFlag)) : loadTerms(DEFAULT_TERMS, false);

/** `%h` / `%s` / `%B` separated by NUL, whole commits separated by NUL (`-z`):
 * a message can contain any text but never NUL, so the parse cannot be broken
 * by message content, and one call reads every commit. */
let output;
try {
  output = execFileSync(
    "git",
    ["-C", repo, "log", "-z", "--no-color", "--format=%h%x00%s%x00%B", range],
    { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
  );
} catch (error) {
  console.error(`lint-commit-messages: git log failed in ${repo} for range "${range}"`);
  const detail = String(error.stderr ?? error.message).trim();
  if (detail) console.error(detail);
  process.exit(2);
}

const parts = output.split("\0");
if (parts[parts.length - 1] === "") parts.pop();
if (parts.length % 3 !== 0) {
  console.error("lint-commit-messages: could not parse git output (unexpected record shape)");
  process.exit(2);
}

const commits = [];
for (let index = 0; index < parts.length; index += 3) {
  commits.push({ short: parts[index], subject: parts[index + 1].split("\n", 1)[0], message: `${parts[index + 1]}\n${parts[index + 2]}` });
}

const LEADING_DELIMITER = /^[\s("'`\[]+/;

const findings = [];
for (const commit of commits) {
  for (const { re, what } of GENERIC_PATTERNS) {
    const flags = re.flags.includes("g") ? re.flags : `${re.flags}g`;
    const hit = new RegExp(re.source, flags).exec(commit.message);
    if (hit) findings.push({ sha: commit.short, subject: commit.subject, what, match: hit[0].replace(LEADING_DELIMITER, "") });
  }
  for (const term of terms) {
    const hit = new RegExp(escapeRegExp(term), "i").exec(commit.message);
    if (hit) findings.push({ sha: commit.short, subject: commit.subject, what: "forbidden term", match: hit[0] });
  }
}

for (const message of warned) console.error(`lint-commit-messages: warning: ${message}`);
if (commits.length === 0) {
  if (!ALLOW_EMPTY) {
    console.error(
      `lint-commit-messages: range "${range}" selected 0 commit(s) — pass --allow-empty to accept an empty range`,
    );
    process.exit(2);
  }
  console.error(`lint-commit-messages: warning: range "${range}" selected 0 commit(s) — nothing was scanned (--allow-empty)`);
}

if (AS_JSON) {
  console.log(JSON.stringify(findings, null, 2));
} else {
  for (const finding of findings) {
    console.log(`${finding.sha} ${finding.subject}: ${finding.what} "${finding.match}"`);
  }
  const source = termsFile ? `${terms.length} term(s) from ${displayPath(termsFile)}` : "no terms file";
  console.log(
    `lint-commit-messages: ${findings.length} finding(s) in ${commits.length} commit(s) of "${range}" (${source})`,
  );
}

process.exit(findings.length > 0 ? 1 : 0);
