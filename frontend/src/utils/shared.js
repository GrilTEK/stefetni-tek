(function() {
const API_BASE = window.location.origin + "/api";
const WS_BASE = window.location.origin.replace(/^http/, "ws");

const token = {
  get: () => localStorage.getItem("st_token"),
  set: (t) => localStorage.setItem("st_token", t),
  remove: () => { localStorage.removeItem("st_token"); apiFetch("/auth/logout", { method: "POST" }).catch(() => {}); },
  payload: () => {
    const t = localStorage.getItem("st_token");
    if (!t) return null;
    try {
      const p = JSON.parse(atob(t.split(".")[1]));
      if (p.exp && p.exp * 1000 < Date.now()) { localStorage.removeItem("st_token"); return null; }
      return p;
    } catch { return null; }
  },
};

async function apiFetch(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  const tok = localStorage.getItem("st_token");
  if (tok) headers["Authorization"] = `Bearer ${tok}`;
  const res = await fetch(API_BASE + path, { ...options, headers, credentials: 'include' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }
  return res.json();
}

class OfflineQueue {
  constructor(key = "st_offline_queue") { this.key = key; }
  load() { try { return JSON.parse(localStorage.getItem(this.key) || "[]"); } catch { return []; } }
  save(q) { localStorage.setItem(this.key, JSON.stringify(q)); }
  push(item) { const q = this.load(); q.push(item); this.save(q); }
  clear() { localStorage.removeItem(this.key); }
  size() { return this.load().length; }
  async flush() {
    const q = this.load();
    if (!q.length || !navigator.onLine || !localStorage.getItem("st_token")) return 0;
    try {
      await apiFetch("/location/sync-offline", { method: "POST", body: JSON.stringify({ updates: q }) });
      this.clear(); return q.length;
    } catch { return 0; }
  }
}

class GPSTracker {
  constructor(onLocation, onError) { this.onLocation = onLocation; this.onError = onError; this.watchId = null; }
  start() {
    if (!window.isSecureContext) {
      this.onError?.("GPS zahteva HTTPS – odpri stran prek https://");
      return;
    }
    if (!navigator.geolocation) {
      this.onError?.("GPS ni na voljo v tem brskalniku");
      return;
    }
    this.watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude: lat, longitude: lng, accuracy, altitude } = pos.coords;
        this.onLocation({ lat, lng, accuracy, altitude, timestamp: new Date().toISOString(), source: "gps" });
      },
      (err) => {
        const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
        const msg = err.code === 1
          ? (isIOS ? "Dostop zavrnjen – pojdi na Nastavitve > Zasebnost > Lokacijske storitve > Safari > Dovoli"
                   : "Dostop do GPS zavrnjen – preveri dovoljenja brskalnika")
          : err.code === 2
          ? (isIOS ? "Lokacija ni dosegljiva – omogoči Lokacijske storitve v iOS Nastavitvah"
                   : "GPS signal ni dosegljiv")
          : err.code === 3
          ? "GPS se ni odzval – premakni se na prosto"
          : (err.message || "Neznana GPS napaka");
        this.onError?.(msg);
      },
      { enableHighAccuracy: true, timeout: Infinity, maximumAge: 5000 }
    );
  }
  stop() { if (this.watchId !== null) { navigator.geolocation.clearWatch(this.watchId); this.watchId = null; } }
  get active() { return this.watchId !== null; }
}

class BLEScanner {
  constructor(onBeacon) { this.onBeacon = onBeacon; }
  isSupported() { return "bluetooth" in navigator; }
  async startScan() {
    try {
      const device = await navigator.bluetooth.requestDevice({ acceptAllDevices: true });
      this.onBeacon?.({ id: device.id, name: device.name, source: "bluetooth" });
      return true;
    } catch { return false; }
  }
}

class ReconnectingWS {
  constructor(url, onMessage, onOpen, onClose) {
    this.url = url; this.onMessage = onMessage; this.onOpen = onOpen; this.onClose = onClose;
    this.ws = null; this.retryDelay = 2000; this.pingInterval = null;
    this.connect();
  }
  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => {
      this.retryDelay = 2000; this.onOpen?.();
      this.pingInterval = setInterval(() => {
        if (this.ws.readyState === WebSocket.OPEN) this.ws.send("ping");
      }, 25000);
    };
    this.ws.onmessage = (e) => {
      if (e.data === "pong") return;
      try { this.onMessage?.(JSON.parse(e.data)); } catch {}
    };
    this.ws.onclose = () => {
      clearInterval(this.pingInterval);
      this.onClose?.();
      setTimeout(() => this.connect(), this.retryDelay);
      this.retryDelay = Math.min(this.retryDelay * 1.5, 30000);
    };
  }
  send(data) { if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(data)); }
  close() { clearInterval(this.pingInterval); this.ws?.close(); }
  get connected() { return this.ws?.readyState === WebSocket.OPEN; }
}

function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLng/2)**2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

async function requestNotifications() {
  if ("Notification" in window && Notification.permission === "default") await Notification.requestPermission();
}

function notify(title, body, tag = "alert") {
  if (Notification.permission === "granted") new Notification(title, { body, tag, icon: "/icon.png" });
}

function formatElapsed(isoStart) {
  if (!isoStart) return "–";
  const diff = (Date.now() - new Date(isoStart)) / 1000;
  const h = Math.floor(diff / 3600), m = Math.floor((diff % 3600) / 60), s = Math.floor(diff % 60);
  return h > 0 ? `${h}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}` : `${m}:${String(s).padStart(2,"0")}`;
}

window.ST = { token, apiFetch, offlineQueue: new OfflineQueue(), GPSTracker, BLEScanner, ReconnectingWS, haversine, notify, requestNotifications, formatElapsed, API_BASE, WS_BASE };
})();
