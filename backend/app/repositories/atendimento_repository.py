from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AtendimentoMensal


class AtendimentoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_todos(self) -> list[AtendimentoMensal]:
        consulta = select(AtendimentoMensal).order_by(
            AtendimentoMensal.cliente_id, AtendimentoMensal.mes_ref
        )
        return list(self._session.scalars(consulta))

    def listar_por_cliente(self, cliente_id: str) -> list[AtendimentoMensal]:
        consulta = (
            select(AtendimentoMensal)
            .where(AtendimentoMensal.cliente_id == cliente_id)
            .order_by(AtendimentoMensal.mes_ref)
        )
        return list(self._session.scalars(consulta))

    def ultimo_mes(self) -> date | None:
        return self._session.scalar(select(func.max(AtendimentoMensal.mes_ref)))
