"""Voice-Clone Shield API — v1."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import auth, checks, voiceprints

app = FastAPI(
    title="Voice-Clone Shield",
    description="AI voice-clone protection for independent musicians. v1: manual-upload matching.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(voiceprints.router)
app.include_router(checks.router)


@app.on_event("startup")
def on_startup() -> None:
    if not settings.JWT_SECRET or settings.JWT_SECRET.startswith("change-me"):
        raise RuntimeError(
            "JWT_SECRET is not configured. Copy backend/.env.example to backend/.env "
            "and set a random value (openssl rand -hex 32)."
        )
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


# ---- Production: serve the built SPA from this same service ----
# Single-service Railway deploy. Skipped when frontend-dist is absent (local dev).
import os as _os

_DIST = _os.environ.get("FRONTEND_DIST", "/app/frontend-dist")
if _os.path.isdir(_DIST):
    from fastapi.staticfiles import StaticFiles as _StaticFiles

    app.mount("/", _StaticFiles(directory=_DIST, html=True), name="spa")
