---
name: calibrated-verification-loop
description: >
  Make a human's review the final authority for many independent placements that automation
  cannot get right: rigid-unit/free-gap decomposition, two independent estimators, escalation
  into fixed-landing review clips, calibrated operator units, invariants that veto impossible
  reports, immutable corrections. Use when a pipeline must place dozens of items only a
  human can confirm.
metadata:
  category: workflow
  trigger: manual
---

# Calibrated Verification Loop

For work where the machine cannot be certain and only a human can sign off. The goal is
to make the operator's review **minimal, incremental and quantitative** instead of asking
them to re-check everything.

The loop: **automate what agrees, escalate what disagrees, calibrate the operator's units,
veto impossible reports with invariants, persist corrections immutably.**

## 1. Model first: rigid units, free gaps

The biggest win is the decomposition, not the matcher. Find the axis where content is
*internally* rigid and *between* units is free.

Worked example (verified 2026-09): a song recorded as 32 separate takes. Within a sung
phrase the internal timing is exact (20–80 ms spread); between phrases the performer
paused arbitrarily. The recording therefore splits into units that each need exactly one
offset, and the pauses cost nothing. Aligning the recording as one continuous timeline is
impossible; aligning ~50 independent offsets is routine.

**Measure before modelling.** Establish the units, the relationship between channels, and
the noise floor from measurement; then design. Every constant should trace to a
measurement, not an estimate. Record the measurements in a dated facts table — they are
the thing that makes later debugging possible.

## 2. Two independent estimators, never one anchored on the other

Run two estimators with *different failure modes* (e.g. sequence matching against a
transcript, and spectral correlation against a reference recording).

- **Agree within tolerance** → accept automatically. No operator cost.
- **Disagree** → escalate. The disagreement is the signal, not noise to be averaged.

**Both estimators must be anchored on the same external reference, never on each other.**
This is the subtle form of the rule: if the second estimator searches a window centred on
the first one's answer, they are not independent, "agreement" is manufactured, and both
will be wrong together. The bug is invisible precisely because the agreement check passes.

## 3. Escalation costs one listen

The operator's review must be a single short clip per decision, with the candidate landing
at a **fixed, identical position** every time (e.g. always at 1.500 s after a fixed
lead-in). Never make them scrub, seek, or count.

| Rule | Why |
|---|---|
| One file per item, `<id>` as the filename | stable ids; the filename never carries meaning, so positions can change freely |
| Render the decision, not the context | cost per decision stays constant as the project grows |
| Disagreement → two files, `<id>a` / `<id>b` | the operator answers "a" or "b", nothing else |
| Let the operator ask for candidates the machine never produced | they routinely infer a third position from two complaints |
| Compare against the **authoritative** source, not a derived or degraded one | a derived source may lack the detail the decision hinges on |
| Match loudness of the compared items **by peak**, not by average | a brickwalled master (crest factor ~6 dB) and a natural recording (~11 dB) at equal average level bury the latter |

## 4. Calibrate the operator's units before trusting their numbers

"Half a unit slow" is a measurement. Treat it as one — after proving you know what a unit
is to them.

- **Make them report the same error from two starting points.** If `a` is "half a unit
  slow" and `b` is "one unit fast", and `|a − b|` equals one unit, the reports are
  independent and must converge; their average is a strong estimate.
- **A whole-period answer means the truth is between the candidates.** See pitfall 2.
- **A report is a hypothesis about direction, not a fact.** Confirm it against the
  reference and the invariants before applying it, and say so when you disagree.

## 5. Invariants veto impossible reports

Cross-check every report against constraints that cannot be violated:

| Invariant | Check |
|---|---|
| Relative timing inside a unit is fixed | two units from the same source must differ by exactly the difference of their local start times |
| Order | units were performed in order; a placement that scrambles them is wrong |
| Existence | a phrase cannot be placed where the reference has no such content |
| Clearance | if a unit lands before the point where its content must begin, it is impossible |

When a report violates an invariant, do not silently apply it: state the conflict and the
constraint, and offer the candidates that satisfy both. In practice the ear is right about
*direction* and the invariants are right about *feasibility*.

