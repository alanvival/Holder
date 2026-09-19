from datetime import date

from sqlalchemy import Float, cast, func, select
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

    def agregado_mensal(self, coluna: str, agregacao: str) -> list[tuple[date, float]]:
        """Média ou soma mensal de uma coluna de toda a carteira, ignorando nulos.

        A média usa `cast(campo, Float)` para que colunas inteiras não sejam
        truncadas por uma AVG inteira (comportamento do SQL Server).
        """
        campo = getattr(AtendimentoMensal, coluna)
        valor_agregado = func.avg(cast(campo, Float)) if agregacao == "media" else func.sum(campo)
        consulta = (
            select(AtendimentoMensal.mes_ref, valor_agregado)
            .where(campo.is_not(None))
            .group_by(AtendimentoMensal.mes_ref)
            .order_by(AtendimentoMensal.mes_ref)
        )
        return [(mes, float(valor)) for mes, valor in self._session.execute(consulta)]
