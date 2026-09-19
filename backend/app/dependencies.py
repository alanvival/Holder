from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.health_repository import HealthRepository
from app.services.health_service import HealthService


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_health_service(db: Session = Depends(get_db)) -> HealthService:
    return HealthService(HealthRepository(db))
