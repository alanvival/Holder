"""
Modelo de risco de cancelamento — regressão logística treinada e validada
contra os cancelamentos reais da base, não um score de pesos escolhidos à
mão (substitui a v1 heurística de score_risco.py, que fica só com a infra
compartilhada: conexão, faixas, persistência do histórico).

Validado por validação cruzada estratificada 5-fold: AUC ≈ 0.95,
Brier ≈ 0.085 (ver testar_modelo_risco.py — reproduz e confere esses
números toda vez que o pipeline mudar).

Alvo do treino (y): pra cada cliente_id + mes_ref de atendimento_mensal,
y=1 se esse mês está dentro dos 3 meses imediatamente antes do
cancelamento daquele cliente; meses mais antigos de clientes cancelados
(fora dessa janela, quando o comportamento ainda era normal) são
EXCLUÍDOS do treino, não viram y=0 — o modelo aprende "esse mês parece
pré-cancelamento", não "esse cliente é do tipo que cancela".
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

import score_risco as sr  # infra compartilhada: engine, faixa_de, histórico

FEATURES = [
    "pct_sla_cumprido", "tempo_medio_resolucao_h", "reclamacoes_formais",
    "uso_plataforma_pct", "dias_atraso_pagamento", "chamados_criticos", "nps_risco",
]
_NPS_MAP = {"Promotor": 0, "Neutro": 50, "Detrator": 100}

_ARQUIVO_MODELO = Path(__file__).resolve().parent / "modelo_risco.pkl"

# Sinais tratados como "precoce" na explicabilidade (mesma lógica da v1
# heurística: desvio da baseline pessoal, não da base geral) — só rótulo
# de apresentação agora, o cálculo é um único modelo, não duas camadas.
_SINAIS_PRECOCE = {"dias_atraso_pagamento", "chamados_criticos"}


def _mes_mais(mes_ref: str, n: int) -> str:
    ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
    idx = (ano * 12 + (mes - 1)) + n
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def _nps_risco_ate(df_nps: pd.DataFrame, cliente_id: str, mes_ref: str) -> float:
    hist = df_nps[(df_nps["cliente_id"] == cliente_id) & (df_nps["respondeu"] == 1) & (df_nps["mes_ref"] <= mes_ref)]
    if len(hist) == 0:
        return 50.0  # sem pesquisa ainda -> neutro default, não penaliza nem favorece
    ultima = hist.sort_values("mes_ref").iloc[-1]["classificacao_nps"]
    return float(_NPS_MAP.get(ultima, 50))


def construir_dataset(df_cli=None, df_atd=None, df_sit=None, df_nps=None) -> pd.DataFrame:
    if df_atd is None:
        df_cli, df_atd, df_sit, df_nps = sr.carregar_dados()

    cancelados = dict(zip(
        df_sit[df_sit["situacao"] == "Cancelado"]["cliente_id"],
        df_sit[df_sit["situacao"] == "Cancelado"]["mes_cancelamento"],
    ))

    linhas = []
    for cliente_id, grupo in df_atd.groupby("cliente_id"):
        mes_canc = cancelados.get(cliente_id)
        for _, row in grupo.iterrows():
            mes_ref = row["mes_ref"]
            if mes_canc:
                dentro_da_janela = any(_mes_mais(mes_canc, -k) == mes_ref for k in (1, 2, 3))
                if not dentro_da_janela:
                    continue  # fora da janela de 3 meses -> excluído, não é y=0
                y = 1
            else:
                y = 0

            linhas.append({
                "cliente_id": cliente_id, "mes_ref": mes_ref, "y": y,
                "pct_sla_cumprido": row["pct_sla_cumprido"],
                "tempo_medio_resolucao_h": row["tempo_medio_resolucao_h"],
                "reclamacoes_formais": row["reclamacoes_formais"],
                "uso_plataforma_pct": row["uso_plataforma_pct"],
                "dias_atraso_pagamento": row["dias_atraso_pagamento"],
                "chamados_criticos": row["chamados_criticos"],
                "nps_risco": _nps_risco_ate(df_nps, cliente_id, mes_ref),
            })

    return pd.DataFrame(linhas)


def treinar_modelo(dataset: pd.DataFrame | None = None):
    """Treina + valida por cross-validation ANTES de treinar no dataset
    completo — nunca confiar num modelo sem essa validação (é o que os
    testes automatizados de testar_modelo_risco.py conferem)."""
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


def salvar_modelo(modelo, scaler, mediana_features, metricas, mes_ref_treino: str | None = None):
    with open(_ARQUIVO_MODELO, "wb") as f:
        pickle.dump({"modelo": modelo, "scaler": scaler, "mediana_features": mediana_features}, f)

    engine = sr._engine()
    with engine.begin() as conn:
        conn.execute(text("""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fModeloRiscoLog')
            CREATE TABLE fModeloRiscoLog (
                id INT IDENTITY(1,1) PRIMARY KEY,
                treinado_em DATETIME2 DEFAULT SYSDATETIME(),
                mes_ref_treino NVARCHAR(7) NULL,
                auc FLOAT NOT NULL,
                brier FLOAT NOT NULL,
                n_amostras INT NOT NULL,
                n_positivos INT NOT NULL
            )
        """))
        conn.execute(text("""
            INSERT INTO fModeloRiscoLog (mes_ref_treino, auc, brier, n_amostras, n_positivos)
            VALUES (:mes, :auc, :brier, :n, :npos)
        """), {"mes": mes_ref_treino, "auc": metricas["auc"], "brier": metricas["brier"],
               "n": metricas["n_amostras"], "npos": metricas["n_positivos"]})
    engine.dispose()


def carregar_modelo():
    if not _ARQUIVO_MODELO.exists():
        modelo, scaler, mediana, metricas = treinar_modelo()
        salvar_modelo(modelo, scaler, mediana, metricas)
        return modelo, scaler, mediana
    with open(_ARQUIVO_MODELO, "rb") as f:
        d = pickle.load(f)
    return d["modelo"], d["scaler"], d["mediana_features"]


def carregar_log_treinos() -> pd.DataFrame:
    engine = sr._engine()
    try:
        df = pd.read_sql("SELECT * FROM fModeloRiscoLog ORDER BY treinado_em DESC", engine)
    except Exception:
        df = pd.DataFrame(columns=["treinado_em", "mes_ref_treino", "auc", "brier", "n_amostras", "n_positivos"])
    engine.dispose()
    return df


# --- Predição por cliente, com explicabilidade -----------------------------

def calcular_score_cliente(cliente_id: str, mes_ref: str, df_atd: pd.DataFrame, df_nps: pd.DataFrame, modelo_pack) -> dict | None:
    """Mesmo formato de retorno da v1 heurística (score_risco.py) — o resto
    do painel (app.py) não precisa mudar nada pra consumir o modelo novo.
    score_precoce/score_confirmado viram só agrupamento de explicabilidade
    (soma |contribuição| dos sinais de cada grupo), não outro cálculo."""
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
        "nps_risco": _nps_risco_ate(df_nps, cliente_id, mes_ref),
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

    nomes = {
        "pct_sla_cumprido": "sla_cumprido", "tempo_medio_resolucao_h": "tempo_resolucao",
        "reclamacoes_formais": "reclamacoes", "uso_plataforma": "uso_plataforma",
        "uso_plataforma_pct": "uso_plataforma", "dias_atraso_pagamento": "atraso_pagamento",
        "chamados_criticos": "chamados_criticos", "nps_risco": "nps",
    }
    sinais_detalhados = {}
    for feat in FEATURES:
        chave = nomes[feat]
        entrada = {"valor_atual": sr._num(valores[feat]) if hasattr(sr, "_num") else round(float(valores[feat]), 2), "contribuicao": contribuicoes[feat]}
        if feat in baseline and baseline[feat] is not None:
            entrada["baseline_pessoal"] = round(float(baseline[feat]), 2)
        if feat == "nps_risco":
            nps_hist = df_nps[(df_nps["cliente_id"] == cliente_id) & (df_nps["respondeu"] == 1) & (df_nps["mes_ref"] <= mes_ref)].sort_values("mes_ref")
            entrada["classificacao_recente"] = nps_hist.iloc[-1]["classificacao_nps"] if len(nps_hist) else None
        sinais_detalhados[chave] = entrada

    score_precoce = round(sum(contribuicoes[f] for f in FEATURES if f in _SINAIS_PRECOCE) / 2, 2)
    score_confirmado = round(sum(contribuicoes[f] for f in FEATURES if f not in _SINAIS_PRECOCE) / (len(FEATURES) - len(_SINAIS_PRECOCE)), 2)

    return {
        "cliente_id": cliente_id,
        "mes_ref": mes_ref,
        "score_precoce": score_precoce,
        "score_confirmado": score_confirmado,
        "risco_percentual": risco_percentual,
        "faixa": sr.faixa_de(risco_percentual),
        "sinais_detalhados": sinais_detalhados,
    }


def calcular_risco_todos_clientes(mes_ref: str | None = None, apenas_ativos: bool = True) -> list[dict]:
    df_cli, df_atd, df_sit, df_nps = sr.carregar_dados()
    if mes_ref is None:
        mes_ref = df_atd["mes_ref"].max()

    modelo_pack = carregar_modelo()

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


def salvar_historico_mes(mes_ref: str | None = None, apenas_ativos: bool = False) -> int:
    """Mesma tabela fScoreRisco da v1 (schema idêntico) — só troca QUEM
    calcula o número (modelo em vez de heurística)."""
    resultados = calcular_risco_todos_clientes(mes_ref=mes_ref, apenas_ativos=apenas_ativos)
    if not resultados:
        return 0
    mes_ref_real = resultados[0]["mes_ref"]

    linhas = [
        {
            "cliente_id": r["cliente_id"], "mes_ref": r["mes_ref"],
            "score_precoce": r["score_precoce"], "score_confirmado": r["score_confirmado"],
            "risco_percentual": r["risco_percentual"], "faixa": r["faixa"],
            "sinais_detalhados": json.dumps(r["sinais_detalhados"], ensure_ascii=False),
        }
        for r in resultados
    ]
    df_linhas = pd.DataFrame(linhas)

    engine = sr._engine()
    sr._garantir_tabela_historico(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fScoreRisco WHERE mes_ref = :mes"), {"mes": mes_ref_real})
    df_linhas.to_sql("fScoreRisco", con=engine, if_exists="append", index=False)
    engine.dispose()
    return len(linhas)


def recalcular_historico_completo() -> dict:
    _, df_atd, _, _ = sr.carregar_dados()
    meses = sorted(df_atd["mes_ref"].unique())
    total_por_mes = {}
    for mes in meses:
        total_por_mes[mes] = salvar_historico_mes(mes_ref=mes, apenas_ativos=False)
    return total_por_mes


if __name__ == "__main__":
    print("Treinando modelo (regressão logística) e validando por cross-validation...")
    dataset = construir_dataset()
    modelo, scaler, mediana, metricas = treinar_modelo(dataset)
    mes_treino = dataset["mes_ref"].max()
    salvar_modelo(modelo, scaler, mediana, metricas, mes_ref_treino=mes_treino)
    print(f"  AUC = {metricas['auc']:.3f} | Brier = {metricas['brier']:.3f} | "
          f"{metricas['n_amostras']} amostras ({metricas['n_positivos']} positivas)")

    print("\nRecalculando histórico completo (fScoreRisco) com o modelo treinado...")
    resumo = recalcular_historico_completo()
    for mes, qtd in resumo.items():
        print(f"  {mes}: {qtd} clientes")
    print("Concluído.")
