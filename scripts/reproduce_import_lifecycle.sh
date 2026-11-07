#!/usr/bin/env bash
# Same-source diagnostic; REPO, SOURCE, WORK and UV_CACHE_DIR must be explicit.
# WORK must not exist, so existing experiments cannot be silently overwritten.
set -euo pipefail
: "${REPO:?Set REPO to the full-history source checkout}"
: "${SOURCE:?Set SOURCE to the immutable source commit}"
: "${WORK:?Set WORK to a new output directory}"
: "${UV_CACHE_DIR:?Set UV_CACHE_DIR to a populated cache for locked offline installs}"
mode="${MODE:-literal_sync}"
install_args=()
case "$mode" in
    literal_sync) ;;
    forced_reinstall) install_args=(--reinstall-package skilllint) ;;
    *)
        echo "MODE must be literal_sync or forced_reinstall" >&2
        exit 2
        ;;
esac
mkdir "$WORK"
mkdir "$WORK/harness" "$WORK/results"
cp "${BASH_SOURCE[0]}" "$WORK/harness/reproduce_import_lifecycle.sh"
printf '%s\n' "$mode" >"$WORK/results/mode.txt"
git -C "$REPO" show "$SOURCE:scripts/bench_import.py" >"$WORK/harness/bench_import.py"
cp "$REPO/scripts/capture_import_samples.py" "$WORK/harness/"
git -C "$REPO" rev-parse "$SOURCE:packages/skilllint" >"$WORK/results/product-tree.txt"
git -C "$REPO" rev-parse "$SOURCE" >"$WORK/results/source.txt"
uv --version >"$WORK/results/uv-version.txt"
date -u +%FT%TZ >"$WORK/results/started.txt"
# Two replicas reverse factor traversal, and each cell runs both module orders.
# Three measurements per module match the CI sample count, not a significance target.
for replica in 1 2; do
    if [[ "$replica" == 1 ]]; then
        histories=(full shallow)
        bytecodes=(write disabled)
        warmups=(0 1)
        orders=(forward reverse)
    else
        histories=(shallow full)
        bytecodes=(disabled write)
        warmups=(1 0)
        orders=(reverse forward)
    fi
    # Predeclared rebuild companion holds history and bytecode policy fixed.
    if [[ "$mode" == forced_reinstall ]]; then
        histories=(full)
        bytecodes=(write)
    fi
    for history in "${histories[@]}"; do
        for bytecode in "${bytecodes[@]}"; do
            for warmup in "${warmups[@]}"; do
                for order in "${orders[@]}"; do
                    name="r${replica}-${history}-${bytecode}-w${warmup}-${order}"
                    checkout="$WORK/$name"
                    # Full clone is from the explicit source ref; shallow is cut to that same commit.
                    git clone --quiet --no-hardlinks "$REPO" "$checkout"
                    git -C "$checkout" checkout --quiet --detach "$SOURCE"
                    if [[ "$history" == shallow ]]; then
                        git -C "$checkout" rev-parse HEAD >"$checkout/.git/shallow"
                        git -C "$checkout" tag -l | xargs -r git -C "$checkout" tag -d >/dev/null
                    fi
                    export PYTHONPYCACHEPREFIX="$checkout/bytecode"
                    export UV_LINK_MODE=copy
                    unset PYTHONDONTWRITEBYTECODE
                    if [[ "$bytecode" == disabled ]]; then export PYTHONDONTWRITEBYTECODE=1; fi
                    args=()
                    if [[ "$order" == reverse ]]; then args=(--reverse); fi
                    for stage in 1 2; do
                        (
                            cd "$checkout"
                            uv sync --locked --offline --python 3.12 "${install_args[@]}" >"$WORK/$name-stage$stage-install.log" 2>&1
                            .venv/bin/python "$WORK/harness/capture_import_samples.py" --runs 3 --warmups "$warmup" "${args[@]}" >"$WORK/results/$name-stage$stage.json"
                        )
                    done
                    # Identity probes run AFTER both stages so they cannot warm measured imports.
                    (
                        cd "$checkout"
                        .venv/bin/python -c 'import hashlib,json,platform; from pathlib import Path; import skilllint,skilllint.rules; from skilllint.rule_registry import RULE_REGISTRY; print(json.dumps({"python":platform.python_version(),"module_relative_path":str(Path(skilllint.__file__).relative_to(Path.cwd())),"module_sha256":hashlib.sha256(Path(skilllint.__file__).read_bytes()).hexdigest(),"runtime_version":skilllint.__version__,"rule_codes":sorted(RULE_REGISTRY)},indent=2))' >"$WORK/results/$name-identity.json" 2>"$WORK/$name-identity-stderr.log"
                        git rev-parse HEAD >"$WORK/results/$name-head.txt"
                        git rev-parse --is-shallow-repository >"$WORK/results/$name-shallow.txt"
                        git rev-list --count HEAD >"$WORK/results/$name-history-count.txt"
                    )
                    echo "$name completed"
                done
            done
        done
    done
done
date -u +%FT%TZ >"$WORK/results/finished.txt"
