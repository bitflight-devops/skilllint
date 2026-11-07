# Staged hook evaluation

`scripts/bench_staged.py` measures **prek's actual staged-file selection** and
hook subprocess execution, rather than passing a simulated list of filenames.
It complements, rather than changes, the strict CLI paired harness.

## Contract

Prepare a self-contained disposable Git repository with staged changes and a
local `language: system` hook named `skilllint`, using the published manifest's
entry, files, exclude and pass_filenames fields. Supply installed baseline and
candidate wheel environments with identical Python and dependency versions.
The runner puts the selected environment's bin directory first on PATH and runs
`prek run skilllint --stage pre-commit --color never`, without file-selection
arguments. This measures a local-system, preinstalled-wheel hook: it does not
measure remote `language: python` provisioning, installation, or Git commit
creation. Only trusted corpus/configuration and executables are supported.

```sh
uv run python -m scripts.bench_staged \
  --baseline /path/to/baseline/bin/python \
  --candidate /path/to/candidate/bin/python \
  --prek /path/to/prek \
  --source /path/to/prepared-git-corpus \
  --artifacts /path/to/new-private-evidence \
  --pairs 10 --warmups 2 --timeout 120
```

All counts and timeout are explicit experiment parameters. Run a same-executable
A/A control too. Endpoints alternate AB/BA continuously across warmup and
measured pairs. Every invocation starts from the same snapshot at the same
absolute path. Reset, snapshot, Git checks and evidence capture are untimed;
framework startup, discovery, hook execution and output capture are timed.
Wall and child user/system CPU use the paired harness's definitions. Reserve a
quiet timing window; OS caches, host contention and CPU frequency are otherwise
uncontrolled. This is a check-only experiment: hooks must leave files unchanged.

Exact stdout, stderr and exit parity is required, without normalization. Only
exit 0/1 is accepted; separately inspect the first raw outcome to establish
whether 1 represents actual lint findings rather than a framework error.
Working-tree paths, bytes, modes and symlinks must remain unchanged. Git's index
stages, object IDs, flags and binary cached diff must remain exactly equal.
Full Git trees before/after are retained privately, but raw index stat-cache
bytes need not match: the framework may legitimately refresh them. This is not
a claim that every Git metadata byte stays unchanged. Source snapshot equality
including Git is checked even on failure. Dependencies and interpreter metadata
are checked at both ends; verify installed/source bytes separately for stronger
provenance.

Partial staging requires a separate behavioral companion: prek emits unique
stash paths even with quiet output, so strict raw-stderr parity rejects that
case. Do not normalize those logs away or publish its failed timing as a
speedup. Compare hook findings exactly, verify the staged version was supplied,
verify the index and restored unstaged bytes, and retain raw framework logs with
the expected stash/restore relationship checked explicitly.

## Evidence

Only `public.json` is an allowlisted export; its fields reuse the paired CLI
schema. Every other file is private, including corpus, commands/configuration,
Git snapshots, index inspections, package metadata, keyed-digest key and raw
findings. The export is incomplete until all comparisons pass. Its opaque
HMACs cannot be compared across experiments. Review the export before copying
it into a public repository. Results establish parity only for the measured
workload and framework configuration, not all hook installations or fixes.
