#!/usr/bin/env bash
# GridNudge: Master verification script
set -euo pipefail

echo "=========================================="
echo "Step 1: Prepare Datasets"
echo "=========================================="
bash scripts/prepare_data.sh

echo "=========================================="
echo "Step 2: Run Python Test Suite"
echo "=========================================="
pytest -q

echo "=========================================="
echo "Step 3: Audit Project Claims"
echo "=========================================="
python scripts/check_claims.py

echo "=========================================="
echo "Step 4: Check Module Ownership"
echo "=========================================="
python scripts/check_ownership.py

echo "=========================================="
echo "Step 5: Dashboard Build Verification"
echo "=========================================="
cd dashboard
npm run build
cd ..

echo "=========================================="
echo "SUCCESS: All GridNudge Verifications Passed!"
echo "=========================================="
