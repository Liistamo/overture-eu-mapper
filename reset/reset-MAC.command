#!/bin/bash
# Start over. Double-click in Finder.
#
# What happens:
#   1. Removes cached boundary data and categories.
#   2. Removes all generated maps from output_map/.
#   3. Leaves the Python environment intact (no reinstall needed).

cd "$(dirname "$0")/.."

echo ""
echo "  Removing cached boundaries ..."
rm -f scripts/data/boundaries_cache.geojson
rm -f scripts/data/boundaries_index.csv

echo "  Removing cached categories ..."
rm -f scripts/data/overture_categories.csv

echo "  Removing generated maps ..."
rm -f output_map/*.html

echo ""
echo "  Clean. Run map_build_mac.command to start over."
echo ""
echo "Press any key to close this window..."
read -n 1
