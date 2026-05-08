#!/bin/bash
# Build a map. Run from a terminal or make executable and double-click.

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo ""
    echo "  Python is not installed."
    echo "  Download it from https://www.python.org/downloads/ and run the installer."
    echo ""
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo ""
    echo "  First run. Setting up Python environment ..."
    echo ""
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r scripts/requirements.txt -q
    echo ""
    echo "  Environment ready."
    echo ""
fi

.venv/bin/python3 scripts/build_map.py
