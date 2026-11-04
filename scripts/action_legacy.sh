#!/usr/bin/env bash
# Compatibility for published releases without structured Action support.
# Preserves their historical output parsing and optional count-only rescan.
set +e # do not exit on non-zero. We capture the exit code ourselves

ARGS=()

# Boolean flags
if [ "${INPUT_CHECK_ONLY}" = "true" ]; then
    ARGS+=("--check")
fi
if [ "${INPUT_FIX}" = "true" ]; then
    ARGS+=("--fix")
fi
if [ "${INPUT_VERBOSE}" = "true" ]; then
    ARGS+=("--verbose")
fi
if [ "${INPUT_NO_COLOR}" = "true" ]; then
    ARGS+=("--no-color")
fi
if [ "${INPUT_TOKENS_ONLY}" = "true" ]; then
    ARGS+=("--tokens-only")
fi
if [ "${INPUT_SHOW_PROGRESS}" = "true" ]; then
    ARGS+=("--show-progress")
fi
if [ "${INPUT_SHOW_SUMMARY}" = "true" ]; then
    ARGS+=("--show-summary")
fi

# Optional string flags
if [ -n "${INPUT_PLATFORM}" ]; then
    ARGS+=("--platform" "${INPUT_PLATFORM}")
fi
if [ -n "${INPUT_FILTER}" ]; then
    ARGS+=("--filter" "${INPUT_FILTER}")
fi
if [ -n "${INPUT_FILTER_TYPE}" ]; then
    ARGS+=("--filter-type" "${INPUT_FILTER_TYPE}")
fi

# Paths (space-separated, split into individual arguments)
read -ra PATH_ARGS <<<"${INPUT_PATHS}"

OUTPUT_FILE="$(mktemp)"
skilllint check "${ARGS[@]}" "${PATH_ARGS[@]}" >"${OUTPUT_FILE}" 2>&1
EXIT_CODE=$?

cat "${OUTPUT_FILE}"

NORMALIZED_OUTPUT="$(tr -d '\r' <"${OUTPUT_FILE}")"
INSPECTED_COUNT="$(sed -n 's/^Total files: \([0-9][0-9]*\)$/\1/p' <<<"${NORMALIZED_OUTPUT}" | tail -n 1)"
if [ "${INPUT_TOKENS_ONLY}" = "true" ] && [ "${EXIT_CODE}" -ne 2 ]; then
    INSPECTED_COUNT="$(grep -cE '^[0-9]+($|[[:blank:]])' <<<"${NORMALIZED_OUTPUT}")"
elif [ "${EXIT_CODE}" -ne 2 ] && [ -z "${INSPECTED_COUNT}" ] && { [ "${INPUT_SHOW_SUMMARY}" != "true" ] || [ "${INPUT_NO_COLOR}" != "true" ]; }; then
    COUNT_ARGS=()
    for ARG in "${ARGS[@]}"; do
        if [ "${ARG}" != "--check" ] && [ "${ARG}" != "--fix" ] && [ "${ARG}" != "--tokens-only" ]; then
            COUNT_ARGS+=("${ARG}")
        fi
    done
    COUNT_OUTPUT="$(skilllint check --no-color "${COUNT_ARGS[@]}" --show-summary "${PATH_ARGS[@]}" 2>&1 || true)"
    INSPECTED_COUNT="$(tr -d '\r' <<<"${COUNT_OUTPUT}" | sed -n 's/^Total files: \([0-9][0-9]*\)$/\1/p' | tail -n 1)"
fi

echo "exit-code=${EXIT_CODE}" >>"$GITHUB_OUTPUT"
echo "inspected-count=${INSPECTED_COUNT}" >>"$GITHUB_OUTPUT"
FINDINGS_OUTPUT="$(sed -E $'s/\033\[[0-?]*[ -\/]*[@-~]//g' "${OUTPUT_FILE}")"
echo "findings=$(grep -oE '(^[[:space:]]*(✗ (ERROR|WARN|INFO)|⚠️? (WARN|INFO)|⚠ (WARN|INFO)|❌|⚠|🔧|ℹ️? (WARN|INFO)|ℹ (WARN|INFO)|ℹ|i INFO) |^FIXED )\[[A-Z]{2}[0-9]{3}(, [A-Z]{2}[0-9]{3})*\]' <<<"${FINDINGS_OUTPUT}" | sed -E 's/^.*\[//; s/\]$//' | tr -d ',' | tr ' ' '\n' | sort -u | xargs)" >>"$GITHUB_OUTPUT"
TOOL_PYTHON="$(uv tool list --show-python | sed -n 's/^skilllint .*\[\([^]]*\)\]$/\1/p' | sed 's/^CPython /Python /')"
echo "tool-python=${TOOL_PYTHON}" >>"$GITHUB_OUTPUT"
echo "tool-version=$(skilllint --version)" >>"$GITHUB_OUTPUT"
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "result=passed" >>"$GITHUB_OUTPUT"
else
    echo "result=failed" >>"$GITHUB_OUTPUT"
fi

exit "${EXIT_CODE}"
