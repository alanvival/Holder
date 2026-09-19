from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConfiguracaoSinal


class SinalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar(self) -> list[ConfiguracaoSinal]:
        return list(self._session.scalars(select(ConfiguracaoSinal).order_by(ConfiguracaoSinal.id)))

    def listar_ativos(self) -> list[ConfiguracaoSinal]:
        consulta = (
            select(ConfiguracaoSinal)
            .where(ConfiguracaoSinal.ativo.is_(True))
            .order_by(ConfiguracaoSinal.id)
        )
        return list(self._session.scalars(consulta))

    def listar_codigos(self) -> set[str]:
        return set(self._session.scalars(select(ConfiguracaoSinal.codigo)))

    def adicionar_todos(self, sinais: list[ConfiguracaoSinal]) -> None:
        if sinais:
            self._session.add_all(sinais)
            self._session.commit()
