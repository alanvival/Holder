from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, agora_utc
from app.core.enums import Dimensao, SentidoPiora, TipoRegra
from app.models._tipos import coluna_enum


class ConfiguracaoSinal(Base):
    """Catálogo de sinais de risco com limiar e peso."""

    __tablename__ = "configuracoes_sinal"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    dimensao: Mapped[Dimensao] = mapped_column(coluna_enum(Dimensao))
    variavel: Mapped[str] = mapped_column(String(50))
    tipo_regra: Mapped[TipoRegra] = mapped_column(coluna_enum(TipoRegra))
    sentido_piora: Mapped[SentidoPiora] = mapped_column(coluna_enum(SentidoPiora))
    limiar: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    metrica: Mapped[str] = mapped_column(String(20), default="media_3m")
    persistencia_min_meses: Mapped[int] = mapped_column(default=2)
    peso: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    lift: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    cobertura_cancelados: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    taxa_falso_alarme: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    antecedencia_media_meses: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    template_evidencia: Mapped[str] = mapped_column(Unicode(300))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, onupdate=agora_utc)
