from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import close_hume_http_client, get_gemini_client, get_hume_http_client, get_settings
from utils.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level)

    app = FastAPI(
        title="Empathic AI Therapy Backend",
        version="0.1.0",
        description="FastAPI backend for Hume EVI voice orchestration and Neo4j knowledge graph updates.",
    )
    app.state.settings = settings
    app.state.ws_max_size_bytes = settings.ws_max_size_bytes

    configure_cors(app)
    include_http_routers(app)
    include_ws_routers(app)
    register_lifecycle_handlers(app)

    return app


def configure_cors(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def include_http_routers(app: FastAPI) -> None:
    from api.routes.auth_hume import router as auth_hume_router
    from api.routes.audio_window import router as audio_window_router
    from api.routes.graph import router as graph_router
    from api.routes.health import router as health_router
    from api.routes.sessions import router as sessions_router

    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(auth_hume_router)
    app.include_router(audio_window_router)
    app.include_router(graph_router)


def include_ws_routers(app: FastAPI) -> None:
    from ws.session_ws import router as session_ws_router

    app.include_router(session_ws_router)


def register_lifecycle_handlers(app: FastAPI) -> None:
    async def on_startup() -> None:
        settings = get_settings()
        app.state.settings = settings
        get_hume_http_client()
        get_gemini_client()

        from services.neo4j.driver import create_driver
        from services.neo4j.migrate import run_migrations

        create_driver(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
        )
        migration_result = run_migrations()
        if migration_result["errors"]:
            raise RuntimeError(
                f"Neo4j migrations failed for database {migration_result['database']}: "
                + "; ".join(str(error) for error in migration_result["errors"])
            )

    async def on_shutdown() -> None:
        from services.neo4j.driver import close_driver

        await close_hume_http_client()
        close_driver()

    app.add_event_handler("startup", on_startup)
    app.add_event_handler("shutdown", on_shutdown)
