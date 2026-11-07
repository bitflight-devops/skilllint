# Fresh paired primary-corpus evaluation

Measured product endpoints: baseline `85813670fbaf8755cc81698497b992cb0a1d2b60`, candidate `41a53b7a7b00e236f2f2f8fc076dbaa965bf2ac8`. Frozen harness source `fcbda8294e97aadc5d79f025f0891ff9125bccf4`, published with identical script bytes in PR #371. Wheel installs, CPython 3.12.14, identical interpreter hash and 29 dependency name/version entries. Source/wheel/installed product files independently verified.

Each row has 2 warmup pairs excluded from statistics and 10 measured alternating AB/BA pairs. A/A rows use the same baseline executable in both roles. All cases use fresh isolated processes and fixed output settings. Exact exit, raw stdout/stderr, corpus path/content/mode/symlink and Git-state parity are required across all samples, with source unchanged. CLI output capture is included in timing. Reset copies, hashing, staging and post-run evidence-file writes are outside timing.

| Workload | Baseline median ms | Candidate median ms | Median paired ratio | Paired ratio IQR | Candidate wins |
| --- | ---: | ---: | ---: | --- | ---: |
| aa-one-small | 763.14 | 795.93 | 0.95154 | 0.84548–1.10360 | 6/10 |
| aa-scan-default | 3657.55 | 3606.09 | 0.98327 | 0.97579–1.02511 | 7/10 |
| fix-default | 3761.02 | 3664.83 | 0.96291 | 0.95012–0.97691 | 8/10 |
| one-median | 511.90 | 519.55 | 1.02998 | 0.95272–1.06372 | 4/10 |
| one-small | 492.31 | 494.37 | 1.01430 | 0.93583–1.05481 | 5/10 |
| scan-default | 3611.11 | 3332.60 | 0.91544 | 0.89064–0.93392 | 10/10 |
| scan-json | 3598.72 | 3415.40 | 0.94455 | 0.91583–0.97854 | 9/10 |
| synthetic-fix | 1643.71 | 1641.75 | 1.00948 | 0.96191–1.01577 | 4/10 |
| ten-file-concise | 513.18 | 533.11 | 1.04864 | 0.98550–1.09556 | 4/10 |

Quartiles use the inclusive method. Ratios below 1 favor the candidate. Marginal medians and medians of paired ratios/deltas are different statistics. Full paired deltas, CPU, order and half-session splits are retained in grid-summary.json.

The private real corpus checks 447 files. It is an exact pinned retained projection, not a complete repository: 22 PNG paths and one large graph JSON are omitted. All skill documents are retained; omitted assets may affect link findings. Corpus source, identity, paths and findings remain private. Therefore these samples do not independently reproduce the repository from public artifacts.

The real fix row was verified to leave files unchanged. Synthetic modifying fix checks 200 files and records 466 repairs; resulting files match across endpoints. Untimed JSON companions verify 1/1/10 files for the short controls. Ten-file selection uses a prepared synthetic index and explicit CLI paths, not actual hook-framework execution or staged discovery. Original history is absent from the primary corpus Git context.

Observed full-scan reductions are bounded to this session. Short-file and modifying-fix rows do not demonstrate a benefit. Ten-file paired median is 4.9% slower (+27.3 ms), with both order groups above 1; this tradeoff remains visible and a separate focused repeat is planned. Same-executable controls show variability. No significance, equivalence, overall-workflow or universal-speedup claim is made.

OS caches are warm/unmanaged; CPU frequency, affinity and external host contention are uncontrolled. Owned CPU jobs were paused. Dependency equality is names/versions, not a comprehensive dependency-byte proof. This controlled wheel experiment does not reproduce the existing CI install/order/cache conditions. User workflow frequencies are unknown. Historical lost samples are not included or pooled.

All public raw samples are allowlisted exports with keyed opaque output/tree/metadata digests. Private byte streams and source remain local for audit; they are deliberately not published. Generic reproducible harness and methodology are in scripts/bench_paired.py and docs/paired-cli-evaluation.md. Independent audit completed: all 216 observations, 432 retained Git captures, retained source/reference/work trees, output and metadata HMACs, summaries, companions and provenance passed. Intermediate final trees are not retained individually; their recorded digests match independently checked retained trees, and the reviewed harness enforced exact parity during execution.
