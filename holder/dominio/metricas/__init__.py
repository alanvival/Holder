"""
Catálogo de métricas agregadas da carteira.

- `agregacoes.py`  as cinco agregações nomeadas (média, média ponderada,
                   razão de somas, proporção, soma);
- `definicoes.py`  o catálogo declarativo, uma entrada por métrica;
- `resolvedor.py`  aplica a definição e devolve o número;
- `nps.py`         o NPS, que tem estrutura própria.
"""
from .definicoes import METRICAS, PLANO_LABELS, PORTE_LABELS
from .resolvedor import (
    calcular_metrica,
    comparar_metrica_por_categoria,
    descrever_universo,
    filtrar,
)

__all__ = [
    "METRICAS",
    "PLANO_LABELS",
    "PORTE_LABELS",
    "calcular_metrica",
    "comparar_metrica_por_categoria",
    "descrever_universo",
    "filtrar",
]
