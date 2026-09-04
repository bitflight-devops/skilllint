#!/usr/bin/env bash
# open_drift_pr.sh — Commit provenance-registry.json drift and open/update its PR.
#
# Run only after scripts/refresh_claim_values.py has already rewritten
# packages/skilllint/schemas/provenance-registry.json in the working tree
# (its exit code 1 means it did). This script does the git/gh side: commit,
# push to a fixed bot-owned branch, and open a PR the first time -- a later
# run pushing more commits to the same branch updates that PR automatically,
# so this only needs to call `gh pr create` when no PR exists yet.
#
# Requires: git, gh (authenticated), and GITHUB_TOKEN / a git remote already
# configured for push (both true in the calling GitHub Actions job).

set -euo pipefail

BRANCH="chore/claim-drift-auto"
REGISTRY_PATH="packages/skilllint/schemas/provenance-registry.json"

if git diff --quiet -- "$REGISTRY_PATH"; then
    echo "Nothing to commit — $REGISTRY_PATH unchanged."
    exit 0
fi

git checkout -B "$BRANCH"
git add "$REGISTRY_PATH"
git commit -m "chore(provenance): sync vendor-backed claim values"
git push --force-with-lease origin "$BRANCH"

if gh pr view "$BRANCH" >/dev/null 2>&1; then
    echo "PR for $BRANCH already exists — push updated it."
    exit 0
fi

gh pr create \
    --base main \
    --head "$BRANCH" \
    --title "chore(provenance): sync vendor-backed claim values" \
    --body "$(
        cat <<'EOF'
Automated run of `scripts/refresh_claim_values.py` found upstream documentation drift. See the diff for which claim(s) changed and what values were added or removed.

Additions are usually safe to merge as-is. A removal means Claude Code stopped documenting something this repo's code still accepts — read `packages/skilllint/rules/hk_series.py`'s corresponding constant before merging, since the code may need a matching change, not just the registry.
EOF
    )"
