from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def criar_engine(url: str) -> Engine:
    """Cria a engine conforme o banco: SQLite (MVP/testes) ou SQL Server (futuro)."""
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    if url.startswith("mssql"):
        return create_engine(url, fast_executemany=True)
    return create_engine(url)


def agora_utc() -> datetime:
    """Data/hora atual em UTC, sem tzinfo (DATETIME2 / SQLite)."""
    return datetime.now(UTC).replace(tzinfo=None)
