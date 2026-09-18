---
name: rem-observability-and-profiling
description: >
  Runtime visibility requirements for project code: when and how to log (level
  and category choice, spam control), debug drawing that is toggle-gated and
  shipping-safe, debugger/tooling integration (gameplay debugger categories,
  console commands and cvars, visual logger, trace channels), and profiling
  tags (CPU profiler scopes, cycle stats, stat groups and their classification,
  CSV stats) — with the review checklist for auditing a change's
  instrumentation. Use when writing or reviewing gameplay/system code that must
  be observable at runtime.
metadata:
  category: meta
  trigger: manual
---

# Observability & Profiling

Owns one review dimension: **can this code tell you what it is doing at
runtime, without a debugger, in the build you ship?**

The rules are UE-generic. Project-specific values — real log category names,
stat group names, cvar names, trace channel names — live in the skill's `local/`
overlay (when present) or the project's own conventions doc, never here.

| Concern | Owner |
|---|---|
| Log/assert macro signatures and their config macros | `rem-cpp-best-practices/references/macros-logging.md` §14 |
| Which string/format type a log message uses | `rem-cpp-best-practices/references/type-mapping.md` §12 |
| When a change's tests are complete | `rem-test-completeness` |
| **When/what to log, debug draw, tooling hooks, profiling tags** | this skill |

---

## 1. When instrumentation is required

Instrumentation is part of the change, not a follow-up. Decide per work unit:

| Change kind | Log | Debug draw | Tooling hook | Profiler tag |
|---|---|---|---|---|
| New per-frame system (tick, component update, subsystem) | transitions + failures | optional | category if it is a new subsystem | **required** |
| New gameplay action / state machine | state transitions | optional | console command if it is inspectable | when it can exceed the frame budget |
| New async / threaded work | start + failure + completion | no | no | **required** |
| Pure data struct, utility, algorithm | no | no | no | only if it is a known hot path |
| Refactor / rename / move | preserve existing | preserve existing | preserve existing | preserve existing |

A review finding here is a **missing** item from the table, not a preference.
A refactor that silently drops instrumentation is a regression: check that
every removed log/draw/stat call either still exists or was intentionally
replaced.

## 2. Logging

### Level selection

| Verbosity | Use for | Never use for |
|---|---|---|
| `Fatal` | Unrecoverable startup failure — it crashes | anything a caller could handle |
| `Error` | An operation failed and the caller/player is affected | expected/recoverable states |
| `Warning` | Recoverable anomaly, configuration fallback, degraded path | per-frame conditions |
| `Display` | Player-visible milestones, session lifecycle | developer detail |
| `Log` | Normal state transitions, external input, decisions taken | per-tick values |
| `Verbose` / `VeryVerbose` | Diagnostic detail behind a cvar | anything unconditional |

Rule of thumb: if the message is useful **only while investigating**, it is
`Verbose` and must be gated (§2.2).

### Category rules

- One category per system; declare it where the system lives
  (`DECLARE_LOG_CATEGORY_EXTERN` in a header, `DEFINE_LOG_CATEGORY` in one
  `.cpp`) — signatures in `rem-cpp-best-practices/references/macros-logging.md`.
- Never log to the generic temporary category in code that ships: a category is
  how a reader filters the log to the system they are debugging.
- The default compile-time verbosity decides what survives in shipping —
  choose it deliberately, not `All` by habit.

### Spam control

- Nothing on a per-frame path may log unconditionally. Gate it with a cvar
  (`_CVAR` macro variant) or a condition (`_COND` variant).
- One-shot messages use a stable key or a `static bool` latch so a repeated
  state does not print once per call.
- Never log inside a tight loop — aggregate and log the summary once.

### What must be logged

| Event | Required content |
|---|---|
| State transition | previous state, next state, trigger |
| External input (network, player, config) | source, sanitized value, decision taken |
| Failure / fallback | what failed, the inputs, and what the code did instead |
| Recovery | the anomaly, how it recovered, whether state is intact |

Never log secrets, credentials, or full payload dumps. Log identifiers, counts
and the decision — not the data.

## 3. Debug drawing

Debug drawing is a **developer tool**, so it must be invisible and free in a
shipping build:

- **Gate every call.** Wrap in `#if ENABLE_DRAW_DEBUG` (0 in Shipping/Test
  builds — confirm the macro in your engine version) or behind a cvar /
  gameplay-debugger category. An ungated `DrawDebug*` call is a review
  rejection: it ships the cost and the visuals.
- **Choose the API by lifetime:**

| Need | API |
|---|---|
| Transient shape for one frame / a few seconds | `DrawDebugLine` / `Sphere` / `Box` / `Circle` / `Arrow` / `String` (`DrawDebugHelpers.h`) |
| Persistent overlay that survives frames | A custom debug draw component / `ULineBatchComponent`, cleared explicitly |
| On-screen text without world geometry | `GEngine->AddOnScreenDebugMessage(Key, TimeToDisplay, Color, Text)` — always pass a stable `Key` so the same line updates instead of stacking |
| Per-actor runtime state inspector | A gameplay debugger category (§4) |

- **Set the lifetime explicitly.** Default `LifeTime` of `-1` with
  `bPersistentLines = true` leaks geometry until the world resets; pass a finite
  lifetime or clear the batch.
