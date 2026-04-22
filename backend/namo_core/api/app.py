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
from namo_core.config.settings import get_settings
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
    def startup_db_and_cache():
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

    return app


app = create_app()
rn app


app = create_app()
