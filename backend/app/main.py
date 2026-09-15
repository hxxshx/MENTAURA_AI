"""
FastAPI Main Application for Mentaura Platform.
"""
import sys
from pathlib import Path

# Ensure chatbot directory is on sys.path
BASE_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
CHATBOT_DIR = BASE_PROJECT_DIR / "chatbot"
if CHATBOT_DIR.exists() and str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

try:
    from api.ws import router as ws_router
except Exception as _ws_err:
    ws_router = None

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.models import user, pulse, support_request, review, notification, intimidation, counsellor_message  # Ensure all models are loaded
from backend.app.routers.auth import router as auth_router
from backend.app.routers.victim import router as victim_router
from backend.app.routers.counsellor import router as counsellor_router
from backend.app.routers.command import router as command_router
from backend.app.routers.admin import router as admin_router
from backend.app.routers.notifications import router as notifications_router

from sqlalchemy import text

# Create database tables automatically
Base.metadata.create_all(bind=engine)

def run_migrations():
    """Ensures newly added columns and tables are present in database without manual migration scripts."""
    # Ensure all tables (including email_otps and intimidation_reports) are created
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        # Migrations for support_pulses
        try:
            conn.execute(text("ALTER TABLE support_pulses ADD COLUMN risk_level VARCHAR(20) DEFAULT 'low'"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE support_pulses ADD COLUMN risk_score INTEGER DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE support_pulses ADD COLUMN dynamic_distress_score INTEGER DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE support_pulses ADD COLUMN acoustic_score INTEGER DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE support_pulses ADD COLUMN sentiment_score INTEGER DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE support_pulses ADD COLUMN escalation_predicted BOOLEAN DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE support_pulses ADD COLUMN xai_explanation TEXT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE support_pulses ADD COLUMN interaction_channel VARCHAR(40) DEFAULT 'web_form'"))
        except Exception:
            pass

        # Migrations for users (role, official_id, is_anonymous, anonymous_id)
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50)"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN official_id VARCHAR(100)"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_anonymous BOOLEAN DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN anonymous_id VARCHAR(50)"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE email_otps ADD COLUMN delivery_email_hash VARCHAR(64)"))
        except Exception:
            pass
        try:
            conn.execute(text("UPDATE users SET role = verified_role WHERE role IS NULL AND verified_role IS NOT NULL"))
        except Exception:
            pass
        conn.commit()

run_migrations()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Secure, Case-Aware Support Intelligence Platform Authentication & Core APIs"
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(victim_router)
app.include_router(counsellor_router)
app.include_router(command_router)
app.include_router(admin_router)
app.include_router(notifications_router)
if ws_router:
    app.include_router(ws_router, tags=["Chatbot WebSocket"])

# Base project directory for serving static frontend files
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Mount CSS, JS, Assets directories if they exist
css_dir = BASE_DIR / "css"
js_dir = BASE_DIR / "js"
assets_dir = BASE_DIR / "assets"

if css_dir.exists():
    app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
if js_dir.exists():
    app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# Serve root html files cleanly with no-cache headers to ensure immediate updates
NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
}

@app.get("/")
def serve_index():
    return FileResponse(str(BASE_DIR / "index.html"), headers=NO_CACHE_HEADERS)

@app.get("/{filename}.html")
def serve_html_page(filename: str):
    file_path = BASE_DIR / f"{filename}.html"
    if file_path.exists():
        return FileResponse(str(file_path), headers=NO_CACHE_HEADERS)
    hyphen_path = BASE_DIR / f"{filename.replace(' ', '-')}.html"
    if hyphen_path.exists():
        return FileResponse(str(hyphen_path), headers=NO_CACHE_HEADERS)
    space_path = BASE_DIR / f"{filename.replace('-', ' ')}.html"
    if space_path.exists():
        return FileResponse(str(space_path), headers=NO_CACHE_HEADERS)
    return FileResponse(str(BASE_DIR / "index.html"), headers=NO_CACHE_HEADERS)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "consent_version": settings.CURRENT_CONSENT_VERSION
    }
