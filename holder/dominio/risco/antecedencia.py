"""
Com quanta antecedência o sinal aparece.

Primeira das três perguntas que o enunciado do desafio lista como
estruturantes: "um sinal que só se manifesta no mês da saída pode ser
certeiro e, ainda assim, inútil: não sobra tempo de agir".

A medição é um backtest retroativo: para cada um dos clientes que já
cancelaram, calcula o score que o modelo teria dado 1, 2, ... 6 meses
ANTES do mês em que ele de fato saiu, e tira a média por distância. Se a
curva sobe conforme se aproxima da saída, o modelo antecipa; onde ela
cruza a faixa Crítico é a antecedência útil — quantos meses o time teria
para agir.

Não é validação do modelo (isso é AUC/Brier, em `modelo.py`): é a
resposta operacional de "quando isso acende?".
"""
from __future__ import annotations

import numpy as np

from . import dataset as ds
from . import modelo as mr
from .faixas import faixa_de

LAG_MAXIMO = 6


def curva_de_antecedencia(df_sit, df_atd, df_nps, modelo_pack, lag_maximo: int = LAG_MAXIMO) -> list[dict]:
    """Risco médio previsto por distância (em meses) do cancelamento real.

    Devolve uma linha por lag, do mais distante para o mais próximo, já com
    a faixa em que aquela média cai — é o que permite dizer "a partir daqui
    o modelo já classificaria como Crítico".
    """
    cancelados = df_sit[df_sit["situacao"] == "Cancelado"][["cliente_id", "mes_cancelamento"]]

    por_lag: dict[int, list[float]] = {lag: [] for lag in range(1, lag_maximo + 1)}
    for _, r in cancelados.iterrows():
        for lag in range(1, lag_maximo + 1):
            mes_alvo = ds.mes_mais(r["mes_cancelamento"], -lag)
            resultado = mr.calcular_score_cliente(r["cliente_id"], mes_alvo, df_atd, df_nps, modelo_pack)
            if resultado:
                por_lag[lag].append(resultado["risco_percentual"])

    linhas = []
    for lag in range(lag_maximo, 0, -1):
        valores = por_lag[lag]
        if not valores:
            continue
        media = float(np.mean(valores))
        linhas.append({
            "meses_antes": lag,
            "risco_medio": round(media, 1),
            "faixa": faixa_de(media),
            "n_clientes": len(valores),
        })
    return linhas


def antecedencia_util(linhas: list[dict], faixa_alvo: str = "Crítico") -> int | None:
    """Quantos meses antes da saída o risco médio já alcança `faixa_alvo` —
    a antecedência que o time de fato teria para agir. None se a curva
    nunca chega lá dentro do horizonte medido."""
    candidatos = [l["meses_antes"] for l in linhas if l["faixa"] == faixa_alvo]
    return max(candidatos) if candidatos else None
