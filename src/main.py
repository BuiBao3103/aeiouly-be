from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.auth.router import router as auth_router
from src.posts.router import router as posts_router

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

# Try to include writing agent router if available
try:
    from src.writing_agent.router import router as writing_router
    app.include_router(writing_router, prefix=settings.API_V1_STR)
    print("[Init] Writing agent router loaded successfully")
except Exception as e:
    # Avoid crashing app if optional deps missing
    print(f"[Init] Writing agent router not loaded: {e}")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 