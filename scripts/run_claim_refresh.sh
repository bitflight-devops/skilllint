#!/usr/bin/env bash
# run_claim_refresh.sh — run refresh_claim_values.py and surface its exit
# code as a GITHUB_OUTPUT value.
#
# GitHub Actions `run:` steps use `bash -e` by default, so a bare invocation
# would abort the step (and the job) the instant the script exits non-zero,
# before the caller ever learns *which* non-zero code it was. The workflow
# needs to tell 0 (no drift) apart from 1 (drift written), 2 (fetch failed,
# no cache) and 3 (unexpected error) to decide whether to open a PR or fail
# the job -- hence `set +e` here, isolated from the rest of the job's steps.
set +e
uv run --locked python scripts/refresh_claim_values.py
echo "exit_code=$?" >>"$GITHUB_OUTPUT"
