#!/usr/bin/env bash
set -euo pipefail

case "$1" in
    2) echo "::error::A claim's vendor document could not be used to refresh values." ;;
    3) echo "::error::scripts/refresh_claim_values.py raised an unexpected error -- see the 'Refresh claim values' step's log for the traceback." ;;
    *) echo "::error::scripts/refresh_claim_values.py exited with unrecognized code $1." ;;
esac
exit 1
