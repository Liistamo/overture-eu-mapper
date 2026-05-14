#!/bin/bash
# One-time setup for macOS.
# Removes the quarantine flag so build-MAC.command can be
# double-clicked in Finder without being blocked by Gatekeeper.
#
# HOW TO RUN (once only):
#   1. Open Terminal  (Applications → Utilities → Terminal)
#   2. Drag this file into the Terminal window
#   3. Press Enter

cd "$(dirname "$0")"

xattr -dr com.apple.quarantine . 2>/dev/null

echo ""
echo "  Done. You can now double-click build-MAC.command."
echo ""
