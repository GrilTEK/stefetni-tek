# Štafetni Tek – Mobile App (Android & iOS)

The native app is a Capacitor 6 wrapper around the same `frontend/` source used by the web server. No duplicate codebase — one HTML/JS source, two platforms.

---

## Prerequisites

Install these on your laptop before anything else.

### All platforms
- **Node.js 20+** — https://nodejs.org (use the LTS installer)
- **Git** — https://git-scm.com

### Android
- **Java 17 (JDK)** — https://adoptium.net (pick "Temurin 17")
- **Android Studio** — https://developer.android.com/studio
  - During setup, install: Android SDK, Android SDK Platform-Tools, an Android emulator image (e.g. Pixel 7, API 34)
  - After install, open SDK Manager → SDK Tools → check **Android SDK Command-line Tools**
- Set environment variables (add to `~/.bashrc` or `~/.zshrc`):
  ```bash
  export JAVA_HOME=/path/to/jdk17          # e.g. /usr/lib/jvm/temurin-17 on Linux
  export ANDROID_HOME=$HOME/Android/Sdk    # default Android Studio path on Linux/Mac
  export PATH=$PATH:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin
  ```

### iOS (macOS only)
- **Xcode 15+** from the App Store
- **CocoaPods**: `sudo gem install cocoapods`
- An Apple Developer account (free works for device testing; paid required for App Store)

---

## First-time setup

```bash
# 1. Clone the repo
git clone https://github.com/GrilTEK/stefetni-tek.git
cd stefetni-tek/mobile

# 2. Install Capacitor and all plugins
npm install

# 3. Create the www symlink (mobile/www -> ../frontend)
node scripts/symlink.js

# 4. Add the Android platform (creates mobile/android/)
npx cap add android

# 5. Add the iOS platform (macOS only)
npx cap add ios
```

After step 4 and 5, commit the generated native project folders — CI needs them:
```bash
git add mobile/android mobile/ios   # whichever you added
git commit -m "chore: add Capacitor native projects"
git push
```

---

## Android manifest permissions

After `npx cap add android`, open `mobile/android/app/src/main/AndroidManifest.xml` and add the following permissions inside `<manifest>` (before `<application>`):

```xml
<!-- Location -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />

<!-- Bluetooth LE (Android 12+) -->
<uses-permission android:name="android.permission.BLUETOOTH_SCAN"
    android:usesPermissionFlags="neverForLocation" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />

<!-- Bluetooth (Android ≤ 11) -->
<uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30" />
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN" android:maxSdkVersion="30" />

<!-- Notifications -->
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

<!-- Network -->
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.INTERNET" />
```

Also add inside `<application>` (before the closing `</application>` tag):
```xml
<service
    android:name="com.getcapacitor.plugin.geolocation.GeolocationForegroundService"
    android:exported="false"
    android:foregroundServiceType="location" />
```

---

## iOS Info.plist entries

After `npx cap add ios`, open `mobile/ios/App/App/Info.plist` and add:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Štafetni Tek potrebuje lokacijo za sledenje trase.</string>

<key>NSLocationAlwaysUsageDescription</key>
<string>Štafetni Tek potrebuje lokacijo v ozadju za sledenje trase.</string>

<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>Štafetni Tek potrebuje lokacijo v ozadju za sledenje trase.</string>

<key>NSBluetoothAlwaysUsageDescription</key>
<string>Štafetni Tek uporablja Bluetooth za zaznavanje skupin.</string>

<key>NSBluetoothPeripheralUsageDescription</key>
<string>Štafetni Tek uporablja Bluetooth za zaznavanje skupin.</string>

<key>UIBackgroundModes</key>
<array>
    <string>location</string>
</array>
```

---

## Daily development workflow

```bash
cd stefetni-tek/mobile

# Sync web assets + plugin code into native projects
bash scripts/sync.sh

# Open in Android Studio (then press ▶ Run)
npx cap open android

# Open in Xcode (macOS only)
npx cap open ios
```

Or run directly on a connected device / emulator:
```bash
npx cap run android       # needs a device or emulator running
npx cap run ios           # macOS + Xcode only
```

---

## Building a debug APK

```bash
cd stefetni-tek/mobile
bash scripts/build-android.sh debug
# Output: android/app/build/outputs/apk/debug/app-debug.apk
```

Install on a connected Android device:
```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

CI also builds this automatically on every push to `main` and uploads it as a GitHub Actions artifact (kept 7 days).

---

## Building a release APK / AAB

