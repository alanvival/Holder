"""Fila de atendimento priorizada — função pura.

Regra: receita em risco = score × valor mensal. Entram na fila só CRITICO e
ATENCAO, ordenados por faixa e depois por receita em risco (maior primeiro),
até a capacidade da fila. Os demais continuam avaliados, mas sem posição.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.core.enums import FaixaRisco

ORDEM_FAIXA = {
    FaixaRisco.CRITICO: 0,
    FaixaRisco.ATENCAO: 1,
    FaixaRisco.MONITORAR: 2,
    FaixaRisco.SAUDAVEL: 3,
}
FAIXAS_DA_FILA = {FaixaRisco.CRITICO, FaixaRisco.ATENCAO}


@dataclass
class ItemAvaliado:
    cliente_id: str
    valor_mensal: float
    score: float
    faixa: FaixaRisco
    receita_em_risco: float = 0.0
    posicao_fila: int | None = None


def priorizar(itens: list[ItemAvaliado], capacidade: int) -> list[ItemAvaliado]:
    calculados = [
        replace(item, receita_em_risco=round(item.score * item.valor_mensal, 2), posicao_fila=None)
        for item in itens
    ]
    ordenados = sorted(
        calculados,
        key=lambda i: (ORDEM_FAIXA[i.faixa], -i.receita_em_risco, i.cliente_id),
    )
    posicao = 0
    for item in ordenados:
        if item.faixa in FAIXAS_DA_FILA and posicao < capacidade:
            posicao += 1
            item.posicao_fila = posicao
    return ordenados
