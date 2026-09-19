from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ClassificacaoNPS
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.cliente import Cliente


class PesquisaNps(Base):
    __tablename__ = "pesquisas_nps"
    __table_args__ = (UniqueConstraint("cliente_id", "mes_ref", name="uq_nps_cliente_mes"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"), index=True)
    mes_ref: Mapped[date] = mapped_column(Date)
    respondeu: Mapped[bool] = mapped_column(Boolean)
    nota_nps: Mapped[int | None]
    classificacao_nps: Mapped[ClassificacaoNPS] = mapped_column(coluna_enum(ClassificacaoNPS))

    # Declarar a relação faz o SQLAlchemy inserir o cliente antes (FK) no mesmo flush.
    cliente: Mapped["Cliente"] = relationship()
