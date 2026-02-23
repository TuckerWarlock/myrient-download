#!/usr/bin/env bash

MAGENTA='\033[0;35m'
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo_magenta() { echo; echo -e "--- ${MAGENTA}$1${NC} ---"; }

if [ "$(dirname "$0")" == "." ]; then
    cd ..
fi

check_return() {
    if [ "$1" -ne 0 ]; then echo -e "${RED}Failed${NC}"; exit 1; fi
    echo -e "${GREEN}Passed${NC}"
}

echo "Running code checks locally"
uv sync

echo_magenta "Pytest"
uv run pytest -q --show-capture=no
check_return $?

echo_magenta "Flake8"
uv run flake8 myrient_download/ tests/
check_return $?

echo_magenta "Mypy"
uv run mypy myrient_download/
check_return $?
