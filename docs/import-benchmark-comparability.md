# Import benchmark comparability

The import CI job measures fresh-process **warm-cache** imports. Before measuring
each module it performs one excluded import in a separate child process. This
prepares bytecode and may also warm filesystem and Git data. It is not a measure
of first-install startup, and it does not eliminate host contention or all order
effects. The timer starts inside each child immediately before the target import;
interpreter startup is excluded.

`bench_import.py --warmups 1` emits `warm_cache_import_*` metrics. Its default
`--warmups 0` retains the original mixed-first-use behavior and `import_*` metric
names. Old history is retained, not rewritten or compared as the same series.
The warmup is performed before each module's measured samples, not once globally.
The sample count remains three per module, so outliers remain a limitation.

CI preserves the workflow revision's script and uses those exact bytes for both endpoints.
PR baseline checkout uses the immutable event base SHA; manual dispatch still
accepts the supplied base ref, or skips comparison if it is empty. Historical
compare refs remain supported because the harness is saved before their checkout. Both endpoints use full Git history and locked editable installs. Equal history
normalizes version identity and shallow-checkout warnings; it is not evidence of
a large timing benefit.
Installed distribution metadata may survive a source checkout and therefore is
not proof of source identity. The checked-out commit and actual imported source
must be considered when interpreting results.

[Fresh lifecycle and factor evidence](evidence/import-lifecycle-2026-11-07.md)
reproduces setup-position differences without a product code change. It retains
raw observations, reversed module/factor order, bytecode and history controls,
and a separate forced-reinstall companion. One excluded import reduced the
median rules-import setup-position effect in this experiment, but did not
eliminate individual variation or uniformly normalize package imports. The
report distinguishes its interrupted sessions and retained failed install from
completed measurements. This does not establish product equivalence or erase
startup costs or residual regressions.
The separate masking evaluation and its controlled workload evidence are tracked
in [PR 371](https://github.com/bitflight-devops/skilllint/pull/371).

First-install performance needs a separate, symmetric fresh-environment experiment.
This job is not a replacement for paired CLI workloads, cold-cache analysis,
multiple hosts/Python versions, or actual staged-hook execution.
