from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PesquisaNps


class NpsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_todos(self) -> list[PesquisaNps]:
        consulta = select(PesquisaNps).order_by(PesquisaNps.cliente_id, PesquisaNps.mes_ref)
        return list(self._session.scalars(consulta))

    def listar_por_cliente(self, cliente_id: str) -> list[PesquisaNps]:
        consulta = (
            select(PesquisaNps)
            .where(PesquisaNps.cliente_id == cliente_id)
            .order_by(PesquisaNps.mes_ref)
        )
        return list(self._session.scalars(consulta))
