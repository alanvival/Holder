from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Numeric, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Plano, Porte
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.situacao_cliente import Situacao


class Cliente(Base):
    __tablename__ = "clientes"

    cliente_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    segmento: Mapped[str] = mapped_column(Unicode(50))
    porte: Mapped[Porte] = mapped_column(coluna_enum(Porte))
    plano: Mapped[Plano] = mapped_column(coluna_enum(Plano))
    valor_mensal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sla_contratado_h: Mapped[int]
    inicio_contrato: Mapped[date] = mapped_column(Date)

    situacao: Mapped["Situacao | None"] = relationship(back_populates="cliente", uselist=False)
