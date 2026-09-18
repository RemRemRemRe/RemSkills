// Skill collection lint — zero dependencies, runs locally and in CI.
//
//   node tools/lint-skills.mjs            # lint every skill folder
//   node tools/lint-skills.mjs --json     # machine-readable output
//
// Enforces the conventions owned by rem-write-better-skill and
// rem-public-skill-generalization: frontmatter shape, name/folder match,
// description trigger, closing checklist, size budget, leak patterns, and the
// Rem-family name allowlist.
//
// Leak and name checks cover **every non-binary file that ships**: a skill's
// own files (SKILL.md, references/, tools/) and the repository-level files
// (README, LICENSE, .github/, .githooks/, tools/). Nothing is exempt — a file
// that ships, ships to everyone — except the allowlist itself, which is the
// reference data for the name check (rem-public-skill-generalization §3.2a).
// A `local/` directory is never shipped content: it is the per-skill overlay of
// machine-local values, git-ignored and linked in from a private repository, so
// every walker skips it and three guards keep it that way (checkLocalOverlay).
import { readFileSync, readdirSync, statSync, lstatSync, existsSync } from "fs";
import { join, basename, dirname, relative } from "path";
import { fileURLToPath } from "url";
import { execFileSync } from "child_process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const AS_JSON = process.argv.includes("--json");

/** SKILL.md size budget in characters. */
const SIZE_WARN = 32_000;
const SIZE_ERROR = 48_000;
/** Descriptions are in context on every request — budget the aggregate, warn on outliers. */
const DESC_WARN = 800;
const DESC_BUDGET = 10_500;
/** An always-loaded skill must be tiny — it costs every session. */
const ALWAYS_SIZE_ERROR = 2_000;

/** Skill text as the repository stores it: line endings normalized to LF, so a
 * checkout with `core.autocrlf=true` measures the same characters as the blob
 * instead of one extra `\r` per line, which inflates every size budget. */
function readText(file) {
  return readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}

