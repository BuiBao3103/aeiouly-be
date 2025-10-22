from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from src.config import settings
from src.auth.router import router as auth_router
from src.posts.router import router as posts_router
from src.dictionary.router import router as dictionary_router
from src.notifications.router import router as notifications_router
from src.analytics.router import router as analytics_router
from src.writing.router import router as writing_router
from src.listening.router import router as listening_router
from fastapi import Request

# Import all models to ensure they are registered with SQLAlchemy
import src.models

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(posts_router, prefix=settings.API_V1_STR)
app.include_router(dictionary_router)
app.include_router(notifications_router)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(writing_router, prefix=settings.API_V1_STR)
app.include_router(listening_router, prefix=settings.API_V1_STR)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Chào mừng đến với Aeiouly!",
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "hoạt động bình thường"}

# Startup event
@app.on_event("startup")
async def startup_event():
    # Optional: auto run alembic migrations on startup
    if settings.AUTO_MIGRATE_ON_STARTUP:
        try:
            import subprocess
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            print("[Startup] Alembic migrations applied")
        except Exception as e:
            print(f"[Startup] Alembic migration failed: {e}")

# Notify via WebSocket when an API call fails (4xx/5xx)
@app.middleware("http")
async def notify_on_api_error(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as e:
        try:
            # Import here to avoid circular import issues at module load time
            from src.notifications.router import manager  # type: ignore
            await manager.broadcast_text(f"[500] {request.method} {request.url.path}: {str(e)}")
        except Exception:
            pass
        raise

    try:
        if response.status_code >= 400:
            from src.notifications.router import manager  # type: ignore
            await manager.broadcast_text(f"[{response.status_code}] {request.method} {request.url.path}")
    except Exception:
        pass

    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 