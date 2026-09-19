from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Cliente


class ClienteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_todos(self) -> list[Cliente]:
        consulta = (
            select(Cliente).options(selectinload(Cliente.situacao)).order_by(Cliente.cliente_id)
        )
        return list(self._session.scalars(consulta))

    def obter(self, cliente_id: str) -> Cliente | None:
        consulta = (
            select(Cliente)
            .options(selectinload(Cliente.situacao))
            .where(Cliente.cliente_id == cliente_id)
        )
        return self._session.scalar(consulta)
