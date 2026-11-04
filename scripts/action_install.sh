#!/usr/bin/env bash
set -euo pipefail
if [ "${INPUT_VERSION}" = "source" ]; then
    uv tool install --python "${INPUT_PYTHON_VERSION}" "${GITHUB_ACTION_PATH}"
elif [ "${INPUT_VERSION}" = "latest" ]; then
    uv tool install --python "${INPUT_PYTHON_VERSION}" skilllint
else
    uv tool install --python "${INPUT_PYTHON_VERSION}" "skilllint==${INPUT_VERSION}"
fi
