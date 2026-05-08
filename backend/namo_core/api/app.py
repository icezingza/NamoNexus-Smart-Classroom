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
import namo_core.database.models  # noqa: F401  # type: ignore[import] — registers ORM classes as side-effect


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Namo Core API",
        version="0.1.0-recovered",
        description="Recovered starter backend for the Namo Core classroom assistant.",
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
        # Restrict to methods/headers actually used — wildcard exposes unnecessary attack surface
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

    # Startup event: Create SQLite tables + Initialize semantic cache
    @app.on_event("startup")
    async def startup_db_and_cache():
        import logging

        _logger = logging.getLogger(__name__)

        # ── Secret guard: refuse to start with placeholder values ──────────
        # Load GCP secrets first so validation uses the real values.
        try:
            await initialize_settings_secrets()
        except ImportError:
            _logger.warning("GCP Secret Manager libraries not found. Using local environment variables.")
        except Exception as exc:
            _logger.error("Failed to load secrets from GCP: %s", exc)

        _PLACEHOLDER = "MUST_BE_SET_IN_ENV"
        _secret_errors: list[str] = []
        if settings.system_secret == _PLACEHOLDER:
            _secret_errors.append("NAMO_SYSTEM_SECRET")
        if settings.admin_password == _PLACEHOLDER:
            _secret_errors.append("NAMO_ADMIN_PASSWORD")
        if settings.jwt_secret_key == _PLACEHOLDER:
            _secret_errors.append("NAMO_JWT_SECRET_KEY")

        if _secret_errors and settings.env == "production":
            # Hard-fail in production — placeholder secrets are catastrophic.
            raise RuntimeError(
                f"Server refused to start: placeholder values detected for "
                f"{', '.join(_secret_errors)}. Set these in .env or GCP Secret Manager."
            )
        elif _secret_errors:
            _logger.warning(
                "[Security] Placeholder secrets detected (%s). "
                "This WILL be a hard failure in production.",
                ", ".join(_secret_errors),
            )

        # SQLite only: auto-create tables for local dev.
        # PostgreSQL uses Alembic migrations (alembic upgrade head) — never create_all in prod.
        _db_url: str = settings.database_url or ""
        if not _db_url.startswith("postgresql"):
            try:
                Base.metadata.create_all(bind=engine)
                _logger.info("[DB] SQLite tables created/verified OK")
            except Exception as exc:
                _logger.error("[DB] Failed to create tables: %s", exc)
        else:
            _logger.info("[DB] PostgreSQL detected — skipping create_all (Alembic manages schema)")

        try:
            db = SessionLocal()
            initialize_semantic_cache(db)
            db.close()
        except Exception as exc:
            _logger.warning("Failed to initialize semantic cache: %s", exc)

        # Cloud Verification: ensure FAISS assets exist (downloads from GCS in prod if missing)
        try:
            from namo_core.utils.gcs_assets import ensure_assets_for_startup
            await ensure_assets_for_startup()
        except Exception as exc:
            _logger.warning("[GCS] Asset check failed (non-fatal): %s", exc)

        # Phase 11V: Pre-warm both RAG retrievers so first teacher query is instant.
        try:
            import asyncio as _asyncio
            from namo_core.services.knowledge.global_library_retriever import get_global_library_retriever
            from namo_core.services.knowledge.tripitaka_retriever import get_tripitaka_retriever
            from namo_core.services.lessons.notebook_service import NotebookService

            # 1. Recovery Mechanism: Cleanup stale jobs
            db = SessionLocal()
            try:
                cleaned = NotebookService(db).cleanup_stale_jobs(hours=1)
                if cleaned > 0:
                    _logger.info("[Recovery] Cleaned up %d stale notebook jobs", cleaned)
            finally:
                db.close()

            # 2. Pre-warm both RAG singletons concurrently
            t0 = _asyncio.get_event_loop().time()
            tri, gl = await _asyncio.gather(
                _asyncio.to_thread(get_tripitaka_retriever),
                _asyncio.to_thread(get_global_library_retriever),
            )
            elapsed_ms = int((_asyncio.get_event_loop().time() - t0) * 1000)
            _logger.info(
                "[PreWarm] Tripitaka=%d vectors, GlobalLib=%d book indexes, elapsed=%dms",
                tri.index.ntotal if tri and hasattr(tri, "index") else 0,
                len(gl.books) if gl else 0,
                elapsed_ms,
            )
        except Exception as exc:
            _logger.warning("[PreWarm/Recovery] Failed: %s", exc)

    return app


app = create_app()
