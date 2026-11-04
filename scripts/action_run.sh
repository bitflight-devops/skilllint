#!/usr/bin/env bash
set -euo pipefail
TOOL_ROOT="$(uv tool dir)/skilllint"
TOOL_PYTHON="${TOOL_ROOT}/bin/python"
if [ ! -f "${TOOL_PYTHON}" ]; then
    TOOL_PYTHON="${TOOL_ROOT}/Scripts/python.exe"
fi
"${TOOL_PYTHON}" "${GITHUB_ACTION_PATH}/scripts/action_dispatch.py"
