# Design Decisions — Multi-Engine Plugin Adaptation

> Dated record of the decisions behind this skill's design (discussion of
> 2026-07-28/29). The rules themselves live in `../SKILL.md`; this file keeps
> only what the skill text does not state — *when* each was decided and *why*.

---

## Design evolution

| Date | Decision |
|------|----------|
| 2026-07-28 | Initial: parameterize the build script for multi-version support |
| 2026-07-28 | Expand: Python rewrite, configuration-driven, auto-fixer |
| 2026-07-29 | Pivot: replace the rule-based auto-fixer with a **skill-guided AI workflow** |

### Why skill-guided instead of a rule engine (2026-07-29)

The earlier plan carried a rule-based auto-fixer (`fix_rules.json` +
`auto_fixer.py`) that matched error patterns and applied fixes automatically.
It was dropped because:

1. Cross-version UE errors are too varied for a rule engine — a fix needs the
   intent of the code and knowledge of what the older engine offers instead.
2. Every new error type would need a new rule written and tested.
3. An AI agent can read the error log, read the surrounding code, search the
   engine sources for the older equivalent, and apply a nuanced fix.

The split that survived: **fixed infrastructure stays as tools** (build
script, engine config); **judgement goes to the AI**, guided by documented
patterns and conventions.

---

## Dated decisions

| # | Question | Decision | Date |
|---|----------|----------|------|
| 1 | Cherry-pick range identification | Commit-message convention (`Changed: set engine version X.Y` as boundary markers) — no config file of ranges | 2026-07-29 |
| 2 | Cherry-pick conflict handling | AI tries the correct resolution first; conflicts caused by stale embedded dependency code → skip that commit and let the build-fix loop handle it; manual merge as last resort | 2026-07-29 |
| 3 | Cross-version fix isolation | Accept cross-version commits: when a fix for version N breaks N-1, adjust the N-level fix and re-adapt downward | 2026-07-29 |
| 4 | Final verification strategy | Incremental trust — a version's build result is trusted from when it passed; no mandatory full rebuild in Step 4 | 2026-07-29 |
| 5 | Minimum-version compatibility break | Backport the self-contained API into the plugin when it is small; otherwise `#if 0` the feature and document the limitation | 2026-07-29 |
| 6 | Embedded dependency adaptation | Dependencies are adapted inside this workflow (the build-fix cycle covers their code); if they later carry their own multi-version `#if` guards, the workflow would only copy them | 2026-07-29 |
