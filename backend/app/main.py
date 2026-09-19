from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registra os models no metadata)
from app.controllers import auth_controller, health_controller
from app.core.config import Settings, get_settings
from app.core.database import Base, criar_engine
from app.core.handlers import registrar_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    """Fábrica da aplicação. Rode com: uvicorn app.main:create_app --factory"""
    settings = settings or get_settings()
    engine = criar_engine(settings.database_url)
    Base.metadata.create_all(engine)

    app = FastAPI(title="Holder — API de risco de churn", version="0.1.0")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.lista_cors,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_handlers(app)
    app.include_router(health_controller.router, prefix="/api")
    app.include_router(auth_controller.router, prefix="/api")
    return app
