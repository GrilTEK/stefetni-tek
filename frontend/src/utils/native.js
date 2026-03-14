// frontend/src/utils/native.js
// Capacitor native shim – safe no-op when loaded in any browser.
// Load this BEFORE shared.js and leaflet on pages that need native APIs.
// Exports: window.STNative
(function () {
  'use strict';

  // ── Detection ──────────────────────────────────────────────────────────────
  const isNative = () => !!(window.Capacitor && window.Capacitor.isNativePlatform());
  const getPlatform = () => window.Capacitor?.getPlatform() ?? 'web';

  // Lazy plugin getter – safe to call before DOMContentLoaded
  const plugin = (name) => window.Capacitor?.Plugins?.[name];

  // ── API / WS base URLs ─────────────────────────────────────────────────────
  const PRODUCTION_URL = 'https://tek.griltek.si';

  function resolveApiBase() {
    return isNative() ? PRODUCTION_URL : null;
  }
  function resolveWsBase() {
    return isNative() ? PRODUCTION_URL.replace(/^https/, 'wss').replace(/^http/, 'ws') : null;
  }

  // ── GPS tracker ────────────────────────────────────────────────────────────
  function NativeGPSTracker(onLocation, onError) {
    this._onLocation = onLocation;
    this._onError    = onError;
    this._watchId    = null;
  }

  NativeGPSTracker.prototype.start = async function () {
    const Geo = plugin('Geolocation');
    if (!Geo) { this._onError?.('Geolocation plugin ni na voljo'); return; }
    try {
      const perm = await Geo.requestPermissions({ permissions: ['location'] });
      if (perm.location !== 'granted' && perm.coarseLocation !== 'granted') {
        this._onError?.('Dostop do GPS zavrnjen – preveri dovoljenja v nastavitvah');
        return;
      }
    } catch (_) {}
    try {
      this._watchId = await Geo.watchPosition(
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 },
        (pos, err) => {
          if (err) { this._onError?.(err.message || 'GPS napaka'); return; }
          const { latitude: lat, longitude: lng, accuracy, altitude } = pos.coords;
          this._onLocation({ lat, lng, accuracy, altitude,
            timestamp: new Date().toISOString(), source: 'gps' });
        }
      );
    } catch (e) {
      this._onError?.(e.message || 'GPS napaka');
    }
  };

  NativeGPSTracker.prototype.stop = async function () {
    const Geo = plugin('Geolocation');
    if (this._watchId !== null && Geo) {
      await Geo.clearWatch({ id: this._watchId }).catch(() => {});
      this._watchId = null;
    }
  };

  Object.defineProperty(NativeGPSTracker.prototype, 'active', {
    get: function () { return this._watchId !== null; }
  });

  // ── BLE scanner ────────────────────────────────────────────────────────────
  function NativeBLEScanner(onBeacon) {
    this._onBeacon = onBeacon;
    this._scanning = false;
  }

  NativeBLEScanner.prototype.isSupported = function () {
    return isNative() && !!plugin('BluetoothLe');
  };

  NativeBLEScanner.prototype.startScan = async function () {
    const BLE = plugin('BluetoothLe');
    if (!BLE) return false;
    try { await BLE.initialize(); } catch (e) { console.warn('[BLE] init:', e); return false; }
    try {
      const perm = await BLE.requestPermissions();
      if (perm.bluetooth !== 'granted') return false;
    } catch (_) {}
    this._scanning = true;
    try {
      await BLE.requestLEScan({ allowDuplicates: true }, (result) => {
        if (!this._scanning) return;
        const name = result.device?.name || result.localName || null;
        const rssi = result.rssi ?? null;
        const id   = result.device?.deviceId || '';
        this._onBeacon?.({ id, name: name || id.slice(-8), rssi,
          source: 'ble-native', rawName: name });
      });
      return true;
    } catch (e) {
      console.warn('[BLE] scan:', e);
      this._scanning = false;
      return false;
    }
  };

  NativeBLEScanner.prototype.stopScan = async function () {
    this._scanning = false;
    const BLE = plugin('BluetoothLe');
    if (BLE) await BLE.stopLEScan().catch(() => {});
  };

  // ── Notifications ──────────────────────────────────────────────────────────
  async function nativeRequestNotifications() {
    const LN = plugin('LocalNotifications');
    if (!LN) return;
    try { await LN.requestPermissions(); } catch (_) {}
  }

  let _notifId = 1;
  async function nativeNotify(title, body) {
    const LN = plugin('LocalNotifications');
    if (!LN) return;
    try {
      await LN.schedule({ notifications: [{ id: _notifId++, title, body, sound: null }] });
    } catch (e) { console.warn('[Notify]', e); }
  }

  // ── Clipboard ─────────────────────────────────────────────────────────────
  async function nativeClipboardWrite(text) {
    const CB = plugin('Clipboard');
    if (!CB) throw new Error('Clipboard plugin ni na voljo');
    await CB.write({ string: text });
  }

  // ── App lifecycle ──────────────────────────────────────────────────────────
  function registerAppListeners() {
    const App = plugin('App');
    if (!App) return;
    App.addListener('backButton', ({ canGoBack }) => {
      if (!canGoBack) App.exitApp();
    });
  }

  // ── Splash / status bar ────────────────────────────────────────────────────
  async function hideSplash() {
    const SP = plugin('SplashScreen');
    if (SP) await SP.hide().catch(() => {});
  }

  // ── Preferences (secure-ish key-value store, falls back to localStorage) ──
  const Preferences = {
    async get(key) {
      const P = plugin('Preferences');
      if (!P) return localStorage.getItem(key);
      const { value } = await P.get({ key });
      return value;
    },
    async set(key, value) {
      const P = plugin('Preferences');
      if (!P) { localStorage.setItem(key, value); return; }
      await P.set({ key, value: String(value) });
    },
    async remove(key) {
      const P = plugin('Preferences');
      if (!P) { localStorage.removeItem(key); return; }
      await P.remove({ key });
    },
  };

  // ── Public API ─────────────────────────────────────────────────────────────
  window.STNative = {
    isNative, getPlatform,
    resolveApiBase, resolveWsBase,
    NativeGPSTracker, NativeBLEScanner,
    nativeNotify, nativeRequestNotifications, nativeClipboardWrite,
    registerAppListeners, hideSplash,
    Preferences,
  };

  // Auto-init when native
  if (isNative()) {
    document.addEventListener('DOMContentLoaded', () => {
      hideSplash();
      registerAppListeners();
    });
  }
})();
