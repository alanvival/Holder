from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AcaoRecomendada


class AcaoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar(self) -> list[AcaoRecomendada]:
        return list(self._session.scalars(select(AcaoRecomendada).order_by(AcaoRecomendada.ordem)))

    def listar_codigos(self) -> set[str]:
        return set(self._session.scalars(select(AcaoRecomendada.codigo)))

    def mapa_por_codigo(self) -> dict[str, AcaoRecomendada]:
        return {acao.codigo: acao for acao in self.listar()}

    def adicionar_todos(self, acoes: list[AcaoRecomendada]) -> None:
        if acoes:
            self._session.add_all(acoes)
            self._session.commit()
