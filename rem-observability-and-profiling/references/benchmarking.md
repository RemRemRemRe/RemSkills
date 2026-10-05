# Benchmarking a Change

Companion to `rem-observability-and-profiling` §5. A benchmark is evidence only if it
could have failed: compare like with like, prove the measured code ran, report the noise.

## Fair A/B

- Measure each path **separately** (e.g. rebuild vs per-frame), never one number for both.
- Make the thing under test the **only** variable: neither side handicapped (same
  inlining, same checks) — a "faster" result from removing work on one side proves nothing.
- Design the data as a matrix (dimension A × dimension B) plus a **floor vs realistic**
  content axis; label a floor dataset as a floor and always pair it with production-shaped data.
- Attach a **structural assertion** to each dataset so it is semantically effective, not
  vacuous — the data actually exercises the path under test.

## Execution and reporting

- Run in independent processes; discard warmup, then take `min` (noise-resistant) and
  `mean` (representative) across multiple trials.
- Same-code run-to-run variance can be **10–30%**, so a cross-config comparison holds only
  within one round; re-run both sides together before concluding.
- Archive raw runs untracked (`rem-temp-files`); the report carries the summary, not the logs.

## Prove the measured path executed (mutation probe)

A near-zero number may mean the measured code never ran — absence of cost is not proof.

- Mutate the measured **in-memory input** and watch the output change; a bench that does
  not react is measuring nothing.
- Assert the measured value equals a **direct recomputation** of the same quantity, so
  "first iteration works, later ones idle" cannot pass.
