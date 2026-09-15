from backend.app.routers.auth import router as auth_router
from backend.app.routers.victim import router as victim_router
from backend.app.routers.counsellor import router as counsellor_router
from backend.app.routers.command import router as command_router
from backend.app.routers.admin import router as admin_router
from backend.app.routers.notifications import router as notifications_router

__all__ = [
    "auth_router",
    "victim_router",
    "counsellor_router",
    "command_router",
    "admin_router",
    "notifications_router",
]
