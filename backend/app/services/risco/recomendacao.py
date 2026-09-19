"""Recomendação de ação a partir das evidências — função pura.

Regras (em ordem): 3+ dimensões → COMITE_RETENCAO; reuniões canceladas +
silêncio no NPS → CONTATO_EXECUTIVO; senão, a dimensão com maior
contribuição somada define a ação.
"""

from __future__ import annotations

from collections import defaultdict

from app.core.enums import Dimensao
from app.services.risco.score import Evidencia

ACAO_POR_DIMENSAO: dict[Dimensao, str] = {
    Dimensao.ATENDIMENTO: "REVISAO_TECNICA",
    Dimensao.SLA: "REVISAO_TECNICA",
    Dimensao.ENGAJAMENTO: "REUNIAO_VALOR",
    Dimensao.FINANCEIRO: "CONVERSA_FINANCEIRA",
    Dimensao.SATISFACAO: "PLANO_DE_RECUPERACAO",
}
ORDEM_DIMENSAO = list(Dimensao)


def recomendar(evidencias: list[Evidencia]) -> str | None:
    if not evidencias:
        return None
    dimensoes = {e.disparo.sinal.dimensao for e in evidencias}
    if len(dimensoes) >= 3:
        return "COMITE_RETENCAO"
    codigos = {e.disparo.sinal.codigo for e in evidencias}
    if {"REUNIOES_CANCELADAS", "NPS_SILENCIO"} <= codigos:
        return "CONTATO_EXECUTIVO"
    por_dimensao: dict[Dimensao, float] = defaultdict(float)
    for evidencia in evidencias:
        por_dimensao[evidencia.disparo.sinal.dimensao] += evidencia.contribuicao
    dominante = min(por_dimensao, key=lambda d: (-por_dimensao[d], ORDEM_DIMENSAO.index(d)))
    return ACAO_POR_DIMENSAO[dominante]
