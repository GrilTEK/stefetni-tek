from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis, close_redis
from app.api import auth, location, admin
from app.websocket import routes as ws_routes
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await init_db()
    logger.info("Ready.")
    yield
    await close_redis()

app = FastAPI(title="Štafetni Tek API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket
app.include_router(ws_routes.router)

# API
app.include_router(auth.router, prefix="/api")
app.include_router(location.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "stefetni-tek"}

@app.get("/api/public/state")
async def public_state():
    from app.core.database import AsyncSessionLocal
    from app.core.redis import redis_client
    from app.services.location_service import LocationService
    async with AsyncSessionLocal() as db:
        service = LocationService(db, redis_client)
        return await service.get_full_state()

@app.get("/api/public/event")
async def public_event():
    from app.core.database import AsyncSessionLocal
    from app.models.event import Event
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Event).order_by(Event.id.desc()).limit(1))
        event = result.scalar_one_or_none()
        if not event:
            return {"map_center_lat": 46.0569, "map_center_lng": 14.5058, "map_zoom": 13, "route_waypoints": []}
        return {
            "name": event.name,
            "map_center_lat": event.map_center_lat,
            "map_center_lng": event.map_center_lng,
            "map_zoom": event.map_zoom,
            "route_waypoints": event.route_waypoints or [],
            "ble_beacons": event.ble_beacons or [],
        }

# Eksplicitne poti za HTML strani
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}

@app.get("/")
async def index():
    return FileResponse(os.path.join(frontend_path, "index.html"), headers=_NO_CACHE)

@app.get("/admin.html")
async def admin_page():
    return FileResponse(os.path.join(frontend_path, "admin.html"), headers=_NO_CACHE)

@app.get("/participant.html")
async def participant_page():
    return FileResponse(os.path.join(frontend_path, "participant.html"), headers=_NO_CACHE)

@app.get("/photographer.html")
async def photographer_page():
    return FileResponse(os.path.join(frontend_path, "photographer.html"), headers=_NO_CACHE)

@app.get("/route.html")
async def route_page():
    return FileResponse(os.path.join(frontend_path, "route.html"), headers=_NO_CACHE)

@app.get("/photographers.html")
async def photographers_page():
    return FileResponse(os.path.join(frontend_path, "photographers.html"), headers=_NO_CACHE)

# Static assets (CSS, JS, slike) — samo za /src/ in /lib/
if os.path.exists(frontend_path):
    app.mount("/src", StaticFiles(directory=os.path.join(frontend_path, "src")), name="src")
    app.mount("/lib", StaticFiles(directory=os.path.join(frontend_path, "lib")), name="lib")
    logger.info(f"Frontend: {frontend_path}")

@app.get("/manifest.json")
async def manifest():
    return FileResponse(os.path.join(frontend_path, "manifest.json"))

@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)