## 6. Persist corrections immutably, from one source of truth

```
state/fixes.json     { "<id>": <absolute value>, ... }   operator-confirmed, NEVER regenerated
state/choices.json   { "<id>": [<candidate>, ...] }      candidate overrides for re-checks
state/mute.json      [<id>, ...]                          units dropped by an overlap decision
```

- Corrections are **absolute values in the target's own coordinate system**, never deltas.
  Deltas stack, drift, and cannot be audited.
- They outrank every automatic result, always. The rebuild path must print that it did not
  touch them.
- Every consumer reads the same loader (one merge of auto results, corrections, mutes and
  overrides in a defined priority order). The review renderer and the final renderer must
  not have separate notions of where a unit goes.
- Split persistent from regenerable storage explicitly, and **prove the split with a test**:
  wipe the volatile side, rebuild, confirm the persistent side is untouched.

## Pitfalls

Each of these caused a real failure. Symptom → cause → fix.

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | A unit lands seconds from where it belongs; constraints cascade into a monotonic ramp | A constraint, window or comparison was applied to the raw **offset** while another site used the **absolute placed position**; the two differ by the unit's local start | Name the coordinate system at every use site, convert once at the boundary. This single root cause produced four separate bugs |
| 2 | Two values exactly one period apart both look wrong; the operator reports "too early" then "too late" | Periodic content is self-similar, so a candidate one period away scores nearly as high as the truth | Evaluate the ±1 period candidates explicitly; treat `|a − b| ≈ one period` as proof the truth lies between them, not at either |
| 3 | Two estimators "agree" and both are wrong | The second estimator was windowed on the first one's answer | Anchor both on the external reference |
| 4 | A unit is confidently placed far away on only a fraction of its evidence | A one-way canonicalisation table mapped token X onto token Y, so a source that genuinely emitted X could never equal Y | Use equivalence groups (mutual similarity), not one-way canonicalisation |
| 5 | A plausible number derived from far too little evidence | No minimum evidence count; the search window was centred on a bad estimate, putting the truth outside it | Require a minimum match count; widen the search and retry; escalate if still thin |
| 6 | A source plays ~N seconds off against everything else | Its file was indexed on the target timeline without converting between time bases | Convert once at the boundary (`source_idx = target_time − OFFSET`) |
| 7 | A tool runs, outputs plausible data, and ignores every operator correction | It reads a stale intermediate artifact instead of the shared loader | One loader, one source of truth, used by every consumer |
| 8 | The quieter, more dynamic item is inaudible in a comparison | Loudness matched by average level across mismatched crest factors | Match by peak, with a per-item target |
| 9 | An override silently does nothing | `x = x or default` never replaces a truthy `x` | Assign the override explicitly |

## Record what failed

Keep a dated list of approaches that were tried and **failed**, with the reason. A
dozen dead ends (whole-signal correlation, phase-based inference, source separation,
per-unit dynamic programming) are the most reusable output of a long alignment effort:
they stop the next session from re-deriving them. Record the disproof, not just the
conclusion.

## Checklist

Before running or resuming a verification loop:

- [ ] The decomposition is measured, not assumed: units are internally rigid, gaps free (1)
- [ ] Two estimators with different failure modes exist, and neither is windowed on the other (2, 3)
- [ ] Review clips are one decision each, with a fixed landing position (3)
- [ ] The comparison renders the authoritative source, and matches loudness by peak (3)
- [ ] The operator's unit is calibrated by a double report before any number is applied (4)
- [ ] Invariants (relative timing, order, existence, clearance) are checked against every report (5)
- [ ] Corrections are absolute, highest priority, and untouched by rebuilds (6)
- [ ] Every consumer reads one shared loader — no tool reads a stale intermediate (7)
- [ ] The persistent/volatile split is proven by wiping the volatile side and rebuilding (6)
- [ ] Failed approaches are recorded with their disproof
- [ ] Every item is either auto-accepted or explicitly confirmed, and cleared items are never re-shown
