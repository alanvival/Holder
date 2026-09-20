"""
O catálogo de métricas: definição declarativa, uma entrada por métrica.

Cada entrada diz de qual tabela ler, qual agregação aplicar, quais linhas
excluir e como escalar o resultado — nunca *como* somar ou dividir, que é
papel de `agregacoes.py`. Cada entrada espelha uma métrica de `METRICAS` em
`assistente-consultas/src/engine/metricas.js`: mesma fórmula, mesmas
exclusões, mesmo campo de origem.

Os quatro ids que hoje divergem do lado JavaScript (`atraso_pagamento`,
`churn`, `uso_plataforma`, `nps`) convergem na fase 7, quando este arquivo
passa a ser gerado a partir de uma definição única.
"""
from __future__ import annotations

from . import agregacoes as ag
from .nps import calcular_nps

PLANO_LABELS = {"Essencial": "Essencial", "Avancado": "Avançado", "Enterprise": "Enterprise"}
PORTE_LABELS = {"Pequeno": "Pequeno", "Medio": "Médio", "Grande": "Grande"}

METRICAS = {
    "ticket_medio": {
        "rotulo": "Ticket médio",
        "aba": "clientes",
        "formato": "moeda",
        "calcular": lambda df: ag.media(df["valor_mensal"]),
    },
    "antiguidade_contrato": {
        "rotulo": "Antiguidade do contrato",
        "aba": "clientes",
        "formato": "dias",
        # Ranking por "maior" = contrato mais VELHO (mais dias desde o
        # início) = cliente mais antigo; "menor" = cliente mais novo.
        "calcular": ag.antiguidade_dias,
    },
    "sla_contratado": {
        # Diferente de "sla_cumprido" (% de chamados dentro do prazo, mês a
        # mês) — este é o PRAZO em horas que consta no contrato, fixo por
        # cliente (6h Enterprise / 12h Avançado / 24h Essencial nesta base).
        "rotulo": "SLA contratado",
        "aba": "clientes",
        "formato": "horas",
        "calcular": lambda df: ag.media(df["sla_contratado_h"]),
    },
    "tempo_medio_resolucao": {
        "rotulo": "Tempo médio de resolução",
        "aba": "atendimento_mensal",
        "formato": "horas",
        # Exclui linhas sem chamado (residual de tempo sem chamado real).
        "filtro_linha": lambda df: df[df["chamados_abertos"] > 0],
        "calcular": lambda df: ag.media_ponderada(df, "tempo_medio_resolucao_h", "chamados_abertos"),
        "leitura_alternativa": {
            "rotulo": "média simples (sem ponderar pelo volume de chamados)",
            "calcular": lambda df: ag.media(df["tempo_medio_resolucao_h"]),
        },
    },
    "media_reclamacoes": {
        "rotulo": "Média de reclamações",
        "aba": "atendimento_mensal",
        "formato": "numero",
        "calcular": lambda df: ag.media(df["reclamacoes_formais"]),
    },
    "atraso_pagamento": {
        "rotulo": "Atraso médio de pagamento",
        "aba": "atendimento_mensal",
        "formato": "dias",
        "calcular": lambda df: ag.media(df["dias_atraso_pagamento"]),
    },
    "sla_cumprido": {
        "rotulo": "SLA cumprido",
        "aba": "atendimento_mensal",
        "formato": "percentual",
        "filtro_linha": lambda df: df[df["chamados_abertos"] > 0],
        "calcular": lambda df: ag.razao_soma(df, "chamados_dentro_sla", "chamados_abertos"),
        "escala100": True,
        "leitura_alternativa": {
            "rotulo": "média simples do percentual mensal já calculado",
            "calcular": lambda df: ag.media(df["pct_sla_cumprido"]),
        },
    },
    "churn": {
        "rotulo": "Taxa de cancelamento (churn)",
        "aba": "situacao_clientes",
        "formato": "percentual",
        "escala100": True,
        "calcular": lambda df: float((df["situacao"] == "Cancelado").mean()) if len(df) else None,
    },
    "uso_plataforma": {
        "rotulo": "Uso médio da plataforma",
        "aba": "atendimento_mensal",
        "formato": "percentual",
        "calcular": lambda df: ag.media(df["uso_plataforma_pct"]),
    },
    "reunioes_realizadas": {
        "rotulo": "Reuniões realizadas",
        "aba": "atendimento_mensal",
        "formato": "percentual",
        "escala100": True,
        "calcular": lambda df: ag.razao_soma(df, "reunioes_realizadas", "reunioes_previstas"),
    },
    "chamados_criticos": {
        "rotulo": "Chamados críticos",
        "aba": "atendimento_mensal",
        "formato": "inteiro",
        "calcular": lambda df: ag.soma(df["chamados_criticos"]),
    },
    "taxa_reabertura": {
        "rotulo": "Taxa de reabertura",
        "aba": "atendimento_mensal",
        "formato": "percentual",
        "escala100": True,
        "filtro_linha": lambda df: df[df["chamados_abertos"] > 0],
        "calcular": lambda df: ag.razao_soma(df, "chamados_reabertos", "chamados_abertos"),
    },
    "nps": {
        "rotulo": "NPS",
        "aba": "pesquisas_nps",
        "formato": "nps",
        "calcular": calcular_nps,
    },
}
