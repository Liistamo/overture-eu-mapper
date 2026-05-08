#!/bin/bash
# Build a map.
# macOS: double-click in Finder. Linux: run from a terminal.
#
# What happens:
#   1. Checks that Python is installed.
#   2. Creates a Python environment and installs dependencies (first run only).
#   3. Opens an interactive prompt where you pick cities and categories.
#   4. Fetches places from Overture Maps.
#   5. Saves a standalone HTML map in output/ and opens it in your browser.

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo ""
    echo "  Python is not installed."
    echo "  Download it from https://www.python.org/downloads/ and run the installer."
    echo ""
    echo "Press any key to close this window..."
    read -n 1
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

echo ""
echo "Press any key to close this window..."
read -n 1
