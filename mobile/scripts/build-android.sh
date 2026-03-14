#!/usr/bin/env bash
# Usage: bash build-android.sh [release]
# release mode requires: KEYSTORE_FILE (base64 .jks), KEYSTORE_PASS, KEY_ALIAS, KEY_PASS
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_TYPE="${1:-debug}"

bash "$SCRIPT_DIR/sync.sh"
cd "$MOBILE_DIR/android"

if [ "$BUILD_TYPE" = "release" ]; then
  [ -z "${KEYSTORE_FILE:-}" ] && { echo "ERROR: KEYSTORE_FILE not set."; exit 1; }
  echo "$KEYSTORE_FILE" | base64 -d > /tmp/release.jks
  ./gradlew bundleRelease \
    -Pandroid.injected.signing.store.file=/tmp/release.jks \
    -Pandroid.injected.signing.store.password="$KEYSTORE_PASS" \
    -Pandroid.injected.signing.key.alias="$KEY_ALIAS" \
    -Pandroid.injected.signing.key.password="$KEY_PASS"
  echo "==> AAB: app/build/outputs/bundle/release/app-release.aab"
else
  ./gradlew assembleDebug
  echo "==> APK: app/build/outputs/apk/debug/app-debug.apk"
fi
