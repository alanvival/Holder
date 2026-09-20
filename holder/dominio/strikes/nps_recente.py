"""
A última opinião que o cliente de fato deu.

Regra única do strike "Último NPS detrator": vale a pesquisa mais recente
**respondida**, não a linha mais recente da tabela.

A diferença não é acadêmica. Havia duas leituras no repo: o painel do
dashboard pegava a última linha de pesquisa sem filtrar `respondeu`, então
um cliente cujo convite mais novo ficou sem resposta aparecia com a
classificação vazia — e **perdia o strike**, mesmo tendo sido detrator na
última vez que respondeu. Nesta base isso escondia três clientes
(C012, C069 e C080).

Esquecer um detrator porque ele ignorou o convite seguinte é a pior leitura
possível: pelo `CONTEXT.md`, não-resposta é comportamento observado, não
dado faltante. Quem cala depois de reclamar não ficou satisfeito.
"""
from __future__ import annotations

import pandas as pd


def _respondidas(df_nps: pd.DataFrame) -> pd.DataFrame:
    return df_nps[df_nps["respondeu"] == 1].sort_values("mes_ref")


def ultima_classificacao_por_cliente(df_nps: pd.DataFrame) -> pd.Series:
    """Série `cliente_id -> classificacao_nps` da pesquisa respondida mais
    recente de cada cliente. Clientes que nunca responderam ficam fora."""
    respondidas = _respondidas(df_nps)
    if len(respondidas) == 0:
        return pd.Series(dtype="object")
    return respondidas.groupby("cliente_id").tail(1).set_index("cliente_id")["classificacao_nps"]


def ultima_classificacao(df_nps: pd.DataFrame, cliente_id: str) -> str | None:
    respondidas = _respondidas(df_nps)
    do_cliente = respondidas[respondidas["cliente_id"] == cliente_id]
    if len(do_cliente) == 0:
        return None
    return do_cliente.iloc[-1]["classificacao_nps"]
