from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import FaixaRisco
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.acao_recomendada import AcaoRecomendada
    from app.models.cliente import Cliente
    from app.models.evidencia_risco import EvidenciaRisco
    from app.models.execucao_analise import ExecucaoAnalise


class AvaliacaoRisco(Base):
    __tablename__ = "avaliacoes_risco"
    __table_args__ = (
        UniqueConstraint("execucao_id", "cliente_id", name="uq_avaliacao_execucao_cliente"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    execucao_id: Mapped[int] = mapped_column(ForeignKey("execucoes_analise.id"), index=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"))
    mes_referencia: Mapped[date] = mapped_column(Date)
    score_risco: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    faixa: Mapped[FaixaRisco] = mapped_column(coluna_enum(FaixaRisco))
    qtd_dimensoes_afetadas: Mapped[int]
    receita_em_risco: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    posicao_fila: Mapped[int | None]
    acao_recomendada_id: Mapped[int | None] = mapped_column(ForeignKey("acoes_recomendadas.id"))

    execucao: Mapped["ExecucaoAnalise"] = relationship(back_populates="avaliacoes")
    cliente: Mapped["Cliente"] = relationship()
    acao_recomendada: Mapped["AcaoRecomendada | None"] = relationship()
    evidencias: Mapped[list["EvidenciaRisco"]] = relationship(
        back_populates="avaliacao", cascade="all, delete-orphan", order_by="EvidenciaRisco.id"
    )
