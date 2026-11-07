# Independent corpus and focused repeat

These are separate sessions, not pooled with the primary corpus or prior runs. Measured baseline `85813670fbaf8755cc81698497b992cb0a1d2b60`, candidate `41a53b7a7b00e236f2f2f8fc076dbaa965bf2ac8`; frozen harness `fcbda8294e97aadc5d79f025f0891ff9125bccf4`. Same verified wheel environments and interpreter as the primary grid.

The public independent corpus is [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills/tree/8f082544116fc0d014188e521ca40304cdfc86b0), pinned at `8f082544116fc0d014188e521ca40304cdfc86b0`. Complete tracked working tree: 5,344 entries, zero omissions, 411 regular SKILL.md files representing 390 distinct contents, plus 67 SKILL.md symlinks. All 1,663 symlinks are internal and resolving. Community CLI runs return exit 1 for matched existing findings, not execution errors; this is mixed rather than all-clean coverage. The default check evaluates 1,644 paths, including aliases and additional targets: this is not a count of unique skills. Git context is a clean, detached, shallow one-commit checkout; repository scripts/plugins were not executed. Root MIT with component notices, including Apache-2.0; source and findings are not republished.

Two retained warmup pairs are excluded from statistics in every row. Ten-file repeat has 30 measured alternating pairs; community rows have 10 each. Fresh isolated CLI processes, reset disposable copies, exact raw output/exit/file/symlink/Git parity, and unchanged sources. Output capture is timed; fixture reset, hashing and post-run evidence writes are not.

| Workload | Pairs | Baseline median ms | Candidate median ms | Paired median ratio | Ratio IQR | Wins |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| community-default | 10 | 9393.60 | 9230.55 | 0.98189 | 0.95786–1.00461 | 7/10 |
| community-fix | 10 | 11246.30 | 10775.94 | 0.96976 | 0.94673–1.00586 | 6/10 |
| community-json | 10 | 9171.77 | 9231.83 | 0.98305 | 0.96251–1.01683 | 7/10 |
| ten-file-repeat | 30 | 522.80 | 516.73 | 0.99057 | 0.95216–1.03385 | 18/30 |

Quartiles use the inclusive method. Marginal medians, paired median ratios and median paired deltas are distinct statistics. CPU, order and half-session splits are retained in secondary-summary.json.

The initial ten-file row was 1.04864 (+27.3 ms median paired delta); the separate repeat is 0.99057 (−4.9 ms), with 18/30 candidate wins. The initial downside did not reproduce at that magnitude, but equivalence and absence of small costs are not established. Neither row is erased or pooled.

Community paired reductions are only about 1.7–3.0%, all IQRs cross 1, and only 6–7 of 10 pairs favor the candidate. These observations do not support a clear, consistent broad speedup across repositories. The stronger primary-corpus improvement remains bounded to its measured workload. No statistical-significance, equivalence or universal-performance claim is made.

OS caches, CPU frequency/affinity and external host activity remain uncontrolled; owned CPU jobs were paused. Installed dependency equality is names/versions, not all dependency bytes. One Linux host and Python version. User workload frequency is unknown. Existing CI import/install/order/cache asymmetry remains a separate unresolved evaluation issue.

All public samples are allowlisted fields with keyed opaque digests. Raw findings and source stay local for independent audit. Untimed fix/post-fix companions preserve exact endpoint output and the measured final trees: community checks 1,644 paths with 93 fix records affecting 90 regular-file contents and retains exit 1 for remaining findings; synthetic checks 200 paths with 466 fix records and exit 0. Independent audit completed: all 136 observations, 272 retained Git captures, source/reference/work trees, stream/metadata/tree HMACs, all summary fields, fix/post-fix companions and live provenance passed. Sources stayed unchanged. Intermediate final trees are not retained individually; their digests match independently checked retained trees, with exact parity enforced during execution.