### 1. Create a keystore (one-time)
```bash
keytool -genkey -v -keystore stefetni-tek.keystore \
  -alias stefetnitek -keyalg RSA -keysize 2048 -validity 10000
```
**Keep this file safe. Back it up. Never commit it.**

### 2. Set environment variables
```bash
export KEYSTORE_PATH=/absolute/path/to/stefetni-tek.keystore
export KEYSTORE_PASSWORD=your_store_password
export KEY_ALIAS=stefetnitek
export KEY_PASSWORD=your_key_password
```

### 3. Build
```bash
bash scripts/build-android.sh release
# Output: android/app/build/outputs/bundle/release/app-release.aab
```

Upload the `.aab` to Google Play Console.

---

## Push notifications

### Local notifications (already wired in)
`STNative.nativeNotify(title, body)` uses `@capacitor/local-notifications` — these work without any server setup. They fire on the device when the app calls them (e.g. proximity alerts).

### Remote push notifications (FCM — optional, future feature)

To add Firebase Cloud Messaging so the server can push to devices:

**1. Install the plugin**
```bash
cd mobile
npm install @capacitor/push-notifications
npx cap sync
```

**2. Create a Firebase project**
- Go to https://console.firebase.google.com
- Add project → Add Android app (package: `si.scpet.stefetnitek`)
- Download `google-services.json` → place at `mobile/android/app/google-services.json`
- For iOS: download `GoogleService-Info.plist` → drag into Xcode project root

**3. Add to Android build files**

`mobile/android/build.gradle` — inside `dependencies {}`:
```groovy
classpath 'com.google.gms:google-services:4.4.0'
```

`mobile/android/app/build.gradle` — at the very bottom:
```groovy
apply plugin: 'com.google.gms.google-services'
```

**4. Request permission in the app**
Add to `frontend/src/utils/native.js` inside the `DOMContentLoaded` block:
```js
const Push = plugin("PushNotifications");
if (Push) {
  Push.requestPermissions();
  Push.addListener("registration", (token) => {
    // Send token to your backend: apiFetch("/device-token", { method:"POST", body: JSON.stringify({token: token.value}) })
    console.log("FCM token:", token.value);
  });
  Push.addListener("pushNotificationReceived", (notification) => {
    console.log("Push received:", notification);
  });
}
```

**5. Backend: send a push**
From your FastAPI backend, use the `firebase-admin` SDK:
```bash
pip install firebase-admin
```
```python
import firebase_admin
from firebase_admin import credentials, messaging

cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

def send_push(token: str, title: str, body: str):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
    )
    messaging.send(message)
```

---

## App updates

### Web content updates (no app store release needed)
Since the app loads from `https://tek.griltek.si`, any change you deploy to the server is immediately live in the app on next launch — no app store update required. This covers all UI and logic changes.

### Native updates (when you change `mobile/` or native config)
These require a new build and distribution through Google Play / App Store:
- New Capacitor plugin added
- AndroidManifest / Info.plist changes
- Permissions changes
- New native SDK integration

Workflow:
```bash
cd mobile
npm install          # if you added new plugins
bash scripts/sync.sh
bash scripts/build-android.sh release
# Upload .aab to Google Play Console
```

### Capacitor Live Updates (optional, paid)
Ionic Appflow offers over-the-air JS updates that bypass the app store review for web content changes. Not required for this project since the server already serves updated content directly.

---

## Google Play — first submission checklist

1. Create app at https://play.google.com/console
2. Fill in: store listing (title, description, screenshots), content rating, privacy policy URL
3. Set up internal testing track first
4. Upload `.aab` (release build)
5. Add testers by email → they install via Play Store link
6. After testing, promote to production

**Required before submission:**
- App icon: 512×512 PNG (create in `mobile/android/app/src/main/res/`)
- Feature graphic: 1024×500 PNG
- At least 2 screenshots per device type

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `www` symlink broken | Run `node scripts/symlink.js` |
| `npx cap sync` fails | Make sure `mobile/android/` or `mobile/ios/` exists (run `npx cap add android` first) |
| App shows blank screen | Check that `https://tek.griltek.si` is reachable and CORS allows `capacitor://localhost` |
| GPS not working on Android | Check permissions in Settings → Apps → Štafetni Tek → Permissions → Location |
| BLE scan fails | Ensure Location permission is granted (required for BLE scan on Android) |
| Build fails: SDK not found | Set `ANDROID_HOME` and `JAVA_HOME` env vars, re-open terminal |
| Keystore error on release | Double-check all 4 env vars are set and the keystore path is absolute |
