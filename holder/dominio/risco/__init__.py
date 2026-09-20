"""
Score de risco: modelo treinado nos cancelamentos reais.

Responde "em que ordem falar?". Não confundir com `holder/dominio/alerta/`
nem com `holder/dominio/strikes/` — ver `CONTEXT.md`.
"""
from .antecedencia import antecedencia_util, curva_de_antecedencia
from .faixas import ACAO_POR_FAIXA, FAIXAS, arredondar, faixa_de
from .modelo import calcular_risco_todos_clientes, calcular_score_cliente, treinar_modelo

__all__ = [
    "ACAO_POR_FAIXA",
    "FAIXAS",
    "antecedencia_util",
    "arredondar",
    "curva_de_antecedencia",
    "faixa_de",
    "calcular_risco_todos_clientes",
    "calcular_score_cliente",
    "treinar_modelo",
]
