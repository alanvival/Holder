from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import AvaliacaoRisco, EvidenciaRisco


class AvaliacaoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _consulta(execucao_id: int) -> Select[tuple[AvaliacaoRisco]]:
        return (
            select(AvaliacaoRisco)
            .where(AvaliacaoRisco.execucao_id == execucao_id)
            .options(
                selectinload(AvaliacaoRisco.cliente),
                selectinload(AvaliacaoRisco.acao_recomendada),
                selectinload(AvaliacaoRisco.evidencias).selectinload(EvidenciaRisco.sinal),
            )
        )

    def listar_por_execucao(self, execucao_id: int) -> list[AvaliacaoRisco]:
        return list(self._session.scalars(self._consulta(execucao_id)))

    def fila(self, execucao_id: int, limite: int) -> list[AvaliacaoRisco]:
        consulta = (
            self._consulta(execucao_id)
            .where(AvaliacaoRisco.posicao_fila.is_not(None))
            .order_by(AvaliacaoRisco.posicao_fila)
            .limit(limite)
        )
        return list(self._session.scalars(consulta))

    def obter_por_cliente(self, execucao_id: int, cliente_id: str) -> AvaliacaoRisco | None:
        consulta = self._consulta(execucao_id).where(AvaliacaoRisco.cliente_id == cliente_id)
        return self._session.scalar(consulta)
