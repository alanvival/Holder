from datetime import datetime

from sqlalchemy import Boolean, DateTime, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, agora_utc


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_completo: Mapped[str] = mapped_column(Unicode(150))
    usuario: Mapped[str] = mapped_column(Unicode(50), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(Unicode(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    ultimo_login_em: Mapped[datetime | None] = mapped_column(DateTime)
