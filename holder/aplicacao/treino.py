"""
Caso de uso: treinar o modelo de risco e recalcular o histórico mensal.

    python -m holder.aplicacao.treino

Mora em `aplicacao/` e não em `dominio/risco/` porque é orquestração: pede o
dataset ao domínio, manda treinar, grava o pickle, registra o log do treino
e regrava o histórico mês a mês. O domínio calcula; quem escreve é daqui.
"""
from __future__ import annotations

import json

import pandas as pd

from holder.dominio.risco.dataset import construir_dataset
from holder.dominio.risco.modelo import calcular_risco_todos_clientes, treinar_modelo
from holder.infra.dados.porta import fonte
from holder.infra.persistencia import historico_score, log_treinos, modelo_treinado


def salvar_historico_mes(mes_ref: str | None = None, apenas_ativos: bool = False) -> int:
    resultados = calcular_risco_todos_clientes(mes_ref=mes_ref, apenas_ativos=apenas_ativos)
    if not resultados:
        return 0
    mes_ref_real = resultados[0]["mes_ref"]

    df_linhas = pd.DataFrame([
        {
            "cliente_id": r["cliente_id"],
            "mes_ref": r["mes_ref"],
            "score_precoce": r["score_precoce"],
            "score_confirmado": r["score_confirmado"],
            "risco_percentual": r["risco_percentual"],
            "faixa": r["faixa"],
            "sinais_detalhados": json.dumps(r["sinais_detalhados"], ensure_ascii=False),
        }
        for r in resultados
    ])

    return historico_score.salvar_mes(df_linhas, mes_ref_real)


def recalcular_historico_completo() -> dict:
    _, df_atd, _, _ = fonte().carregar_tudo()
    meses = sorted(df_atd["mes_ref"].unique())
    return {mes: salvar_historico_mes(mes_ref=mes, apenas_ativos=False) for mes in meses}


def main() -> None:
    print("Treinando modelo (regressão logística) e validando por validação cruzada...")
    dataset = construir_dataset()
    modelo, scaler, mediana, metricas = treinar_modelo(dataset)

    modelo_treinado.salvar(modelo, scaler, mediana)
    log_treinos.registrar(metricas, mes_ref_treino=dataset["mes_ref"].max())

    print(f"  AUC = {metricas['auc']:.3f} | Brier = {metricas['brier']:.3f} | "
          f"{metricas['n_amostras']} amostras ({metricas['n_positivos']} positivas)")

    print("\nRecalculando histórico completo (fScoreRisco) com o modelo treinado...")
    for mes, qtd in recalcular_historico_completo().items():
        print(f"  {mes}: {qtd} clientes")


if __name__ == "__main__":
    main()
