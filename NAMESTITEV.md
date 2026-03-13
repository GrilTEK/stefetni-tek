# 🌿 Namestitev — Podnebni Štafetni Tek ŠCPET

## Predpogoji

- Hetzner strežnik z Dockerjem in Docker Compose
- Nginx Proxy Manager ki že teče
- Domena ali subdomena usmerjena na strežnik (npr. `tek.sola.si`)

---

## Korak 1 — Ugotovi ime NPM omrežja

Prijavi se na strežnik in zaženi:

```bash
docker network ls
```

Poišči omrežje kjer teče Nginx Proxy Manager. Primer izpisa:

```
NETWORK ID     NAME                          DRIVER
a1b2c3d4e5f6   npm_default                   bridge   ← to je NPM omrežje
f6e5d4c3b2a1   bridge                        bridge
```

Zapomni si ime (najpogosteje `npm_default`, `proxy`, ali `nginx-proxy-manager_default`).

---

## Korak 2 — Naloži projekt na strežnik

```bash
# Ustvari mapo za projekt
mkdir -p ~/projects/stefetni-tek
cd ~/projects/stefetni-tek

# Prenesi zip in razpakuj
unzip stefetni-tek.zip
```

---

## Korak 3 — Nastavi NPM omrežje v docker-compose.yml

Odpri `docker-compose.yml`:

```bash
nano docker-compose.yml
```

Na dnu datoteke poišči `networks` sekcijo in zamenjaj ime omrežja:

```yaml
networks:
  internal:
    driver: bridge
  proxy:
    external: true   # ← zamenjaj "proxy" z imenom iz Koraka 1
```

Če se tvoje omrežje imenuje npr. `npm_default`, spremeni v:

```yaml
networks:
  internal:
    driver: bridge
  npm_default:        # ← pravo ime
    external: true
```

In v `backend` service sekciji najdi:
```yaml
    networks:
      - internal
      - proxy         # ← zamenjaj tudi tukaj
```

---

## Korak 4 — Nastavi gesla (.env)

```bash
cp .env.example .env
nano .env
```

Nastavi naslednje vrednosti:

```env
POSTGRES_PASSWORD=izberi_mocno_geslo_za_bazo
SECRET_KEY=dolg_nakljucen_niz_vsaj_32_znakov
ADMIN_PASSWORD=geslo_za_admin_panel
```

Za `SECRET_KEY` lahko uporabiš:
```bash
openssl rand -hex 32
```

---

## Korak 5 — Zaženi aplikacijo

```bash
docker compose up -d --build
```

Počakaj ~30 sekund da se inicializira baza, nato preveri:

```bash
# Preveri status containerjev
docker compose ps

# Preveri loge backenda
docker logs stefetni_backend --tail 50

# Testiraj health endpoint
curl http://localhost:8000/health
```

Pričakovan odgovor:
```json
{"status": "ok", "service": "stefetni-tek"}
```

---

## Korak 6 — Nastavi NPM (Nginx Proxy Manager)

Odpri NPM GUI v brskalniku (`http://tvoj-ip:81`) in dodaj nov **Proxy Host**.

### Osnovna nastavitev:

| Polje | Vrednost |
|-------|----------|
| **Domain Names** | `tek.tvoja-domena.si` |
| **Scheme** | `http` |
| **Forward Hostname / IP** | `stefetni_backend` |
| **Forward Port** | `8000` |
| **Cache Assets** | izklopljeno |
| **Block Common Exploits** | vklopljeno |
| **Websockets Support** | ✅ **OBVEZNO VKLOPITI** |

### SSL (priporočeno):

V zavihku **SSL** izberi:
- SSL Certificate: **Request a new SSL Certificate**
- Force SSL: ✅ vklopljeno
- HTTP/2 Support: ✅ vklopljeno
- Email: tvoj email za Let's Encrypt

Klikni **Save**.

> ⚠️ **Websockets Support je kritičen** — brez tega live tracker, admin panel in sledenje fotografov ne bodo delovali.

---

## Korak 7 — Preveri delovanje

```bash
curl https://tek.tvoja-domena.si/health
```

Nato odpri v brskalniku:

| URL | Namen |
|-----|-------|
| `https://tek.tvoja-domena.si/` | Javni live tracker (za TV/projektor) |
| `https://tek.tvoja-domena.si/admin.html` | Admin panel |
| `https://tek.tvoja-domena.si/participant.html` | Mobilni view za udeležence |
| `https://tek.tvoja-domena.si/photographer.html` | View za fotografe |

---

## Gesla in dostopi

| Vloga | Kje | Geslo |
|-------|-----|-------|
| **Admin** | `/admin.html` | Vrednost `ADMIN_PASSWORD` iz `.env` |
| **Fotograf** | `/photographer.html` | `foto2024` (spremenljivo v kodi) |
| **Udeleženec** | `/participant.html` | Koda skupine (npr. `GRP001`) — generira admin |

---

## Pred tekom — checklist za admina

1. Prijavi se v `/admin.html`
2. Dodaj vse skupine (gumb **+ Dodaj skupino**)
3. Vsaka skupina dobi svojo **kodo** (npr. `AB3X9K`) — to daj vodji skupine
4. Ko skupina starta, pritisni **▶** gumb v admin panelu
5. Javni tracker na `https://tek.tvoja-domena.si/` odpri na velikem zaslonu

---

## Upravljanje po instalaciji

```bash
# Ustavi aplikacijo
docker compose down

# Ponovni zagon
docker compose up -d

# Rebuild po spremembi kode
docker compose up -d --build

# Poglej loge v živo
docker logs stefetni_backend -f

# Backup baze
docker exec stefetni_postgres pg_dump -U stefan stefetnitek > backup_$(date +%Y%m%d).sql
```

---

## Pogosta težava — omrežje ne najde NPM

Napaka: `network proxy declared as external, but could not be found`

Rešitev: zamenjaj ime omrežja v `docker-compose.yml` (Korak 3) ali ustvari omrežje ročno:

```bash
docker network create proxy
```

Nato povezi NPM container na to omrežje:
```bash
docker network connect proxy <ime_npm_containerja>
```
