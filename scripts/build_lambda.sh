#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

rm -rf build/lambda && mkdir -p build/lambda/config
cp -r gridnudge services agent build/lambda/
cp config/safety.yaml build/lambda/config/

cat > build/lambda/requirements.txt <<'EOF'
numpy>=1.24.0,<2.0.0
pydantic>=2.0
pyyaml>=6.0
EOF

find build/lambda -name "__pycache__" -type d -prune -exec rm -rf {} +
echo "Lambda package staged in build/lambda"
