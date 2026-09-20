"""
NPS da carteira.

Tem estrutura própria (score, nota média, respondidas, convites) e por isso
não cabe no formato "um valor" das outras métricas. A contagem de
`convites` importa: ausência de resposta é comportamento observado, não dado
faltante — ver `CONTEXT.md`, verbete "Não-resposta".
"""
from __future__ import annotations


def calcular_nps(df):
    respondidas = df[df["respondeu"] == 1]
    if len(respondidas) == 0:
        return None
    promotores = (respondidas["classificacao_nps"] == "Promotor").sum()
    detratores = (respondidas["classificacao_nps"] == "Detrator").sum()
    return {
        "score": float((promotores - detratores) / len(respondidas) * 100),
        "nota_media": float(respondidas["nota_nps"].mean()),
        "respondidas": int(len(respondidas)),
        "convites": int(len(df)),
    }
