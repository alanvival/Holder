from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import (
    AtendimentoMensal,
    AvaliacaoRisco,
    Cliente,
    EvidenciaRisco,
    ExecucaoAnalise,
    PesquisaNps,
    Situacao,
)


class OrigemRepository:
    """Grava os dados de origem (planilha). Substitui tudo em uma única transação."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def substituir_tudo(
        self,
        clientes: list[Cliente],
        situacoes: list[Situacao],
        atendimentos: list[AtendimentoMensal],
        pesquisas: list[PesquisaNps],
    ) -> None:
        try:
            for modelo in (
                EvidenciaRisco,
                AvaliacaoRisco,
                ExecucaoAnalise,
                AtendimentoMensal,
                PesquisaNps,
                Situacao,
                Cliente,
            ):
                self._session.execute(delete(modelo))
            self._session.add_all(clientes)
            self._session.flush()
            self._session.add_all([*situacoes, *atendimentos, *pesquisas])
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        finally:
            self._session.expunge_all()