/** The raw frontmatter text when it looks like skill frontmatter (name + description). */
function skillFrontmatterBlock(source) {
  const match = /^(?:\uFEFF)?---[ \t]*\r?\n([\s\S]*?)\r?\n---/.exec(source);
  if (!match) return null;
  if (!/^name:\s*\S+/m.test(match[1]) || !/^description:\s*\S/m.test(match[1])) return null;
  return match[1];
}
/** Allowed frontmatter values. */
const CATEGORIES = new Set(["meta", "workflow"]);
const TRIGGERS = new Set(["manual", "always"]);
/** Patterns that must never appear in a public skill (see rem-public-skill-generalization). */
const LEAK_PATTERNS = [
  { re: /(?:^|[\s("'`\[])[A-Za-z]:[\\/]/m, what: "drive-letter path" },
  { re: /(?:^|[\s("'`\[])\/home\//m, what: "posix home path" },
  { re: /(?:^|[\s("'`\[])\/Users\//m, what: "macOS home path" },
  { re: /\bMyCompanyPlugin\b/, what: "example project name" },
];
/** Rem-family names a public skill may state verbatim, with their public source. */
const NAMES_FILE = join(ROOT, "tools", "public-names.json");

/** Load and validate the allowlist, so a broken file reports one clear reason. */
function loadNames() {
  if (!existsSync(NAMES_FILE)) {
    return { problem: "tools/public-names.json is missing — the Rem-family name check cannot run" };
  }
  let data;
  try {
    data = JSON.parse(readFileSync(NAMES_FILE, "utf8"));
  } catch (error) {
    return { problem: `tools/public-names.json is not valid JSON: ${error.message}` };
  }
  const withoutSource = [];
  for (const bucket of ["publicNames", "documentedExamples"]) {
    for (const [name, source] of Object.entries(data[bucket] ?? {})) {
      if (typeof source !== "string" || source.trim() === "") withoutSource.push(`${bucket}.${name}`);
    }
  }
  if (withoutSource.length > 0) {
    return { problem: `tools/public-names.json entries without a source: ${withoutSource.join(", ")}` };
  }
  return { data };
}

const NAMES = loadNames();
const KNOWN_NAMES = new Set([
  ...Object.keys(NAMES.data?.publicNames ?? {}),
  ...Object.keys(NAMES.data?.documentedExamples ?? {}),
]);
/**
 * A Rem-family identifier — `RemXxx`, and the type-prefixed `URemXxx` / `ERemXxx`
 * forms that carry the word. Case-sensitive, so "remote"/"Removed" stay out.
 */
const REM_NAME_RE = /\b[EUFAIST]?Rem[A-Z][A-Za-z0-9_]*\b/g;
/** Findings reported per file before the list is truncated. */
const MAX_FINDINGS_PER_FILE = 8;
/** The per-skill overlay directory name: machine-local values, never shipped content. */
const LOCAL_DIR = "local";
const TRIGGER_RE = /\buse (when|whenever|this|it)\b|\bwhen(?:ever)? (?:you|a |the |writing|reviewing|creating|updating|committing|syncing|adapting|auditing|adding|changing|deciding)\b/i;
const DATE_RE = /last verified|since ue \d|verified \d{4}-\d{2}/i;
const ENGINE_API_RE = /Engine\/Source|#include\s+"[A-Za-z]+\//;

function fail(list, message) {
  list.push({ level: "error", message });
}

/** Every non-binary file of a skill folder — SKILL.md, references/, tools/. */
function scannedFiles(dir) {
  const files = [];
  const stack = [dir];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      // `local/` is the per-skill overlay: git-ignored, linked from a private
      // repository, and empty of shipped content — never lint or measure it.
      if (entry.name === ".git" || (entry.isDirectory() && entry.name === LOCAL_DIR)) continue;
      const full = join(current, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else if (!isBinary(full)) files.push(full);
    }
  }
  return files.sort();
}

/** A NUL byte in the first block is the classic binary tell — scanning decoded
 * binary yields nonsense findings, and no rule is aimed at it. */
function isBinary(file) {
  return readFileSync(file).subarray(0, 8192).includes(0);
}

function lineOf(source, index) {
  return source.slice(0, index).split("\n").length;
}

/** `URemXxx` and `RemXxx` name the same thing — the allowlist holds the bare form. */
function bareName(name) {
  return /^[EUFAIST]Rem/.test(name) ? name.slice(1) : name;
}

/** Rem-family identifiers of `source` that no public source backs: [name, index]. */
function unverifiedRemNames(source) {
  const hits = [];
  for (const match of source.matchAll(REM_NAME_RE)) {
    if (!KNOWN_NAMES.has(match[0]) && !KNOWN_NAMES.has(bareName(match[0]))) {
      hits.push([match[0], match.index]);
    }
  }
  return hits;
}
function warn(list, message) {
  list.push({ level: "warn", message });
}

/** Parse the small YAML subset the collection uses: scalars, `>`/`|` blocks, one nested level. */
function parseFrontmatter(source) {
  const match = /^(?:\uFEFF)?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/.exec(source);
  if (!match) return { error: "missing or malformed frontmatter block" };
  const lines = match[1].split(/\r?\n/);
  const data = {};
  let currentKey = null;
  let blockMode = null;
  for (const line of lines) {
    if (blockMode) {
      if (/^\s+\S/.test(line)) {
        data[currentKey] = `${data[currentKey]}${blockMode === ">" ? " " : "\n"}${line.trim()}`;
        continue;
      }
      blockMode = null;
      currentKey = null;
    }
    if (!line.trim() || /^\s*#/.test(line)) continue;
    if (/^\s*-\s/.test(line)) return { error: `unsupported list syntax in frontmatter: ${line.trim()}` };
    const kv = /^(\s*)([A-Za-z_][\w-]*):[ \t]*(.*)$/.exec(line);
    if (!kv) return { error: `unsupported frontmatter line: ${line.trim()}` };
    const [, indent, key, rest] = kv;
    const isNested = indent.length > 0;
    if (rest === ">" || rest === "|") {
      blockMode = rest;
      currentKey = isNested ? `${data.__parent}.${key}` : key;
      data[currentKey] = "";
      continue;
    }
    if (!isNested && rest === "") {
      data[key] = {};
      data.__parent = key;
      continue;
    }
    const value = rest.replace(/^["']|["']$/g, "").trim();
    if (isNested) {
      const parent = data[data.__parent];
      if (!parent || typeof parent !== "object") return { error: `nested key without a parent object: ${key}` };
      parent[key] = value;
    } else {
      data[key] = value;
      data.__parent = null;
    }
  }
  delete data.__parent;
  return { data };
}

function lintSkill(name, dir) {
  const issues = [];
  const file = join(dir, "SKILL.md");
  if (!existsSync(file)) {
    fail(issues, "SKILL.md is missing");
    return { name, size: 0, descChars: 0, issues };
  }
  const source = readText(file);
  const size = source.length;

  const parsed = parseFrontmatter(source);
  if (parsed.error) {
    fail(issues, parsed.error);
  } else {
    const { data } = parsed;
    if (!data.name) fail(issues, "frontmatter: missing `name`");
    else if (data.name !== name) fail(issues, `frontmatter: name "${data.name}" != folder "${name}"`);
    if (!data.description) fail(issues, "frontmatter: missing `description`");
    else {
      if (!TRIGGER_RE.test(data.description)) {
        warn(issues, "description states what but not when to use it (no \"use when ...\" trigger)");
      }
      if (data.description.length > DESC_WARN) {
        warn(
          issues,
          `description is ${data.description.length} chars (> ${DESC_WARN}) — it is in context on every request; keep distinct triggers and move detail into the body`
        );
      }
    }
    const meta = data.metadata;
    if (!meta || typeof meta !== "object") fail(issues, "frontmatter: missing `metadata` block");
    else {
      if (!CATEGORIES.has(meta.category)) {
        fail(issues, `metadata.category "${meta.category ?? ""}" not in {${[...CATEGORIES].join(", ")}}`);
      }
      if (!TRIGGERS.has(meta.trigger)) {
        fail(issues, `metadata.trigger "${meta.trigger ?? ""}" not in {${[...TRIGGERS].join(", ")}}`);
      }
    }
  }

  if (!/^#\s+\S/m.test(source)) fail(issues, "no H1 heading");
  const always = parsed.data?.metadata?.trigger === "always";
  if (!/^##\s+.*checklist/im.test(source) && !always) {
    fail(issues, "no closing `## ... Checklist` section");
  }

  // The checklist is the contract and must stay in SKILL.md — exclude it from the
  // size budget so a complete checklist is never a reason to split the file.
  // Locate the LAST `## ... Checklist` heading that is not inside a fenced block:
  // a section whose title merely mentions "checklist", or a fenced example of one,
  // must not shadow the closing checklist — either makes the budget under-count
  // the body it exists to measure.
  const checklist = (() => {
    let fenced = false, start = -1, offset = 0;
    for (const line of source.split("\n")) {
      if (/^\s*(```|~~~)/.test(line)) fenced = !fenced;
      else if (!fenced && /^##\s+.*checklist/i.test(line)) start = offset;
      offset += line.length + 1;
    }
    return start < 0 ? null : source.slice(start);
  })();
  const budgetSize = size - (checklist ? checklist.length : 0);
  if (budgetSize > SIZE_ERROR) fail(issues, `SKILL.md body is ${budgetSize} chars (> ${SIZE_ERROR}, checklist excluded) — split detail into references/`);
  else if (budgetSize > SIZE_WARN) warn(issues, `SKILL.md body is ${budgetSize} chars (> ${SIZE_WARN}, checklist excluded) — consider moving examples to references/`);
  if (always && size > ALWAYS_SIZE_ERROR) {
    fail(issues, `always-loaded skill is ${size} chars (> ${ALWAYS_SIZE_ERROR}) — it costs every session`);
  }

  reportContentFindings(issues, scannedFiles(dir), dir);
  if (ENGINE_API_RE.test(source) && !DATE_RE.test(source)) {
    warn(issues, "documents engine API without a dated marker (\"Last verified: YYYY-MM\")");
  }

  const refDir = join(dir, "references");
  const refFiles = existsSync(refDir)
    ? readdirSync(refDir, { recursive: true }).filter((entry) => statSync(join(refDir, entry)).isFile())
    : [];
  const refChars = refFiles.reduce((sum, entry) => sum + readText(join(refDir, entry)).length, 0);

  return { name, size, descChars: parsed.data?.description?.length ?? 0, refFiles: refFiles.length, refChars, issues };
}

/** Leak and unverified-name findings for a set of files, reported against `base`. */
function reportContentFindings(issues, files, base) {
  for (const file of files) {
    const where = relative(base, file).replace(/\\/g, "/");
    const body = readText(file);
    const findings = [];
    for (const { re, what } of LEAK_PATTERNS) {
      const flags = re.flags.includes("g") ? re.flags : `${re.flags}g`;
      for (const hit of body.matchAll(new RegExp(re.source, flags))) {
        findings.push(`${where}:${lineOf(body, hit.index)}: leak pattern (${what}): "${hit[0].trim()}"`);
      }
    }
    const seen = new Map();
    // Without a usable allowlist every name would fail — report the root cause alone.
    for (const [name, index] of NAMES.problem ? [] : unverifiedRemNames(body)) {
      if (!seen.has(name)) seen.set(name, index);
    }
    for (const [name, index] of seen) {
      findings.push(
        `${where}:${lineOf(body, index)}: unverified Rem-family name "${name}" — give it a public source in tools/public-names.json or generalize it (rem-public-skill-generalization §3.2)`,
      );
    }
    // A `.md` other than SKILL.md that carries skill frontmatter is loaded as a skill
    // by the harness: it pays an always-on description and defeats the reference-file
    // pattern (rem-public-skill-generalization §4).
    if (!/SKILL\.md$/.test(file) && skillFrontmatterBlock(body)) {
      findings.push(
        `${where}:1: skill frontmatter in a non-SKILL.md file — the harness loads it as a skill, so its description stays in context on every request`
      );
    }
    // A `references/…` path that resolves neither here nor at the repository root is an
    // ambiguous cross-skill pointer: a reader resolves it against its own skill first, so
    // name the owning skill instead. Two explicit exemptions — a path with a placeholder or
    // glob (`references/<this-skill>.md`, `tools/**`) is documentation, and a `local/…` path
    // is the per-skill overlay: a clone without the private repository legitimately lacks
    // the link, so a local pointer must never be reported as a broken reference.
    for (const hit of body.matchAll(/(?:^|[\s`(])((?:references|tools|local)\/[\w.<>*-]+)/gm)) {
      const ref = hit[1];
      if (/[<>*]/.test(ref)) continue;
      if (hasLocalSegment(ref)) continue;
      if (existsSync(join(base, ref)) || existsSync(join(ROOT, ref))) continue;
      findings.push(
        `${where}:${lineOf(body, hit.index)}: "${ref}" does not resolve here — qualify it with the owning skill (\`<skill>/${ref}\`)`
      );
    }
    // A qualified `<skill>/references/…` path is repository-relative, so a typo in the skill
    // name hides until someone needs the file.
    for (const hit of body.matchAll(/(?:^|[\s`(])([a-z0-9-]+\/(?:references|tools)\/[\w.\/-]+)/gm)) {
      const ref = hit[1];
      if (hasLocalSegment(ref)) continue;
      if (existsSync(join(ROOT, ref))) continue;
      findings.push(`${where}:${lineOf(body, hit.index)}: "${ref}" does not exist from the repository root`);
    }
    for (const finding of findings.slice(0, MAX_FINDINGS_PER_FILE)) fail(issues, finding);
    if (findings.length > MAX_FINDINGS_PER_FILE) {
      fail(issues, `${where}: ${findings.length - MAX_FINDINGS_PER_FILE} more finding(s) suppressed`);
    }
  }
}

/** Does a repository-relative path contain a `local/` segment? */
function hasLocalSegment(path) {
  return path.split(/[\\/]/).includes(LOCAL_DIR);
}

/** Every file below a `local/` directory; real subdirectories are followed, symlinked ones are not. */
function localOverlayFiles(dir) {
  const files = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory() && !entry.isSymbolicLink()) files.push(...localOverlayFiles(full));
    else files.push(full);
  }
  return files;
}

/** One file under `local/` must be a symlink whose target resolves — never a regular file. */
function checkLocalOverlayFile(issues, file) {
  const where = relative(ROOT, file).replace(/\\/g, "/");
  if (basename(file) === "SKILL.md") {
    fail(issues, `"${where}" is a stray SKILL.md — the harness would load it as a skill; only a top-level <skill>/SKILL.md ships`);
  }
  if (!lstatSync(file).isSymbolicLink()) {
    fail(issues, `"${where}" is a regular file — every file under local/ is a symlink into the private repository, never content of this repo`);
  } else if (!existsSync(file)) {
    fail(issues, `"${where}" is a broken symlink — its target does not resolve; recreate the link into the private repository`);
  }
}

/**
 * The per-skill `local/` overlay guards. The overlay holds machine-local values, ships
 * nowhere, and is linked in from a private repository, so three failures must be loud:
 * a `local/` path that git tracks, a file there that is not a resolving symlink, and a
 * `SKILL.md` outside a top-level skill folder (the harness would discover it as a skill).
 */
function checkLocalOverlay(issues) {
  let tracked;
  try {
    tracked = execFileSync("git", ["ls-files", "-z"], { cwd: ROOT, encoding: "utf8" });
  } catch (error) {
    fail(issues, `git ls-files failed (${error.message.trim()}) — the tracked-${LOCAL_DIR} guard cannot run`);
  }
  for (const path of (tracked ?? "").split("\0").filter(Boolean)) {
    if (hasLocalSegment(path)) {
      fail(issues, `"${path}" is tracked by git — files under a local/ directory are machine-local values, never committed here`);
    }
  }

  const stack = [ROOT];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      if (entry.name === ".git" || entry.name === "node_modules") continue;
      const full = join(current, entry.name);
      if (entry.isDirectory() && entry.name === LOCAL_DIR) {
        for (const file of localOverlayFiles(full)) checkLocalOverlayFile(issues, file);
        continue;
      }
      if (entry.isDirectory()) {
        stack.push(full);
        continue;
      }
      const where = relative(ROOT, full).replace(/\\/g, "/");
      if (entry.name === "SKILL.md" && !/^[^/]+\/SKILL\.md$/.test(where)) {
        fail(issues, `"${where}" is a stray SKILL.md — the harness would load it as a skill; only a top-level <skill>/SKILL.md ships`);
      }
    }
  }
}

/** The allowlist is the reference data for the name check, not a scanned file. */
const SCAN_EXEMPT = new Set(["tools/public-names.json"]);

/** Repository-level files, which ship too: README, LICENSE, workflows, hooks,
 * tools. Skill folders are skipped — each is linted once as a skill. */
function repoFiles() {
  const files = [];
  const stack = [ROOT];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      if (entry.name === ".git" || entry.name === "node_modules") continue;
      if (entry.isDirectory() && entry.name === LOCAL_DIR) continue;
      const full = join(current, entry.name);
      const rel = relative(ROOT, full).replace(/\\/g, "/");
      if (entry.isDirectory()) {
        if (!existsSync(join(full, "SKILL.md"))) stack.push(full);
      } else if (!isBinary(full) && !SCAN_EXEMPT.has(rel)) {
        files.push(full);
      }
    }
  }
  return files.sort();
}

/** `--discovery [root...]`: audit how many skills a set of roots put in context.
 * Roots default to this repository. Any `.md` other than SKILL.md carrying skill
 * frontmatter is an error: the harness would load it as a skill. */
function runDiscovery(roots) {
  let totalSkills = 0;
  let totalChars = 0;
  let problems = 0;
  for (const root of roots) {
    const found = [];
    const bad = [];
    const stack = [root];
    while (stack.length > 0) {
      const dir = stack.pop();
      let entries;
      try {
        entries = readdirSync(dir, { withFileTypes: true });
      } catch {
        console.log(`ERROR ${root}: cannot read directory`);
        problems += 1;
        break;
      }
      for (const entry of entries) {
        if (entry.name === ".git" || entry.name === "node_modules") continue;
        const full = join(dir, entry.name);
        if (entry.isDirectory()) stack.push(full);
        else if (entry.name.endsWith(".md") && !isBinary(full)) {
          const source = readText(full);
          if (!skillFrontmatterBlock(source)) continue;
          const parsed = parseFrontmatter(source);
          const chars = parsed.error ? 0 : (parsed.data.description ?? "").length;
          const rel = relative(root, full).replace(/\\/g, "/");
          if (entry.name === "SKILL.md") found.push({ rel, chars });
          else bad.push(rel);
        }
      }
    }
    found.sort((a, b) => a.rel.localeCompare(b.rel));
    const chars = found.reduce((sum, entry) => sum + entry.chars, 0);
    totalSkills += found.length;
    totalChars += chars;
    console.log(
      `\n${root} — ${found.length} skill(s), ${chars} chars of description (~${Math.round(chars / 4)} tokens in context on every request)`
    );
    for (const entry of found) console.log(`  ${String(entry.chars).padStart(4)}  ${entry.rel}`);
    for (const rel of bad) {
      problems += 1;
      console.log(`  ERROR ${rel}: skill frontmatter outside SKILL.md — the harness loads it as a skill`);
    }
  }
  console.log(`\nTOTAL: ${totalSkills} skill(s), ${totalChars} chars of description, in context on every request`);
  if (problems > 0) process.exitCode = 1;
}

const discoveryAt = process.argv.indexOf("--discovery");
if (discoveryAt >= 0) {
  const roots = process.argv.slice(discoveryAt + 1).filter((arg) => !arg.startsWith("--"));
  runDiscovery(roots.length > 0 ? roots : [ROOT]);
} else {

// Normal run: lint every skill in this repository.
const skills = readdirSync(ROOT, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && !entry.name.startsWith("."))
  .filter((entry) => existsSync(join(ROOT, entry.name, "SKILL.md")))
  .map((entry) => entry.name)
  .sort();

const results = skills.map((name) => lintSkill(name, join(ROOT, name)));

// Repository-level files ship too — a drive path in the CI workflow or in a hook
// leaks exactly like one in a skill.
const repoFileList = repoFiles();
const repoIssues = [];
reportContentFindings(repoIssues, repoFileList, ROOT);
checkLocalOverlay(repoIssues);
const repoChars = repoFileList.reduce((sum, file) => sum + readText(file).length, 0);
results.push({ name: "(repository)", size: repoChars, refFiles: 0, refChars: 0, issues: repoIssues });

if (AS_JSON) {
  console.log(JSON.stringify(results, null, 2));
} else {
  let errors = 0;
  let warnings = 0;
  if (NAMES.problem) {
    errors += 1;
    console.log(`ERROR tools/public-names.json\n        error: ${NAMES.problem}`);
  }
  for (const result of results) {
    const bad = result.issues.filter((issue) => issue.level === "error");
    const soft = result.issues.filter((issue) => issue.level === "warn");
    errors += bad.length;
    warnings += soft.length;
    const refs = result.refFiles ? `, refs ${result.refFiles} (${result.refChars} chars)` : "";
    const status = bad.length ? "ERROR" : soft.length ? "WARN " : "ok   ";
    console.log(`${status} ${result.name} — ${result.size} chars${refs}`);
    for (const issue of [...bad, ...soft]) console.log(`        ${issue.level}: ${issue.message}`);
  }
  const descChars = results.reduce((sum, result) => sum + (result.descChars ?? 0), 0);
  if (descChars > DESC_BUDGET) {
    warnings += 1;
    console.log(
      `WARN  (always-on) — descriptions total ${descChars} chars (> ${DESC_BUDGET}), in context on every request; see rem-write-better-skill §11`
    );
  }
  console.log(`\n${skills.length} skills, ${errors} error(s), ${warnings} warning(s)`);
  console.log(
    `always-on: ${descChars} chars of description (~${Math.round(descChars / 4)} tokens), budget ${DESC_BUDGET}`
  );
  if (errors > 0) process.exitCode = 1;
}
}
