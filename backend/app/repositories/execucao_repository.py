from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import TipoExecucao
from app.models import ExecucaoAnalise


class ExecucaoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def gravar(self, execucao: ExecucaoAnalise) -> ExecucaoAnalise:
        """Grava a execução com avaliações e evidências em uma única transação."""
        try:
            self._session.add(execucao)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return execucao

    def ultima_producao(self) -> ExecucaoAnalise | None:
        consulta = (
            select(ExecucaoAnalise)
            .where(ExecucaoAnalise.tipo == TipoExecucao.PRODUCAO)
            .order_by(ExecucaoAnalise.executado_em.desc(), ExecucaoAnalise.id.desc())
            .limit(1)
        )
        return self._session.scalar(consulta)
