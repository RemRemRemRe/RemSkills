#!/usr/bin/env node
// Un-folded range lint — zero dependencies, node built-ins only.
//
//   node tools/lint-push-range.mjs --repo <path> --range <a>..<b> [--json] [--allow-empty]
//
// A range that rewrites itself is WIP left as permanent history: a commit adds
// something, a later commit in the same range takes it back, and the public
// changelog ends up listing both halves. The rule and its remedy belong to
// rem-commit-workflow (`### Fold before the tag`); this file is the mechanical
// half, run by `.githooks/pre-push` on every outgoing branch.
//
// Two findings, in descending severity:
//   ERROR cancelled  a file touched by two or more commits whose net diff over
//                    the whole range is empty — the range undoes itself; fold it.
//   WARN  churn      a file touched by three or more commits with a real net
//                    diff — an iterative stack; fold it or say why it stays.
//
// The file ships, so it carries no private term and no machine path.
import { relative, resolve, basename } from "node:path";
import { execFileSync } from "node:child_process";

const USAGE = [
  "Usage: node tools/lint-push-range.mjs --repo <path> --range <a>..<b> [--json] [--allow-empty]",
  "",
  "  --repo        repository to read (required)",
  "  --range       range to inspect, e.g. origin/main..HEAD (required)",
  "  --json        print a JSON array of findings instead of text lines",
  "  --allow-empty accept a range that selects 0 commits (otherwise it is an error)",
].join("\n");

const argv = process.argv.slice(2);
const AS_JSON = argv.includes("--json");
const ALLOW_EMPTY = argv.includes("--allow-empty");

function valueOf(flag) {
  const index = argv.indexOf(flag);
  if (index < 0) return null;
  const value = argv[index + 1];
  return value && !value.startsWith("--") ? value : null;
}

const repo = valueOf("--repo");
const range = valueOf("--range");

if (!repo || !range) {
  console.error(`lint-push-range: --repo and --range are required\n\n${USAGE}`);
  process.exit(2);
}

/** A path safe to print — never an absolute drive-letter path. */
function displayPath(file) {
  const repoRel = relative(resolve(repo), resolve(repo, file));
  return repoRel && !repoRel.startsWith("..") ? repoRel : basename(file);
}

function git(args) {
  return execFileSync("git", ["-C", repo, ...args], { encoding: "utf8" });
}

/** commit hash -> the files it touched, merge commits excluded by git's default. */
function commitsToFiles() {
  const output = git(["log", "--format=%x00%H", "--name-only", "--no-renames", range]);
  const map = new Map();
  let current = null;
  for (const raw of output.split("\n")) {
    const line = raw.trim();
    if (line.startsWith("\u0000")) {
      current = line.slice(1);
      map.set(current, new Set());
      continue;
    }
    if (!line || current === null) continue;
    map.get(current).add(line);
  }
  return map;
}

let filesOf;
try {
  filesOf = commitsToFiles();
} catch (error) {
  console.error(`lint-push-range: cannot read ${range}: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(2);
}

if (filesOf.size === 0 && !ALLOW_EMPTY) {
  console.error(`lint-push-range: the range "${range}" selects 0 commits (pass --allow-empty if that is intended)`);
  process.exit(2);
}

/** Files whose net diff across the whole range is empty, i.e. touched and restored. */
const netDiff = new Set(git(["diff", "--name-only", "--no-renames", range]).split("\n").filter(Boolean));

/**
 * The blob a path has at a revision, or null when the path does not exist there.
 * Compared between a later commit and the parent of the earlier touch, this is
 * what proves a commit took back exactly what an earlier one added.
 */
function blobAt(rev, file) {
  try {
    return git(["rev-parse", "--verify", "--quiet", `${rev}:${file}`]).trim();
  } catch {
    return null;
  }
}

const touchCount = new Map();
for (const [commit, files] of filesOf) {
  for (const file of files) {
    if (!touchCount.has(file)) touchCount.set(file, []);
    touchCount.get(file).push(commit);
  }
}

const findings = [];
for (const [file, commitsNewestFirst] of [...touchCount].sort((a, b) => a[0].localeCompare(b[0]))) {
  if (commitsNewestFirst.length < 2) continue;
  const commits = [...commitsNewestFirst].reverse();
  const short = commits.map((hash) => hash.slice(0, 7));
  /** A later commit restored the file to what it was before an earlier touch. */
  const cancelledPair = commits.some((later, index) => {
    if (index === 0) return false;
    const earlier = commits[index - 1];
    let earlierParent;
    try {
      earlierParent = git(["rev-parse", `${earlier}^`]).trim();
    } catch {
      return false;
    }
    return blobAt(later, file) === blobAt(earlierParent, file);
  });
  if (cancelledPair || !netDiff.has(file)) {
    findings.push({
      severity: "error",
      rule: "cancelled",
      file,
      commits: short,
      message:
        `touched by ${commits.length} commits and a later one restored it — the range undoes itself ` +
        `(${short.join(", ")}); fold it before pushing`,
    });
  } else if (commits.length >= 3) {
    findings.push({
      severity: "warn",
      rule: "churn",
      file,
      commits: short,
      message:
        `touched by ${commits.length} commits (${short.join(", ")}) — an iterative stack; ` +
        "fold it, or say in the commit body why it stays",
    });
  }
}

if (AS_JSON) {
  console.log(JSON.stringify(findings, null, 2));
} else if (findings.length === 0) {
  console.log(`lint-push-range: 0 finding(s) in ${filesOf.size} commit(s) of "${range}"`);
} else {
  const errors = findings.filter((f) => f.severity === "error").length;
  const warns = findings.length - errors;
  console.log(
    `lint-push-range: ${findings.length} finding(s) in ${filesOf.size} commit(s) of "${range}" ` +
      `(${errors} error, ${warns} warning)`,
  );
  for (const finding of findings) {
    console.log(`  ${finding.severity === "error" ? "ERROR" : "WARN "} ${finding.rule} ${displayPath(finding.file)} — ${finding.message}`);
  }
}

process.exit(findings.some((f) => f.severity === "error") ? 1 : 0);
