from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtendimentoMensal(Base):
    __tablename__ = "atendimentos_mensais"
    __table_args__ = (UniqueConstraint("cliente_id", "mes_ref", name="uq_atendimento_cliente_mes"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"), index=True)
    mes_ref: Mapped[date] = mapped_column(Date, index=True)
    chamados_abertos: Mapped[int]
    chamados_criticos: Mapped[int]
    chamados_reabertos: Mapped[int]
    chamados_dentro_sla: Mapped[int]
    pct_sla_cumprido: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    tempo_medio_resolucao_h: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    reclamacoes_formais: Mapped[int]
    uso_plataforma_pct: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    dias_atraso_pagamento: Mapped[int]
    reunioes_previstas: Mapped[int]
    reunioes_realizadas: Mapped[int]
