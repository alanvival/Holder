"""
As faixas de ação do score de risco.

Quatro nomes, e são exclusivos deste conceito: o índice de alerta usa
Alto/Médio/Baixo justamente para não colidir com estes. Ver `CONTEXT.md`.
"""
from __future__ import annotations

# Ponto de partida, a recalibrar quando houver histórico real de quantos
# clientes em cada faixa efetivamente cancelaram.
FAIXAS = [
    (0, 30, "Saudável"),
    (30, 55, "Atenção"),
    (55, 75, "Em risco"),
    (75, 101, "Crítico"),
]

NOMES = [nome for _, _, nome in FAIXAS]


def faixa_de(risco_percentual: float) -> str:
    for lo, hi, nome in FAIXAS:
        if lo <= risco_percentual < hi:
            return nome
    return "Crítico"


def arredondar(v):
    """Duas casas, tratando None e NaN (`v != v` é verdade só para NaN)."""
    if v is None or v != v:
        return None
    return round(float(v), 2)
