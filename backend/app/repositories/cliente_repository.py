from dataclasses import dataclass

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.enums import FaixaRisco, Plano, Porte, SituacaoCliente
from app.models import AvaliacaoRisco, Cliente, Situacao


@dataclass(frozen=True)
class FiltroClientes:
    situacao: SituacaoCliente | None = None
    faixa: FaixaRisco | None = None
    plano: Plano | None = None
    porte: Porte | None = None
    segmento: str | None = None
    busca: str | None = None


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

    def buscar(
        self,
        execucao_id: int | None,
        filtro: FiltroClientes,
        ordenar: str,
        offset: int,
        limite: int,
    ) -> tuple[list[tuple[Cliente, AvaliacaoRisco | None]], int]:
        """Clientes + avaliação da execução informada (outer join), filtrados e paginados."""
        juncao_avaliacao = and_(
            AvaliacaoRisco.cliente_id == Cliente.cliente_id,
            AvaliacaoRisco.execucao_id == (execucao_id if execucao_id is not None else -1),
        )
        condicoes = self._condicoes(filtro)

        total = self._session.scalar(
            select(func.count(Cliente.cliente_id))
            .select_from(Cliente)
            .outerjoin(Situacao, Situacao.cliente_id == Cliente.cliente_id)
            .outerjoin(AvaliacaoRisco, juncao_avaliacao)
            .where(*condicoes)
        )
        consulta = (
            select(Cliente, AvaliacaoRisco)
            .select_from(Cliente)
            .outerjoin(Situacao, Situacao.cliente_id == Cliente.cliente_id)
            .outerjoin(AvaliacaoRisco, juncao_avaliacao)
            .options(selectinload(Cliente.situacao))
            .where(*condicoes)
            .order_by(*self._ordem(ordenar))
            .offset(offset)
            .limit(limite)
        )
        linhas = [(cliente, avaliacao) for cliente, avaliacao in self._session.execute(consulta)]
        return linhas, total or 0

    @staticmethod
    def _condicoes(filtro: FiltroClientes) -> list[ColumnElement[bool]]:
        condicoes: list[ColumnElement[bool]] = []
        if filtro.situacao is not None:
            condicoes.append(Situacao.situacao == filtro.situacao)
        if filtro.faixa is not None:
            condicoes.append(AvaliacaoRisco.faixa == filtro.faixa)
        if filtro.plano is not None:
            condicoes.append(Cliente.plano == filtro.plano)
        if filtro.porte is not None:
            condicoes.append(Cliente.porte == filtro.porte)
        if filtro.segmento:
            condicoes.append(func.lower(Cliente.segmento) == filtro.segmento.strip().lower())
        if filtro.busca and filtro.busca.strip():
            termo = f"%{filtro.busca.strip().lower()}%"
            condicoes.append(
                or_(
                    func.lower(Cliente.cliente_id).like(termo),
                    func.lower(Cliente.segmento).like(termo),
                )
            )
        return condicoes

    @staticmethod
    def _ordem(ordenar: str) -> list:
        # "nulos no fim" portável (SQL Server não tem NULLS LAST)
        if ordenar == "valor_mensal":
            return [Cliente.valor_mensal.desc(), Cliente.cliente_id]
        if ordenar in ("score", "receita_em_risco"):
            coluna = (
                AvaliacaoRisco.score_risco
                if ordenar == "score"
                else AvaliacaoRisco.receita_em_risco
            )
            return [case((coluna.is_(None), 1), else_=0), coluna.desc(), Cliente.cliente_id]
        return [Cliente.cliente_id]
