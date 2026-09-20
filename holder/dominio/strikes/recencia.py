"""
A janela de recência dos strikes.

"Recente" = os dois últimos meses **em que houve medição**, não o mês
corrente e o anterior pelo calendário. A diferença aparece quando um cliente
não tem registro no mês mais recente da base: a leitura por calendário
esconderia o strike dele em silêncio.

Este módulo existe porque a regra estava escrita duas vezes, com definições
diferentes: o painel do dashboard usava `DateOffset(months=1)` e o motor do
assistente usava os dois últimos meses presentes nos dados. Agora há um só
lugar, e é este.
"""
from __future__ import annotations

QUANTIDADE_PADRAO = 2


def meses_recentes(df, quantidade: int = QUANTIDADE_PADRAO) -> list:
    """Os últimos `quantidade` valores distintos de `mes_ref` presentes no
    DataFrame, em ordem crescente."""
    if "mes_ref" not in df.columns or len(df) == 0:
        return []
    return sorted(df["mes_ref"].unique())[-quantidade:]
