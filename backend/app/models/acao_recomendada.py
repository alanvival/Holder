from sqlalchemy import String, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import Dimensao, Responsavel
from app.models._tipos import coluna_enum


class AcaoRecomendada(Base):
    """Playbook: o que fazer para cada padrão de risco."""

    __tablename__ = "acoes_recomendadas"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    titulo: Mapped[str] = mapped_column(Unicode(150))
    descricao: Mapped[str] = mapped_column(UnicodeText)
    dimensao_gatilho: Mapped[Dimensao | None] = mapped_column(coluna_enum(Dimensao))
    responsavel_sugerido: Mapped[Responsavel] = mapped_column(coluna_enum(Responsavel))
    prazo_dias: Mapped[int]
    ordem: Mapped[int]
