#!/usr/bin/env bash
# fail_claim_refresh.sh — surface refresh_claim_values.py's exit code as a
# job failure with a message that matches the code (2: unfetchable claim,
# 3: unexpected error -- see scripts/refresh_claim_values.py's docstring).
set -euo pipefail

case "$1" in
    2) echo "::error::A claim's vendor document could not be fetched and no cache exists." ;;
    3) echo "::error::scripts/refresh_claim_values.py raised an unexpected error -- see the 'Refresh claim values' step's log for the traceback." ;;
    *) echo "::error::scripts/refresh_claim_values.py exited with unrecognized code $1." ;;
esac
exit 1
