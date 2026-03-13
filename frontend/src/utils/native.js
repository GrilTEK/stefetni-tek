(function () {
  "use strict";

  // Lazy plugin getter — avoids timing issues at eval time
  function plugin(name) {
    return window.Capacitor?.Plugins?.[name];
  }

  function isNative() {
    return !!window.Capacitor?.isNativePlatform?.();
  }

  function resolveApiBase() {
    return isNative() ? "https://tek.griltek.si" : null;
  }

  function resolveWsBase() {
    return isNative() ? "wss://tek.griltek.si" : null;
  }

  // ── GPS Tracker ──────────────────────────────────────────────────────────────
  function NativeGPSTracker(onLocation, onError) {
    var watchId = null;

    this.start = function () {
      var Geo = plugin("Geolocation");
      if (!Geo) { onError?.("Geolocation plugin ni na voljo"); return; }
      Geo.requestPermissions().then(function () {
        return Geo.watchPosition(
          { enableHighAccuracy: true, maximumAge: 5000 },
          function (pos, err) {
            if (err) { onError?.(err.message || "GPS napaka"); return; }
            if (!pos) return;
            var c = pos.coords;
            onLocation({
              lat: c.latitude,
              lng: c.longitude,
              accuracy: c.accuracy,
              altitude: c.altitude,
              timestamp: new Date().toISOString(),
              source: "gps",
            });
          }
        );
      }).then(function (id) {
        watchId = id;
      }).catch(function (e) {
        onError?.(e.message || "GPS napaka");
      });
    };

    this.stop = function () {
      var Geo = plugin("Geolocation");
      if (watchId !== null && Geo) {
        Geo.clearWatch({ id: watchId });
        watchId = null;
      }
    };

    Object.defineProperty(this, "active", {
      get: function () { return watchId !== null; },
    });
  }

  // ── BLE Scanner ──────────────────────────────────────────────────────────────
  function NativeBLEScanner(onBeacon) {
    var scanning = false;

    this.isSupported = function () {
      return isNative() && !!plugin("BluetoothLe");
    };

    this.startScan = function () {
      var BLE = plugin("BluetoothLe");
      if (!BLE) return Promise.resolve(false);
      return BLE.initialize()
        .then(function () { return BLE.requestPermissions(); })
        .then(function () {
          return BLE.requestLEScan({ allowDuplicates: true }, function (result) {
            if (!result) return;
            onBeacon({
              id: result.device?.deviceId || result.deviceId || "unknown",
              name: result.localName || result.device?.name || null,
              rssi: result.rssi ?? null,
              source: "ble-native",
            });
          });
        })
        .then(function () { scanning = true; return true; })
        .catch(function () { return false; });
    };

    this.stopScan = function () {
      var BLE = plugin("BluetoothLe");
      if (BLE && scanning) {
        BLE.stopLEScan().catch(function () {});
        scanning = false;
      }
    };

    Object.defineProperty(this, "active", {
      get: function () { return scanning; },
    });
  }

  // ── Notifications ────────────────────────────────────────────────────────────
  function nativeRequestNotifications() {
    var LN = plugin("LocalNotifications");
    if (!LN) return Promise.resolve();
    return LN.requestPermissions();
  }

  function nativeNotify(title, body) {
    var LN = plugin("LocalNotifications");
    if (!LN) return;
    LN.schedule({
      notifications: [
        {
          title: title,
          body: body,
          id: Math.floor(Math.random() * 100000),
          schedule: { at: new Date(Date.now() + 100) },
        },
      ],
    }).catch(function () {});
  }

  // ── Clipboard ────────────────────────────────────────────────────────────────
  function nativeClipboardWrite(text) {
    var CB = plugin("Clipboard");
    if (!CB) return Promise.resolve();
    return CB.write({ string: text });
  }

  // ── App lifecycle ────────────────────────────────────────────────────────────
  function registerAppListeners() {
    var AppPlugin = plugin("App");
    if (!AppPlugin) return;
    AppPlugin.addListener("backButton", function () {
      // Default: do nothing (let the webview handle history)
      // Override in page scripts if needed
    });
  }

  // ── Splash screen ────────────────────────────────────────────────────────────
  function hideSplash() {
    var SS = plugin("SplashScreen");
    if (SS) SS.hide().catch(function () {});
  }

  // ── Auto-init when native ────────────────────────────────────────────────────
  if (isNative()) {
    document.addEventListener("DOMContentLoaded", function () {
      hideSplash();
      registerAppListeners();
    });
  }

  // ── Public API ───────────────────────────────────────────────────────────────
  window.STNative = {
    isNative: isNative,
    resolveApiBase: resolveApiBase,
    resolveWsBase: resolveWsBase,
    NativeGPSTracker: NativeGPSTracker,
    NativeBLEScanner: NativeBLEScanner,
    nativeRequestNotifications: nativeRequestNotifications,
    nativeNotify: nativeNotify,
    nativeClipboardWrite: nativeClipboardWrite,
    registerAppListeners: registerAppListeners,
    hideSplash: hideSplash,
  };
})();
