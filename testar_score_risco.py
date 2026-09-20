"""
Backtest do score de risco (score_risco.py) contra os 22 clientes que
JÁ cancelaram: pra cada um, olha o score salvo (fScoreRisco) nos meses
-4 a -1 antes do cancelamento e reporta em que lag a maioria entra em "Em
risco"/"Crítico", e em que lag o sinal precoce aparece sozinho (score
precoce alto, confirmado ainda baixo) — é o teste real de que a arquitetura
de duas camadas antecipa o alerta, não só confirma depois que já era tarde.

Não força as conclusões do desafio a bater — reporta o resultado real,
seja qual for.

Uso: python testar_score_risco.py
(requer score_risco.py já ter rodado e salvo o histórico — ver
`python score_risco.py`)
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

import score_risco as sr


def _mes_menos(mes_ref: str, lag: int) -> str:
    ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
    data = dt.date(ano, mes, 1)
    for _ in range(lag):
        data = (data.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    return f"{data.year:04d}-{data.month:02d}"


def main():
    _, df_atd, df_sit, _ = sr.carregar_dados()
    historico = sr.carregar_historico()
    if historico.empty:
        print("Sem histórico salvo — rode `python score_risco.py` primeiro.")
        return

    cancelados = df_sit[df_sit["situacao"] == "Cancelado"][["cliente_id", "mes_cancelamento"]]
    print(f"Testando com {len(cancelados)} clientes cancelados da base.\n")

    por_lag = {lag: {"total": 0, "em_risco_ou_critico": 0, "precoce_isolado": 0} for lag in (1, 2, 3, 4, 5, 6)}
    detalhe_por_cliente = []

    for _, row in cancelados.iterrows():
        cid, mes_canc = row["cliente_id"], row["mes_cancelamento"]
        linhas_cliente = []
        for lag in (1, 2, 3, 4, 5, 6):
            mes_alvo = _mes_menos(mes_canc, lag)
            linha = historico[(historico["cliente_id"] == cid) & (historico["mes_ref"] == mes_alvo)]
            if linha.empty:
                continue
            r = linha.iloc[0]
            por_lag[lag]["total"] += 1
            if r["faixa"] in ("Em risco", "Crítico"):
                por_lag[lag]["em_risco_ou_critico"] += 1
            # "sinal precoce isolado": precoce alto, confirmado ainda dentro do normal
            if r["score_precoce"] >= 50 and r["score_confirmado"] < 40:
                por_lag[lag]["precoce_isolado"] += 1
            linhas_cliente.append((lag, r["risco_percentual"], r["faixa"], r["score_precoce"], r["score_confirmado"]))
        detalhe_por_cliente.append((cid, mes_canc, linhas_cliente))

    print("=== Resumo por lag (meses antes do cancelamento) ===")
    print(f"{'Lag':>4} | {'Amostra':>7} | {'% Em risco/Crítico':>18} | {'% Precoce isolado':>17}")
    for lag in (6, 5, 4, 3, 2, 1):
        d = por_lag[lag]
        if d["total"] == 0:
            continue
        pct_risco = d["em_risco_ou_critico"] / d["total"] * 100
        pct_precoce = d["precoce_isolado"] / d["total"] * 100
        print(f"{lag:>4} | {d['total']:>7} | {pct_risco:>17.1f}% | {pct_precoce:>16.1f}%")

    print("\n=== Detalhe por cliente (lag: risco% / faixa) ===")
    for cid, mes_canc, linhas in detalhe_por_cliente:
        resumo = ", ".join(f"L{lag}:{risco:.0f}%({faixa})" for lag, risco, faixa, *_ in sorted(linhas))
        print(f"{cid} (cancelou {mes_canc}): {resumo}")

    print("\nNota: 'Precoce isolado' = score_precoce >= 50 e score_confirmado < 40 nesse lag —")
    print("é o caso que justifica ter duas camadas separadas: pega o problema antes do score total subir.")


if __name__ == "__main__":
    main()
