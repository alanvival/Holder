"""
As linhas de corte dos strikes: o perfil típico dos meses de quem já
cancelou.

Mediana para a maioria das colunas; média apenas para reclamações formais,
que são contagens esparsas (a mediana de uma coluna que é quase toda zero
seria zero, e o corte não separaria nada).
"""
from __future__ import annotations

from ..metricas.resolvedor import filtrar

COLUNAS = [
    "chamados_abertos", "chamados_criticos", "chamados_reabertos", "chamados_dentro_sla",
    "pct_sla_cumprido", "tempo_medio_resolucao_h", "reclamacoes_formais",
    "uso_plataforma_pct", "dias_atraso_pagamento",
]

# Contagens esparsas: média, não mediana.
COLUNAS_POR_MEDIA = {"reclamacoes_formais"}


def linhas_de_corte() -> dict[str, float]:
    df_cancelados = filtrar("atendimento_mensal", {"situacao": "Cancelado"})
    if len(df_cancelados) == 0:
        return {}

    linhas = {}
    for col in COLUNAS:
        serie = df_cancelados[col].dropna()
        if len(serie) == 0:
            continue
        linhas[col] = float(serie.mean()) if col in COLUNAS_POR_MEDIA else float(serie.median())
    return linhas
