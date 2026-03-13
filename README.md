# 🌿 Podnebni Štafetni Tek – ŠCPET

Spletna aplikacija za sledenje skupin na podnebnem štafetnem teku.

## Arhitektura

```
┌─────────────────────────────────────────────────┐
│                  Nginx (Port 80)                 │
│  /          → index.html  (javni live tracker)  │
│  /participant.html → udeleženec PWA             │
│  /photographer.html → fotograf view             │
│  /admin.html → admin panel                      │
│  /api/*     → FastAPI backend                   │
│  /ws/*      → WebSocket (live)                  │
└──────────────┬──────────────────────────────────┘
               │
       ┌───────▼────────┐
       │  FastAPI + WS  │  ← Python 3.12, asyncpg
       └───┬────────┬───┘
           │        │
    ┌──────▼──┐  ┌──▼──────┐
    │Postgres │  │  Redis  │
    │(persist)│  │(cache+  │
    │         │  │ pub/sub)│
    └─────────┘  └─────────┘
```

## Vloge in zasloni

| URL | Vloga | Opis |
|-----|-------|------|
| `/` | Javni | Live karta vseh skupin (TV/projektor) |
| `/participant.html` | Udeleženec | GPS sledenje, BLE, offline sync |
| `/photographer.html` | Fotograf | Karta + bližinska opozorila |
| `/admin.html` | Admin | Upravljanje skupin, statistike |

## Namestitev na Hetzner

```bash
# 1. Kloniraj projekt
git clone <your-repo> stefetni-tek
cd stefetni-tek

# 2. Nastavi environment
cp .env.example .env
nano .env  # Nastavi gesla!

# 3. Zaženi
docker compose up -d --build

# 4. Preveri delovanje
curl http://localhost/health
```

## WebSocket kanali

| Endpoint | Opis |
|----------|------|
| `/ws/live` | Javni gledalci (brez autentikacije) |
| `/ws/admin?token=...` | Admin panel |
| `/ws/photographer/{id}?token=...` | Fotograf (opozorila) |
| `/ws/group/{id}?token=...` | Skupina (status updates) |

## REST API

| Metoda | URL | Opis |
|--------|-----|------|
| POST | `/api/auth/join-group` | Udeleženec vstopi v skupino |
| POST | `/api/auth/login` | Admin / fotograf prijava |
| POST | `/api/location/update` | Pošlji lokacijo |
| POST | `/api/location/update-group/{id}` | Fotograf pin za skupino |
| POST | `/api/location/sync-offline` | Offline batch sync |
| GET | `/api/public/state` | Stanje vseh skupin (brez auth) |
| GET | `/api/public/event` | Event config (brez auth) |
| GET | `/api/admin/groups` | Seznam skupin (admin) |
| POST | `/api/admin/groups` | Dodaj skupino (admin) |
| PATCH | `/api/admin/groups/{id}` | Uredi skupino (admin) |
| POST | `/api/admin/groups/{id}/start` | Začni skupino (admin) |
| POST | `/api/admin/groups/{id}/finish` | Zaključi skupino (admin) |

## Gesla (nastavi v .env)

- **Admin**: `/admin.html` → geslo iz `ADMIN_PASSWORD`
- **Fotograf**: `/photographer.html` → geslo `foto2024` (spremenljivo v kodi)
- **Udeleženec**: `/participant.html` → koda skupine npr. `GRP001`

## Offline delovanje

Mobilna naprava udeležencev samodejno shranjuje lokacije lokalno, ko ni interneta. Ko se spet poveže, jih sinhroniziraj z gumbom "Sinhroniziraj" ali samodejno ob reconnectu.

## BLE Beaconi

Web Bluetooth API podpira samo Chrome/Edge na Android. iOS zahteva native app.
UUID beaconov se konfigurira v admin panelu pod "Event settings".
