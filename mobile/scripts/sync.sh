#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(dirname "$SCRIPT_DIR")"
echo "==> Ensuring www symlink..."
node "$SCRIPT_DIR/symlink.js"
echo "==> Running: npx cap sync"
cd "$MOBILE_DIR"
npx cap sync
echo "==> Sync complete."
