"""
Testes de validação do score de risco (holder/dominio/risco/):
1. Reproduz a validação cruzada e confere que AUC/Brier não caíram muito
   abaixo do que já foi validado (referência: AUC ≈ 0.948, Brier ≈ 0.085) —
   se cair muito depois de qualquer mudança no pipeline de features,
   avisa antes de confiar no modelo em produção.
2. Backtest retroativo nos 22 clientes cancelados: confere que a
   probabilidade prevista sobe de forma consistente conforme se aproxima
   do cancelamento real (não força o número a bater, só confere a
   tendência geral).

Uso: pytest testes/test_modelo_risco.py
     pytest -m "not sqlserver"   pra pular tudo que depende do banco
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from holder.dominio.risco import dataset as ds
from holder.dominio.risco import modelo as mr
from holder.infra.dados.porta import fonte
from holder.infra.persistencia import modelo_treinado

AUC_MINIMO_ACEITAVEL = 0.85
BRIER_MAXIMO_ACEITAVEL = 0.15


@pytest.mark.sqlserver
@pytest.mark.lento
def test_validacao_cruzada():
    dataset = ds.construir_dataset()
    _, _, _, metricas = mr.treinar_modelo(dataset)

    print(f"AUC = {metricas['auc']:.3f} (mínimo aceitável: {AUC_MINIMO_ACEITAVEL})")
    print(f"Brier = {metricas['brier']:.3f} (máximo aceitável: {BRIER_MAXIMO_ACEITAVEL})")
    print(f"Amostras: {metricas['n_amostras']} ({metricas['n_positivos']} positivas)")

    assert metricas["auc"] >= AUC_MINIMO_ACEITAVEL, f"AUC caiu abaixo do aceitável: {metricas['auc']:.3f}"
    assert metricas["brier"] <= BRIER_MAXIMO_ACEITAVEL, f"Brier subiu acima do aceitável: {metricas['brier']:.3f}"
    print("OK   validação cruzada dentro do esperado.\n")


@pytest.mark.sqlserver
@pytest.mark.lento
def test_backtest_retroativo():
    modelo_pack = modelo_treinado.carregar()
    _, df_atd, df_sit, df_nps = fonte().carregar_tudo()
    cancelados = df_sit[df_sit["situacao"] == "Cancelado"][["cliente_id", "mes_cancelamento"]]

    por_lag = {lag: [] for lag in range(1, 7)}
    for _, r in cancelados.iterrows():
        cid, mes_canc = r["cliente_id"], r["mes_cancelamento"]
        for lag in range(1, 7):
            mes_alvo = ds.mes_mais(mes_canc, -lag)
            resultado = mr.calcular_score_cliente(cid, mes_alvo, df_atd, df_nps, modelo_pack)
            if resultado:
                por_lag[lag].append(resultado["risco_percentual"])

    medias = {lag: np.mean(vals) for lag, vals in por_lag.items() if vals}
    print("Probabilidade média prevista, por lag (meses antes do cancelamento real):")
    for lag in range(6, 0, -1):
        if lag in medias:
            print(f"  Lag {lag}: {medias[lag]:.1f}%  (n={len(por_lag[lag])})")

    # Tendência geral: lag 1 (mais perto do cancelamento) deve ter risco
    # médio bem maior que lag 6 (mais longe) — não exige monotonicidade
    # perfeita em cada lag intermediário, só a tendência de conjunto.
    assert medias[1] > medias[6], "Probabilidade não sobe conforme aproxima do cancelamento — modelo não está antecipando."
    assert medias[1] >= 70, f"Probabilidade no último mês antes do cancelamento está baixa demais: {medias[1]:.1f}%"
    print("OK   probabilidade sobe consistentemente conforme aproxima do cancelamento real.\n")


