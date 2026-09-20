"""
Score de risco: modelo treinado nos cancelamentos reais.

Responde "em que ordem falar?". Não confundir com `holder/dominio/alerta/`
nem com `holder/dominio/strikes/` — ver `CONTEXT.md`.
"""
from .faixas import FAIXAS, arredondar, faixa_de
from .modelo import calcular_risco_todos_clientes, calcular_score_cliente, treinar_modelo

__all__ = [
    "FAIXAS",
    "arredondar",
    "faixa_de",
    "calcular_risco_todos_clientes",
    "calcular_score_cliente",
    "treinar_modelo",
]
