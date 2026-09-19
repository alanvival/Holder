from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import SituacaoCliente
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.cliente import Cliente


class Situacao(Base):
    __tablename__ = "situacao_clientes"

    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"), primary_key=True)
    situacao: Mapped[SituacaoCliente] = mapped_column(coluna_enum(SituacaoCliente))
    mes_cancelamento: Mapped[date | None] = mapped_column(Date)

    cliente: Mapped["Cliente"] = relationship(back_populates="situacao")
