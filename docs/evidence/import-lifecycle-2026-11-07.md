# Fresh import lifecycle reproduction

This is a **new experiment**, not recovered historical evidence. A bounded search
of the available Skilllint workspaces, shared workspace, and temporary files did
not find the earlier lifecycle/factor observations. The qualitative historical
statement in `docs/import-benchmark-comparability.md` must not be mistaken for a
raw-data-backed result from that earlier run.

## Question and boundary

Can sequential setup position change the import benchmark result without any
product code change, and how do excluded warmups, bytecode, module order, and Git
history affect that observation? This is a diagnostic for the import CI harness.
It does not measure the user's end-to-end lint workflow, justify removing product
startup costs, or establish equivalence between different product revisions.

The fixed source commit is `ae5c0dfcb5e36ef97e1de3861cf84db8345c1605`.
Both lifecycle stages in every cell use that commit and the same locked editable
installation. The original benchmark script is copied once and used for every
cell. The reproduction command extracts it from `SOURCE`, so later working-tree
docstring edits do not change the reproduced timer bytes. Its SHA-256 is
`8247e424f78f0ab67a906503fdfdc379aead0f53d4a77db95732a0e9e1447455`.
The recorder wraps its private timing function to retain each unrounded returned
value; it does not replace or alter the child timer. Unit tests verify observation
order, warmup exclusion, exact values, and restoration after failure.

## Protocol

Run `scripts/reproduce_import_lifecycle.sh` with `REPO` set to this checkout,
`SOURCE` set to the commit above, `WORK` set to a new absolute directory, and
`UV_CACHE_DIR` set to a populated cache. The directory must be new so a rerun
cannot overwrite earlier observations. The runner retains cloned checkouts,
install logs, raw captures, and identity probes locally. Choose storage with room
for every retained environment and clone: this experiment copies 32 development
environments for the main matrix and eight more for the companion. The shared
4.9 GB temporary filesystem on this host was insufficient (see recovery below).

- Two replicas traverse the factor combinations in opposite orders. Every
  combination has both package-first and rules-first module order. This is
  deterministic reversal, not randomization or a confidence-interval design.
- Factors: full versus one-commit history, writable versus disabled bytecode,
  zero versus one excluded import per module, and forward versus reversed module
  order. Each measured module has three fresh-process observations, matching CI.
- Every cell starts with a new local clone and new editable virtual environment.
  `UV_LINK_MODE=copy` avoids sharing installed dependency files between cells.
  Dependencies come from an existing uv cache; this is not a network-install test.
- Each cell has its own initially absent `PYTHONPYCACHEPREFIX`. Stage 2 reuses it.
  The disabled factor adds `PYTHONDONTWRITEBYTECODE=1` throughout both stages.
  Standard-library imports by the recorder can populate that prefix before the
  first target import. No application import probe runs before the measurements.
- Both stages run `uv sync --locked --offline --python 3.12`. The second is
  normally an audited no-op for identical source. This follows the literal sync
  command but is not a forced rebuild or a different-source baseline checkout.
- The shallow control truncates visible history to the same HEAD and removes
  tags in the experiment clone; underlying Git objects are retained. It tests
  runtime version/history semantics, not clone download cost or a smaller object
  database. Full and shallow source bytes are identical.
- Identity probes run only after both stages. They record the actual imported
  relative source path, file hash, runtime version, and sorted registered rule
  codes. These observations do not prove end-to-end lint behavior.

The child timer begins immediately before the target import. It excludes
interpreter startup, parent orchestration, installation, and process teardown.
Zero warmups mixes the first application import with subsequent reuse; one
warmup records that preparation separately and excludes it from the three-sample
aggregate. Neither mode is an OS-cold measurement: filesystem caches were not
flushed, dependencies were cached, and all cells share one host. Other task-owned
timing and heavy checks were paused during this run; host contention is still
uncontrolled. No significance claim is supported by two replicas.

## Evidence and interpretation

For the full-history, writable-bytecode subset, each row summarizes four paired
cells (two replicas, both module orders). Ratios use the reported three-sample
means: stage 2 divided by stage 1. Below 1 means the second lifecycle stage was
faster despite identical product source. Medians and ranges are descriptive,
not confidence intervals or regression thresholds.

| Warmups | Import | Median ratio | Minimum–maximum paired ratio |
| --- | --- | --- | --- |
| 0 | package | 0.913 | 0.585–1.083 |
| 0 | rules | 0.818 | 0.666–0.956 |
| 1 | package | 0.927 | 0.882–1.055 |
| 1 | rules | 1.006 | 0.882–1.232 |

