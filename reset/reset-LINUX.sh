#!/bin/bash
# Start over. Run from a terminal.

cd "$(dirname "$0")/.."

echo ""
echo "  Removing cached boundaries ..."
rm -f scripts/data/boundaries_cache.geojson
rm -f scripts/data/boundaries_index.csv

echo "  Removing cached categories ..."
rm -f scripts/data/overture_categories.csv

echo "  Removing generated maps ..."
rm -f output/*.html

echo ""
echo "  Clean. Run build-LINUX.sh to start over."
