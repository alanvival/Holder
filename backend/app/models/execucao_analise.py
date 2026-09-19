from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, agora_utc
from app.core.enums import TipoExecucao
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.avaliacao_risco import AvaliacaoRisco


class ExecucaoAnalise(Base):
    __tablename__ = "execucoes_analise"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoExecucao] = mapped_column(coluna_enum(TipoExecucao))
    mes_referencia: Mapped[date] = mapped_column(Date)
    versao_modelo: Mapped[str] = mapped_column(String(20))
    parametros_json: Mapped[str] = mapped_column(UnicodeText)
    executado_por_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    executado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    qtd_clientes_avaliados: Mapped[int]

    avaliacoes: Mapped[list["AvaliacaoRisco"]] = relationship(
        back_populates="execucao", cascade="all, delete-orphan"
    )

    @property
    def qtd_na_fila(self) -> int:
        return sum(1 for avaliacao in self.avaliacoes if avaliacao.posicao_fila is not None)
