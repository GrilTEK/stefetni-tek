#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Creating www symlink..."
node scripts/symlink.js

echo "==> Running cap sync..."
npx cap sync
