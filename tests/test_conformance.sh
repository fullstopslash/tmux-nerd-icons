#!/usr/bin/env bash
# test_conformance.sh - Run nerd-icons test vectors against vendored resolver
#
# Usage:
#   ./tests/test_conformance.sh
#
# Requires the shared test-vectors spec from the nerd-icons project at
# /home/rain/projects/nerd-icons/spec/test-vectors.yml (development only).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "${SCRIPT_DIR}")"
SPEC_DIR="/home/rain/projects/nerd-icons/spec"
TEST_VECTORS="${SPEC_DIR}/test-vectors.yml"
NERD_ICONS_TEST="/home/rain/projects/nerd-icons/tests/test_resolver.py"

if [[ ! -f "${TEST_VECTORS}" ]]; then
    echo "SKIP: test vectors not found at ${TEST_VECTORS}"
    echo "  (this test requires the nerd-icons repo to be present)"
    exit 0
fi

echo "Running conformance tests against vendored nerd_icons..."
echo "  PYTHONPATH=${PLUGIN_DIR}/scripts"
echo "  test runner: ${NERD_ICONS_TEST}"
echo ""

PYTHONPATH="${PLUGIN_DIR}/scripts" python3 "${NERD_ICONS_TEST}"
exit_code=$?

if [[ ${exit_code} -eq 0 ]]; then
    echo "All conformance tests passed."
else
    echo "FAIL: some conformance tests failed (exit ${exit_code})."
fi

exit ${exit_code}
