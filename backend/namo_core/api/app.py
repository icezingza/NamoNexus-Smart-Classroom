import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from namo_core.api.routes.classroom import router as classroom_router
from namo_core.api.routes.devices import router as devices_router
from namo_core.api.routes.emotion import router as emotion_router
from namo_core.api.routes.health import router as health_router
from namo_core.api.routes.knowledge import router as knowledge_router
from namo_core.api.routes.lessons import router as lessons_router
from namo_core.api.routes.nexus import router as nexus_router
from namo_core.api.routes.reasoning import router as reasoning_router
from namo_core.api.routes.semantic_cache import router as semantic_cache_router
from namo_core.api.routes.speech import router as speech_router
from namo_core.api.routes.status import router as status_router
from namo_core.api.routes.tts import router as tts_router
from namo_core.api.routes.ws import router as ws_router
from namo_core.api.routes.feedback import router as feedback_router
from namo_core.api.routes.auth_routes import router as auth_routes_router
from namo_core.api.routes.notebook import router as notebook_router
from namo_core.api.routes.skills import router as skills_router
from namo_core.config.settings import get_settings, initialize_settings_secrets
from namo_core.services.knowledge.cache_initialization import initialize_semantic_cache
from namo_core.database.core import SessionLocal, engine, Base
__import__("namo_core.database.models")  # registers ORM classes with Base as side-effect

_logger = logging.getLogger(__name__)


async def load_secrets(settings) -> None:
    """Load GCP secrets then validate no placeholders remain."""
    try:
        await initialize_settings_secrets()
    except ImportError:
        _logger.warning("GCP Secret Manager libraries not found. Using local environment variables.")
    except Exception as exc:
        _logger.error("Failed to load secrets from GCP: %s", exc)

    _PLACEHOLDER = "MUST_BE_SET_IN_ENV"
    missing = [
        name
        for name, val in [
            ("NAMO_JWT_SECRET_KEY", settings.jwt_secret_key),
            ("NAMO_ADMIN_PASSWORD", settings.admin_password),
        ]
        if val == _PLACEHOLDER
    ]
    if missing and settings.env == "production":
        raise RuntimeError(
            f"Server refused to start: placeholder values detected for "
            f"{', '.join(missing)}. Set these in .env or GCP Secret Manager."
        )
    if missing:
        _logger.warning(
            "[Security] Placeholder secrets detected (%s). This WILL be a hard failure in production.",
            ", ".join(missing),
        )


def init_db(settings) -> None:
    """Auto-create SQLite tables for local dev; skip for PostgreSQL (Alembic manages schema)."""
    if not (settings.database_url or "").startswith("postgresql"):
        try:
            Base.metadata.create_all(bind=engine)
            _logger.info("[DB] SQLite tables created/verified OK")
        except Exception as exc:
            _logger.error("[DB] Failed to create tables: %s", exc)
    else:
        _logger.info("[DB] PostgreSQL detected — skipping create_all (Alembic manages schema)")


def init_cache() -> None:
    """Initialize in-memory semantic cache from the database."""
    try:
        db = SessionLocal()
        try:
            initialize_semantic_cache(db)
        finally:
            db.close()
    except Exception as exc:
        _logger.warning("Failed to initialize semantic cache: %s", exc)


async def ensure_assets() -> None:
    """Download FAISS assets from GCS if missing (no-op in local dev)."""
    try:
        from namo_core.utils.gcs_assets import ensure_assets_for_startup
        await ensure_assets_for_startup()
    except Exception as exc:
        _logger.warning("[GCS] Asset check failed (non-fatal): %s", exc)


async def prewarm_retrievers() -> None:
    """Pre-warm both RAG singletons and clean up stale notebook jobs."""
    try:
        from namo_core.services.knowledge.global_library_retriever import get_global_library_retriever
        from namo_core.services.knowledge.tripitaka_retriever import get_tripitaka_retriever
        from namo_core.services.lessons.notebook_service import NotebookService

        db = SessionLocal()
        try:
            cleaned = NotebookService(db).cleanup_stale_jobs(hours=1)
            if cleaned > 0:
                _logger.info("[Recovery] Cleaned up %d stale notebook jobs", cleaned)
        finally:
            db.close()

        t0 = asyncio.get_event_loop().time()
        tri, gl = await asyncio.gather(
            asyncio.to_thread(get_tripitaka_retriever),
            asyncio.to_thread(get_global_library_retriever),
        )
        elapsed_ms = int((asyncio.get_event_loop().time() - t0) * 1000)
        _logger.info(
            "[PreWarm] Tripitaka=%d vectors, GlobalLib=%d book indexes, elapsed=%dms",
            tri.index.ntotal if tri and hasattr(tri, "index") else 0,
            len(gl.books) if gl else 0,
            elapsed_ms,
        )
    except Exception as exc:
        _logger.warning("[PreWarm/Recovery] Failed: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    await load_secrets(settings)
    init_db(settings)
    init_cache()
    await ensure_assets()
    await prewarm_retrievers()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Namo Core API",
        version="0.1.0-recovered",
        description="Recovered starter backend for the Namo Core classroom assistant.",
        lifespan=lifespan,
    )

    from namo_core.api.auth import EnterpriseAuthMiddleware
    from namo_core.api.middleware import TraceIDMiddleware, setup_traced_logging, HSTSMiddleware

    setup_traced_logging()

    app.add_middleware(TraceIDMiddleware)
    app.add_middleware(EnterpriseAuthMiddleware)
    if settings.env == "production":
        app.add_middleware(HSTSMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origin_list or [],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    app.include_router(health_router)
    app.include_router(status_router)
    app.include_router(knowledge_router)
    app.include_router(lessons_router)
    app.include_router(devices_router)
    app.include_router(reasoning_router)
    app.include_router(emotion_router)
    app.include_router(classroom_router)
    app.include_router(tts_router)
    app.include_router(speech_router)
    app.include_router(nexus_router)
    app.include_router(ws_router)
    app.include_router(feedback_router)
    app.include_router(auth_routes_router)
    app.include_router(semantic_cache_router)
    app.include_router(notebook_router)
    app.include_router(skills_router)

    return app


app = create_app()
