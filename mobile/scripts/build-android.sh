#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${1:-debug}"

echo "==> Syncing Capacitor..."
bash scripts/sync.sh

echo "==> Building Android ($MODE)..."
cd android

if [ "$MODE" = "release" ]; then
  if [ -z "${KEYSTORE_PATH:-}" ] || [ -z "${KEYSTORE_PASSWORD:-}" ] || \
     [ -z "${KEY_ALIAS:-}" ] || [ -z "${KEY_PASSWORD:-}" ]; then
    echo "ERROR: Release build requires KEYSTORE_PATH, KEYSTORE_PASSWORD, KEY_ALIAS, KEY_PASSWORD env vars."
    exit 1
  fi
  ./gradlew bundleRelease \
    -Pandroid.injected.signing.store.file="$KEYSTORE_PATH" \
    -Pandroid.injected.signing.store.password="$KEYSTORE_PASSWORD" \
    -Pandroid.injected.signing.key.alias="$KEY_ALIAS" \
    -Pandroid.injected.signing.key.password="$KEY_PASSWORD"
  echo "==> Release bundle: app/build/outputs/bundle/release/app-release.aab"
else
  ./gradlew assembleDebug
  echo "==> Debug APK: app/build/outputs/apk/debug/app-debug.apk"
fi
