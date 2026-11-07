# Fresh paired import diagnostic

Baseline 85813670fbaf8755cc81698497b992cb0a1d2b60 versus candidate 41a53b7a7b00e236f2f2f8fc076dbaa965bf2ac8. CPython 3.12.14 wheel installs, matching 29 dependency name/version entries. Same interpreter hash; source/wheel/installed package bytes checked.

Each endpoint ran a fresh `python -I -c "import skilllint"` or `python -I -c "import skilllint.rules"`. Two discarded warmup pairs and 30 measured alternating AB/BA pairs per workload; no competing owned jobs. Wall time surrounds subprocess completion with piped output; completed-child user/system CPU is also recorded. Both imports returned zero with empty stdout/stderr in every observation. Source/install provenance was independently rechecked after the run.

Package marginal medians: 48.40 to 48.92 ms; median paired ratio 0.99685, IQR 0.95346–1.03457; 16/30 candidate wins. Median paired absolute delta −0.147 ms.

Rules marginal medians: 159.31 to 161.88 ms; median paired ratio 1.02084, IQR 0.98043–1.08935; 10/30 candidate wins. Median paired absolute delta +3.382 ms.

All 128 observation records, ordering, warmup exclusion and summary statistics were independently audited. Quartiles use `statistics.quantiles(method="inclusive")`. Empty stdout/stderr were enforced by the runner and recorded as booleans; raw streams were not retained for independent byte rehashing. The output check was audited through the code invariant and saved booleans. Marginal medians and medians of paired differences are different statistics. These results do not reproduce the larger CI mean regressions in this wheel-based session, but do not establish that CI results are noise or that environments/install modes are equivalent. A small rules-import downside remains observed. OS cache state/frequency/other-host activity were not controlled; no statistical equivalence or significance claim is made. This session is separate from historical measurements and from the pending real-corpus evaluation.
