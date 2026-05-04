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
from namo_core.config.settings import get_settings, initialize_settings_secrets
from namo_core.services.knowledge.cache_initialization import initialize_semantic_cache
from namo_core.database.core import SessionLocal, engine, Base
import namo_core.database.models  # noqa: F401 — ensure all models are registered before create_all


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Namo Core API",
        version="0.1.0-recovered",
        description="Recovered starter backend for the Namo Core classroom assistant.",
    )

    from namo_core.api.auth import EnterpriseAuthMiddleware

    app.add_middleware(EnterpriseAuthMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origin_list or [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    # Startup event: Create SQLite tables + Initialize semantic cache
    @app.on_event("startup")
    async def startup_db_and_cache():
        import logging

        _logger = logging.getLogger(__name__)
        # Phase 12: auto-create all tables (idempotent — safe to run on every start)
        try:
            Base.metadata.create_all(bind=engine)
            _logger.info("[DB] SQLite tables created/verified OK")
        except Exception as exc:
            _logger.error("[DB] Failed to create tables: %s", exc)

        try:
            db = SessionLocal()
            initialize_semantic_cache(db)
            db.close()
        except Exception as exc:
            _logger.warning("Failed to initialize semantic cache: %s", exc)

        # Phase 1: Load secrets before handling requests.
        try:
            await initialize_settings_secrets()
        except ImportError:
            _logger.warning("GCP Secret Manager libraries not found. Using local environment variables.")
        except Exception as exc:
            _logger.error("Failed to load secrets from GCP: %s", exc)

        # Phase 11V: Pre-warm both RAG retrievers so first teacher query is instant.
        try:
            import asyncio as _asyncio
            from namo_core.services.knowledge.global_library_retriever import get_global_library_retriever
            from namo_core.services.knowledge.tripitaka_retriever import get_tripitaka_retriever
            tri, gl = await _asyncio.gather(
                _asyncio.to_thread(get_tripitaka_retriever),
                _asyncio.to_thread(get_global_library_retriever),
            )
            _logger.info("[PreWarm] Tripitaka ready, GlobalLib: %d book indexes", len(gl.books))
        except Exception as exc:
            _logger.warning("[PreWarm] Failed (will load on first request): %s", exc)

    return app

app = create_app()
