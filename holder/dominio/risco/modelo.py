"""
Score de risco de cancelamento: regressão logística treinada e validada
contra os cancelamentos reais da base.

Não é um score de pesos escolhidos à mão. Referência de validação, por
validação cruzada estratificada 5-fold: **AUC ≈ 0.95, Brier ≈ 0.085** —
`testes/test_modelo_risco.py` reproduz e confere esses números toda vez que
o pipeline mudar.

Responde "em que ordem falar?". É conceito distinto do índice de alerta e
dos strikes — ver `CONTEXT.md` e
`docs/adr/0001-dois-conceitos-de-risco.md`.
"""
from __future__ import annotations

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler

from holder.infra.dados.porta import fonte
from holder.infra.persistencia import modelo_treinado

from .dataset import FEATURES, construir_dataset, nps_risco_ate
from .faixas import arredondar, faixa_de

# Sinais tratados como "precoce" na explicabilidade (desvio da baseline
# pessoal, não da base geral) — só rótulo de apresentação, o cálculo é um
# único modelo, não duas camadas.
SINAIS_PRECOCE = {"dias_atraso_pagamento", "chamados_criticos"}

# Nome de exibição de cada feature nos sinais detalhados.
NOMES_DE_EXIBICAO = {
    "pct_sla_cumprido": "sla_cumprido",
    "tempo_medio_resolucao_h": "tempo_resolucao",
    "reclamacoes_formais": "reclamacoes",
    "uso_plataforma_pct": "uso_plataforma",
    "dias_atraso_pagamento": "atraso_pagamento",
    "chamados_criticos": "chamados_criticos",
    "nps_risco": "nps",
}


def treinar_modelo(dataset: pd.DataFrame | None = None):
    """Treina + valida por validação cruzada ANTES de treinar no dataset
    completo — nunca confiar num modelo sem essa validação (é o que os
    testes automatizados conferem)."""
    if dataset is None:
        dataset = construir_dataset()

    X = dataset[FEATURES].fillna(dataset[FEATURES].median())
    y = dataset["y"]
    mediana_features = X.median()

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    modelo = LogisticRegression(max_iter=1000, class_weight="balanced")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    probas_cv = cross_val_predict(modelo, Xs, y, cv=cv, method="predict_proba")[:, 1]

    metricas = {
        "auc": float(roc_auc_score(y, probas_cv)),
        "brier": float(brier_score_loss(y, probas_cv)),
        "n_amostras": int(len(dataset)),
        "n_positivos": int((y == 1).sum()),
    }

    modelo.fit(Xs, y)  # no dataset completo, pra uso em produção
    return modelo, scaler, mediana_features, metricas


def calcular_score_cliente(cliente_id: str, mes_ref: str, df_atd: pd.DataFrame, df_nps: pd.DataFrame, modelo_pack) -> dict | None:
    """Score de um cliente num mês, com explicabilidade por sinal.

    `score_precoce`/`score_confirmado` são agrupamento de explicabilidade
    (soma das contribuições de cada grupo de sinais), não um segundo
    cálculo."""
    modelo, scaler, mediana_features = modelo_pack

    hist = df_atd[(df_atd["cliente_id"] == cliente_id) & (df_atd["mes_ref"] <= mes_ref)].sort_values("mes_ref")
    if len(hist) == 0 or hist.iloc[-1]["mes_ref"] != mes_ref:
        return None
    atual = hist.iloc[-1]
    baseline_janela = hist.iloc[:-1].tail(6)

    valores = {
        "pct_sla_cumprido": atual["pct_sla_cumprido"],
        "tempo_medio_resolucao_h": atual["tempo_medio_resolucao_h"],
        "reclamacoes_formais": atual["reclamacoes_formais"],
        "uso_plataforma_pct": atual["uso_plataforma_pct"],
        "dias_atraso_pagamento": atual["dias_atraso_pagamento"],
        "chamados_criticos": atual["chamados_criticos"],
        "nps_risco": nps_risco_ate(df_nps, cliente_id, mes_ref),
    }
    x_row = pd.DataFrame([valores])[FEATURES].fillna(mediana_features)
    xs = scaler.transform(x_row)
    probabilidade = float(modelo.predict_proba(xs)[0, 1])
    risco_percentual = round(probabilidade * 100, 2)

    # Explicabilidade: coeficiente × valor padronizado = contribuição
    # (mesma unidade do log-odds; convertida pra 0-100 só pra exibição,
    # normalizada pelo maior |contribuição| da linha).
    contribuicoes_brutas = {feat: float(modelo.coef_[0][i] * xs[0][i]) for i, feat in enumerate(FEATURES)}
    maior_abs = max((abs(v) for v in contribuicoes_brutas.values()), default=1) or 1
    contribuicoes = {k: round(abs(v) / maior_abs * 100, 1) for k, v in contribuicoes_brutas.items()}

    baseline = {
        "dias_atraso_pagamento": baseline_janela["dias_atraso_pagamento"].mean() if len(baseline_janela) else None,
        "chamados_criticos": baseline_janela["chamados_criticos"].mean() if len(baseline_janela) else None,
    }

    sinais_detalhados = {}
    for feat in FEATURES:
        chave = NOMES_DE_EXIBICAO[feat]
        entrada = {"valor_atual": arredondar(valores[feat]), "contribuicao": contribuicoes[feat]}
        if feat in baseline and baseline[feat] is not None:
            entrada["baseline_pessoal"] = round(float(baseline[feat]), 2)
        if feat == "nps_risco":
            nps_hist = df_nps[
                (df_nps["cliente_id"] == cliente_id)
                & (df_nps["respondeu"] == 1)
                & (df_nps["mes_ref"] <= mes_ref)
            ].sort_values("mes_ref")
            entrada["classificacao_recente"] = nps_hist.iloc[-1]["classificacao_nps"] if len(nps_hist) else None
        sinais_detalhados[chave] = entrada

    score_precoce = round(sum(contribuicoes[f] for f in FEATURES if f in SINAIS_PRECOCE) / len(SINAIS_PRECOCE), 2)
    score_confirmado = round(
        sum(contribuicoes[f] for f in FEATURES if f not in SINAIS_PRECOCE) / (len(FEATURES) - len(SINAIS_PRECOCE)),
        2,
    )

    return {
        "cliente_id": cliente_id,
        "mes_ref": mes_ref,
        "score_precoce": score_precoce,
        "score_confirmado": score_confirmado,
        "risco_percentual": risco_percentual,
        "faixa": faixa_de(risco_percentual),
        "sinais_detalhados": sinais_detalhados,
    }


def calcular_risco_todos_clientes(mes_ref: str | None = None, apenas_ativos: bool = True) -> list[dict]:
    df_cli, df_atd, df_sit, df_nps = fonte().carregar_tudo()
    if mes_ref is None:
        mes_ref = df_atd["mes_ref"].max()

    modelo_pack = modelo_treinado.carregar()

    candidatos = df_atd["cliente_id"].unique().tolist()
    if apenas_ativos:
        ativos_ids = set(df_sit[df_sit["situacao"] == "Ativo"]["cliente_id"])
        candidatos = [c for c in candidatos if c in ativos_ids]

    resultados = []
    for cliente_id in candidatos:
        r = calcular_score_cliente(cliente_id, mes_ref, df_atd, df_nps, modelo_pack)
        if r:
            resultados.append(r)

    resultados.sort(key=lambda r: r["risco_percentual"], reverse=True)
    return resultados
