from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.deps import get_settings
    from utils.logging import configure_logging

    settings = get_settings()
    configure_logging(level=settings.log_level)

    import logging
    try:
        from services.neo4j.driver import create_driver
        create_driver(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
        )
        from services.neo4j.migrate import run_migrations
        run_migrations()
        logging.getLogger("startup").info("Neo4j connected and migrations applied.")
    except Exception as exc:
        logging.getLogger("startup").warning(
            "Neo4j unavailable at startup (will retry on first request): %s", exc
        )

    yield

    # Shutdown
    from services.neo4j.driver import close_driver
    close_driver()


def create_app() -> FastAPI:
    app = FastAPI(title="Empathic AI Therapy API", version="0.1.0", lifespan=lifespan)
    configure_cors(app)
    include_http_routers(app)
    include_ws_routers(app)
    return app


def configure_cors(app: FastAPI) -> None:
    from app.deps import get_settings
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def include_http_routers(app: FastAPI) -> None:
    from api.routes.health import router as health_router
    from api.routes.sessions import router as sessions_router
    from api.routes.auth_hume import router as hume_router
    from api.routes.graph import router as graph_router

    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(hume_router)
    app.include_router(graph_router)


def include_ws_routers(app: FastAPI) -> None:
    from ws.session_ws import router as ws_router
    app.include_router(ws_router)


def register_lifecycle_handlers(app: FastAPI) -> None:
    pass  # Now handled by lifespan context manager above


app = create_app()
