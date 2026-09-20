"""
Montagem do dataset de treino do score de risco.

O alvo (y) é a parte mais importante deste arquivo: para cada cliente e mês
de atendimento, **y=1 se aquele mês está dentro dos 3 meses imediatamente
anteriores ao cancelamento** daquele cliente. Meses mais antigos de clientes
cancelados, quando o comportamento ainda era normal, são **excluídos** do
treino — não viram y=0.

Isso é deliberado e é o que faz o modelo aprender "este mês parece
pré-cancelamento" em vez de "este cliente é do tipo que cancela". Rotular
todo o histórico de um cliente cancelado como positivo ensinaria o modelo a
reconhecer o cliente, não o risco.
"""
from __future__ import annotations

import pandas as pd

from holder.infra.dados.porta import fonte

FEATURES = [
    "pct_sla_cumprido", "tempo_medio_resolucao_h", "reclamacoes_formais",
    "uso_plataforma_pct", "dias_atraso_pagamento", "chamados_criticos", "nps_risco",
]

NPS_PARA_RISCO = {"Promotor": 0, "Neutro": 50, "Detrator": 100}

MESES_DA_JANELA = (1, 2, 3)


def mes_mais(mes_ref: str, n: int) -> str:
    """Desloca um `mes_ref` em n meses (n negativo anda para trás)."""
    ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
    idx = (ano * 12 + (mes - 1)) + n
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def nps_risco_ate(df_nps: pd.DataFrame, cliente_id: str, mes_ref: str) -> float:
    hist = df_nps[
        (df_nps["cliente_id"] == cliente_id)
        & (df_nps["respondeu"] == 1)
        & (df_nps["mes_ref"] <= mes_ref)
    ]
    if len(hist) == 0:
        return 50.0  # sem pesquisa ainda -> neutro default, não penaliza nem favorece
    ultima = hist.sort_values("mes_ref").iloc[-1]["classificacao_nps"]
    return float(NPS_PARA_RISCO.get(ultima, 50))


def construir_dataset(df_cli=None, df_atd=None, df_sit=None, df_nps=None) -> pd.DataFrame:
    if df_atd is None:
        df_cli, df_atd, df_sit, df_nps = fonte().carregar_tudo()

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
                dentro_da_janela = any(mes_mais(mes_canc, -k) == mes_ref for k in MESES_DA_JANELA)
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
                "nps_risco": nps_risco_ate(df_nps, cliente_id, mes_ref),
            })

    return pd.DataFrame(linhas)
