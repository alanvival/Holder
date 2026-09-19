from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Dimensao
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.avaliacao_risco import AvaliacaoRisco
    from app.models.configuracao_sinal import ConfiguracaoSinal


class EvidenciaRisco(Base):
    """O porquê de cada alerta: um sinal disparado para uma avaliação."""

    __tablename__ = "evidencias_risco"

    id: Mapped[int] = mapped_column(primary_key=True)
    avaliacao_id: Mapped[int] = mapped_column(ForeignKey("avaliacoes_risco.id"), index=True)
    configuracao_sinal_id: Mapped[int] = mapped_column(ForeignKey("configuracoes_sinal.id"))
    dimensao: Mapped[Dimensao] = mapped_column(coluna_enum(Dimensao))
    valor_observado: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    linha_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    variacao_pct: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    meses_persistencia: Mapped[int]
    contribuicao: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    texto: Mapped[str] = mapped_column(Unicode(300))

    avaliacao: Mapped["AvaliacaoRisco"] = relationship(back_populates="evidencias")
    sinal: Mapped["ConfiguracaoSinal"] = relationship()