The rules import shows a substantial same-source setup-position effect without
excluded warmups. One warmup brings its median ratio close to 1, but individual
pairs still span 0.882–1.232. Package imports do not show the same degree of
normalization. Thus the result supports measuring and naming warm-cache imports
separately; it does **not** establish universal removal of order effects.

With bytecode writing disabled, the full-history median first-stage means were
816–865 ms for the package and 1,431–1,476 ms for rules across warmup settings,
versus 233–276 ms and 418–565 ms with writing enabled. Excluded imports cannot
prepare reusable bytecode when writes are disabled. Residual second/first ratios
still varied, including package imports becoming slower in the zero-warmup
condition. This is a cache-policy diagnostic, not a product speedup estimate.

The history control retained the same product tree and registered rule codes,
but changed runtime version identity and emitted shallow-history warnings.
It does not establish a large timing benefit from full history.

### Predeclared forced-reinstall companion

The companion holds history at full and bytecode at writable, with both warmup
settings and both module orders in two reversed-traversal replicas (eight cells).
Set `MODE=forced_reinstall` and a different new `WORK` directory to reproduce it.
Both stages add `--reinstall-package skilllint` to locked offline sync. This
separates explicit editable rebuild/reinstallation from the main experiment's
usually no-op second sync. It still uses identical source rather than a different
baseline revision, and is reported separately.

### Interrupted capture, preserved observations

The main run completed 22 cells (44 stage captures), then the next fresh install
failed copying the prek executable because the temporary filesystem was full.
That failed attempt produced no timed observations. The partial environment and
failure log were preserved. Only the already-measured virtual environments were
relocated to workspace storage, retaining symlinks at their original paths; they
were not measured again. Source clones, raw captures, and bytecode prefixes stayed
in place. This freed space for fresh remaining cells on the **same original
temporary filesystem**, rather than changing the storage medium mid-experiment.

The staged-workflow evaluation used the host during the pause. The remaining
cells therefore belong to a separate resumed timing session, not an uninterrupted
counterbalanced run. The raw evidence identifies the session boundary and failed
attempt. Comparisons below use each cell's stage-2/stage-1 ratio; cross-cell
summaries remain descriptive, with the time gap and host-cache state uncontrolled.

## Forced-reinstall results

All eight companion cells completed. Every stage's retained install log records
an editable build and installation; stage 2 also records uninstallation.
The same within-cell ratio definition applies (four paired cells per row):

| Warmups | Import | Median ratio | Minimum–maximum paired ratio |
| --- | --- | --- | --- |
| 0 | package | 0.843 | 0.771–1.013 |
| 0 | rules | 0.638 | 0.482–0.935 |
| 1 | package | 1.280 | 0.458–1.504 |
| 1 | rules | 1.114 | 0.833–1.328 |

The forced-reinstall warmup results remain noisy, especially package imports:
the observed range is 0.458–1.504, and the median is above 1. Rules imports also
retain variation. These data do not establish that warmups universally normalize
rebuild lifecycle costs, or that they make first-use costs disappear.

This companion measures forced rebuild/reinstallation separately from literal
same-source sync. It is not a different-product baseline comparison, and the
warmup's excluded work remains a real startup cost recorded in the raw samples.

## Raw artifacts and provenance

- [Main matrix](import-lifecycle-2026-11-07.json): 32 complete cells, 64 stage
  captures, the failed pre-measurement install, exact initial/resume protocols,
  and session labels. No successful timing was discarded or repeated.
- [Forced-reinstall companion](import-reinstall-2026-11-07.json): eight complete
  cells, 16 stage captures, and the exact companion protocol.
- Every capture includes unrounded timings for measured and excluded imports,
  module order, warmup count, and the existing harness's rounded aggregates.
- Identity records confirm identical source/product trees, imported source hash,
  49 registered rule codes, Python 3.12.14 build, and 57 identical non-project
  installed distributions across all cells. Full history exposes 663 commits;
  the truncated control exposes one. The runtime versions are respectively
  `1.22.3.dev14+gae5c0dfcb` and `0.1.dev1+gae5c0dfcb`.
- Install and warning paths are replaced with symbolic roots. No hostname,
  credentials, environment dump, or private corpus is included. The raw protocol
  text and public package/version identifiers are retained.
- The measured benchmark bytes are from the fixed source commit above. The later
  docstring-only removal of its stale hardcoded rule count changes its file hash,
  not its timer; use that fixed commit when reproducing the captured harness hash.

## Validation status

The focused fast profile passed all 12 import/recorder tests. Full hook validation
passed after formatting the new shell script. The full suite is pending until
the separately timed staged-workflow repeat finishes. This report does not claim
that completion gate has passed.
