#!/usr/bin/env bash
# GridNudge: Generate / prepare all 7 processed datasets and validate schemas
set -euo pipefail

echo "=========================================="
echo "Preparing GridNudge Datasets"
echo "=========================================="

for s in grid sessions stations rct battery ved weather; do
    echo "Running data/scripts/fetch_${s}.py..."
    python data/scripts/fetch_${s}.py
done

echo "Validating generated schemas..."
python data/scripts/validate.py

echo "Dataset preparation complete."
