import src.models
from src.users.router import router as users_router
from src.online.websocket import websocket_endpoint
from src.speaking.router import router as speaking_router
from src.solo_study.user_favorite_video_router import router as user_favorite_video_router
from src.solo_study.session_goal_router import router as session_goal_router
from src.solo_study.background_video_router import router as background_video_router
from src.solo_study.background_video_type_router import router as background_video_type_router
from src.solo_study.router import router as sound_router
from src.vocabulary.router import router as vocabulary_router
from src.reading.router import router as reading_router
from src.listening.router import router as listening_router
from src.writing.router import router as writing_router
from src.online.router import router as online_router
from src.dictionary.router import router as dictionary_router
from src.posts.router import router as posts_router
from src.auth.router import router as auth_router
from src.chatbot.router import router as chatbot_router
from src.config import settings
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging.config
from pathlib import Path

from src.utils.logging import attach_strip_ansi_to_file_handlers

# Load environment variables from .env file
load_dotenv()

# Configure logging from logging.ini file
logging_config_path = Path(__file__).parent.parent / "logging.ini"
if logging_config_path.exists():
    logging.config.fileConfig(
        logging_config_path, disable_existing_loggers=False
    )
    # Gắn filter xoá ANSI cho tất cả FileHandler (ví dụ app.log)
    attach_strip_ansi_to_file_handlers()
    print(f"[Startup] Logging configured from {logging_config_path}")
else:
    # Fallback to basic logging configuration (không thêm màu)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    print(
        f"[Startup] Logging config file not found at {logging_config_path}, using basic configuration"
    )


# Combine solo study routers
solo_study_router = APIRouter()
solo_study_router.include_router(sound_router)
solo_study_router.include_router(background_video_type_router)
solo_study_router.include_router(background_video_router)
solo_study_router.include_router(session_goal_router)
solo_study_router.include_router(user_favorite_video_router)

# Import all models to ensure they are registered with SQLAlchemy

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    swagger_ui_parameters={"docExpansion": "none"}
)

# Add CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin)
                       for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(writing_router, prefix=settings.API_V1_STR)
app.include_router(listening_router, prefix=settings.API_V1_STR)
app.include_router(speaking_router, prefix=settings.API_V1_STR)
app.include_router(reading_router, prefix=settings.API_V1_STR)
app.include_router(dictionary_router, prefix=settings.API_V1_STR)
app.include_router(vocabulary_router, prefix=settings.API_V1_STR)
app.include_router(solo_study_router, prefix=settings.API_V1_STR)
app.include_router(posts_router, prefix=settings.API_V1_STR)
app.include_router(online_router, prefix=settings.API_V1_STR)
app.include_router(chatbot_router, prefix=settings.API_V1_STR)

# WebSocket endpoint (documentation in websocket_endpoint docstring)
app.websocket("/online/ws")(websocket_endpoint)

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
    logger = logging.getLogger(__name__)
    logger.info("Application starting up...")

    # Optional: auto run alembic migrations on startup
    if settings.AUTO_MIGRATE_ON_STARTUP:
        try:
            import subprocess
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            logger.info("[Startup] Alembic migrations applied")
        except Exception as e:
            logger.error(f"[Startup] Alembic migration failed: {e}")

# Notify via WebSocket when an API call fails (4xx/5xx)


@app.middleware("http")
async def notify_on_api_error(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as e:
        try:
            # Import here to avoid circular import issues at module load time
            from src.online.dependencies import get_connection_manager  # type: ignore

            manager = get_connection_manager()
            await manager.broadcast(
                f"[500] {request.method} {request.url.path}: {str(e)}"
            )
        except Exception:
            pass
        raise

    try:
        if response.status_code >= 400:
            from src.online.dependencies import get_connection_manager  # type: ignore

            manager = get_connection_manager()
            await manager.broadcast(
                f"[{response.status_code}] {request.method} {request.url.path}"
            )
    except Exception:
        pass

    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