- **Label with meaning.** A sphere with no text tells a reader nothing; draw the
  value that decided it.
- **Never draw from a shipping path.** Drawing allocates and submits render
  commands — it is not a cheap early-out.

## 4. Tooling integration

A subsystem that cannot be inspected at runtime costs a rebuild for every
question. Ask once per new subsystem:

| Question | Hook |
|---|---|
| "What state does this actor/subsystem think it is in?" | Gameplay debugger category (`FGameplayDebuggerCategory`, `CollectData` / `DrawData`) |
| "Can I change this at runtime while playing?" | Console variable (`TAutoConsoleVariable<T>` / `FAutoConsoleVariableRef`) |
| "Can I trigger this path without playing the game to it?" | Console command (`FAutoConsoleCommand*` with world/args) |
| "What happened in the frames before the bug?" | Visual logger (`UE_VLOG`) |
| "What does this subsystem do over a whole session?" | Unreal Insights trace channel (`UE_TRACE_CHANNEL_DEFINE`) |

Rules:

- A new subsystem with per-frame behavior should ship at least a cvar (to turn
  it off) and, if it owns actors, a debugger category.
- Console variables and commands need a help string — the documentation rule
  is owned by `rem-docs-and-config` §4.
- Registering a debugger category or cvar must not create a hard dependency from
  a runtime module onto an editor-only module; keep the hook in the module that
  already owns the dependency.

## 5. Profiling tags

### Scope macros

| Macro | Emits | Use when |
|---|---|---|
| `TRACE_CPUPROFILER_EVENT_SCOPE(Name)` | Insights CPU timing, static name | default choice for a new hot path |
| `TRACE_CPUPROFILER_EVENT_SCOPE_STR(Name)` | Insights CPU timing, dynamic name | the name is data-driven — costs more, never in a tight loop |
| `TRACE_CPUPROFILER_EVENT_SCOPE_ON_CHANNEL(Name, Channel)` | Insights, custom channel | the work belongs to a subsystem trace channel |
| `SCOPE_CYCLE_COUNTER(Stat)` | `stat` command counter | the value must be visible in the in-game `stat` overlay |
| `CSV_SCOPED_TIMING_STAT(Category, Stat)` | CSV profiling capture | the timing feeds a CSV capture |
| `CSV_CUSTOM_STAT(Category, Stat, Value)` | CSV numeric series | a scalar (count, size, ratio), not a duration |
| `LLM_SCOPE(Tag)` | Low-level memory tracking | the code allocates in a way that should be attributed |

Headers and full signatures: `references/api-tables.md`.

### When a tag is required

- Any per-frame system: tag the tick/update entry point.
- Any loop over a data-dependent count: tag the loop body or the loop itself so
  the cost scales visibly.
- Any async/threaded task: tag the task body.
- Any path with a known budget: tag it so a regression shows up as a name, not
  as an anonymous frame-time bump.

### Stat group classification

- Every cycle stat belongs to a **stat group**; declare groups in one place per
  module (`DECLARE_STATS_GROUP`), not ad hoc per file.
- Naming: one group per system, one stat per subsystem-level operation. A group
  named after a single function is a smell — group by the thing a reader would
  look up, not by the call site.
- Reuse an existing group before adding a new one; a new group is a taxonomy
  decision, and taxonomy is reviewed (see `rem-cpp-best-practices` §11 on
  single ownership — one name per concept).
- `DECLARE_STATS_GROUP` vs `_VERBOSE` vs `_SORTBYNAME`: pick `_VERBOSE` only
  when the stats are noise by default; `_SORTBYNAME` when the group is large.

### Overhead rules

- Scope macros are cheap but not free: do not tag every 3-line helper.
- Never tag inside a loop that runs more than a few thousand times per frame —
  the tag becomes the cost. Tag the loop, not the iteration.
- Dynamic-name tags (`_STR`) allocate; hoist the string out of the loop.

## Checklist

Before declaring an instrumentation change (or reviewing one) done:

- [ ] §1 — every row of the "when instrumentation is required" table was considered for the change kind
- [ ] §1 — a refactor preserved or intentionally replaced every removed log/draw/stat call
- [ ] §2 — every log has a deliberate verbosity; no `Verbose` message is unconditional
- [ ] §2 — logs use a system category, never the generic temporary category
- [ ] §2 — no unconditional logging on a per-frame path; repeated states are latched or cvar-gated
- [ ] §2 — state transitions, external input, failures and recoveries carry their decision context
- [ ] §2 — no secrets, credentials or payload dumps in logs
- [ ] §3 — every debug draw call is gated (`ENABLE_DRAW_DEBUG` or a cvar/debugger category)
- [ ] §3 — debug draw lifetime is explicit and finite; no persistent-line leak
- [ ] §3 — debug draw carries the value it visualizes, not just a shape
- [ ] §4 — a new per-frame subsystem ships a cvar to disable it
- [ ] §4 — a new actor-owning subsystem has a gameplay debugger category or a stated reason why not
- [ ] §4 — every cvar/console command carries the help string required by `rem-docs-and-config` §4
- [ ] §5 — every per-frame entry point, data-dependent loop and async task carries a profiling tag
- [ ] §5 — cycle stats are registered in a declared stat group, not ad hoc
- [ ] §5 — no dynamic-name tag inside a loop; no tag inside a >1k-iteration loop body
