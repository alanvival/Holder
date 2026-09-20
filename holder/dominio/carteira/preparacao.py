"""
Preparação da carteira para o dashboard.

Produz os nove objetos que alimentam todos os gráficos das três abas:
tabelas base, matriz de valor × risco (RFV), linhas de corte dos
cancelados, assinatura de churn, painel de strikes e taxa de disparo.

Estava dentro de `app.py`, como uma função de 120 linhas decorada com
`@st.cache_data`. O cálculo saiu; o cache continua no dashboard, porque é
detalhe do Streamlit, não regra de negócio. O ganho é poder chamar isto sem
subir uma interface.
"""
from __future__ import annotations

import pandas as pd

from holder.infra.dados.porta import fonte

from ..strikes.nps_recente import ultima_classificacao_por_cliente
from ..strikes.recencia import meses_recentes

# Abaixo disso, o mês conta como quebra de SLA para a contagem de meses
# ruins do cliente.
LIMITE_QUEBRA_SLA = 80.0

# Linhas de corte que são contagens esparsas: média, não mediana (a mediana
# de uma coluna quase toda zero seria zero, e não separaria nada).
COLUNAS_POR_MEDIA = ["reclamacoes_formais", "reunioes_ausentes"]

COLUNAS_STRIKES = [
    "Strike 1 (SLA Crítico Atual)",
    "Strike 2 (Lentidão Atual)",
    "Strike 3 (Reclamação Recente)",
    "Strike 4 (Último NPS Detrator)",
]


def _categorizar_saude(row) -> str:
    if row["V_Score"] >= 4 and row["R_Score"] <= 2:
        return "Ação Imediata"
    if row["V_Score"] >= 4 and row["R_Score"] >= 3:
        return "Proteger e Expandir"
    if row["V_Score"] <= 3 and row["R_Score"] <= 2:
        return "Avaliar Fit"
    return "Fluxo Normal"


def calcular_rfv(df_cli, df_atd, df_sit, meses: int | None = None):
    """Matriz de valor × risco (RFV) dos clientes ativos — usada pela Matriz
    Estratégica. `meses` restringe o histórico de atendimento considerado
    aos N meses mais recentes (campo de período da aba); None usa a base
    inteira (comportamento de sempre). Só filtra a base de ATIVOS — nunca
    aplicar isso ao cálculo das linhas de corte tiradas de quem já
    cancelou, que fica em `preparar` e ignora esse período de propósito."""
    df_atd = df_atd.copy()
    if "mes_ref_dt" not in df_atd.columns:
        df_atd["mes_ref_dt"] = pd.to_datetime(df_atd["mes_ref"], format="%Y-%m")

    df_master = df_cli.merge(df_sit, on="cliente_id", how="inner")
    df_ativos = df_master[df_master["situacao"] == "Ativo"].copy()

    df_atd_ativos = df_atd[df_atd["cliente_id"].isin(df_ativos["cliente_id"])].copy()
    df_atd_ativos["quebra_sla"] = df_atd_ativos["pct_sla_cumprido"] < LIMITE_QUEBRA_SLA

    if meses is not None:
        limite = df_atd_ativos["mes_ref_dt"].max() - pd.DateOffset(months=meses)
        df_atd_ativos = df_atd_ativos[df_atd_ativos["mes_ref_dt"] > limite]

    agrupamento = df_atd_ativos.groupby("cliente_id").agg(
        meses_abaixo_sla=("quebra_sla", "sum"),
        total_reclamacoes=("reclamacoes_formais", "sum"),
        uso_medio=("uso_plataforma_pct", "mean"),
    ).reset_index()

    df_rfv = df_ativos[["cliente_id", "valor_mensal", "segmento"]].merge(
        agrupamento, on="cliente_id", how="left"
    )
    df_rfv["V_Score"] = pd.qcut(df_rfv["valor_mensal"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df_rfv["Fator_Risco"] = df_rfv["meses_abaixo_sla"] + df_rfv["total_reclamacoes"]
    df_rfv["R_Rank"] = df_rfv["Fator_Risco"].rank(method="first", ascending=False)
    df_rfv["R_Score"] = pd.qcut(df_rfv["R_Rank"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df_rfv["Categoria_Saude"] = df_rfv.apply(_categorizar_saude, axis=1)
    return df_rfv


def preparar(df_cli, df_atd, df_sit, df_nps):
    """Recebe as quatro tabelas e devolve os nove objetos do dashboard."""
    df_atd = df_atd.copy()
    df_nps = df_nps.copy()

    df_atd["mes_ref_dt"] = pd.to_datetime(df_atd["mes_ref"], format="%Y-%m")
    df_nps["mes_ref_dt"] = pd.to_datetime(df_nps["mes_ref"], format="%Y-%m")

    # Reuniões ausentes: o que foi previsto e não aconteceu.
    df_atd["reunioes_ausentes"] = df_atd["reunioes_previstas"] - df_atd["reunioes_realizadas"]
    df_atd = df_atd.drop(columns=["reunioes_previstas", "reunioes_realizadas"])

    df_atd = df_atd.merge(
        df_sit[["cliente_id", "situacao", "mes_cancelamento"]], on="cliente_id", how="left"
    )

    df_master = df_cli.merge(df_sit, on="cliente_id", how="inner")
    df_ativos = df_master[df_master["situacao"] == "Ativo"].copy()
    df_cancelados = df_master[df_master["situacao"] == "Cancelado"].copy()

    df_atd_ativos = df_atd[df_atd["cliente_id"].isin(df_ativos["cliente_id"])].copy()
    df_atd_ativos["quebra_sla"] = df_atd_ativos["pct_sla_cumprido"] < LIMITE_QUEBRA_SLA

    # RFV da base inteira (sem filtro de período) — é o que as abas Monitor
    # Individual e Score de Risco usam. A Matriz Estratégica recalcula a
    # dela com o período escolhido via `calcular_rfv`, direto no dashboard.
    df_rfv = calcular_rfv(df_cli, df_atd, df_sit, meses=None)

    # --- Linhas de corte, tiradas de quem já cancelou ---------------------
    df_atd_canc = df_atd[df_atd["situacao"] == "Cancelado"].copy()
    colunas_excluidas = ["cliente_id", "mes_ref", "mes_ref_dt", "mes_cancelamento"]
    colunas_numericas = [
        col for col in df_atd.select_dtypes(include="number").columns
        if col not in colunas_excluidas
    ]

    linhas_risco = {}
    for col in colunas_numericas:
        if col in COLUNAS_POR_MEDIA:
            linhas_risco[col] = df_atd_canc[col].mean()
        else:
            linhas_risco[col] = df_atd_canc[col].median()

    # --- Assinatura de churn: quantos dos que saíram batiam cada sinal ----
    df_atd_canc["mes_canc_dt"] = pd.to_datetime(df_atd_canc["mes_cancelamento"], format="%Y-%m")
    df_atd_canc["meses_para_canc"] = (
        (df_atd_canc["mes_canc_dt"].dt.year - df_atd_canc["mes_ref_dt"].dt.year) * 12
        + (df_atd_canc["mes_canc_dt"].dt.month - df_atd_canc["mes_ref_dt"].dt.month)
    )
    ultimos_meses_canc = df_atd_canc[
        (df_atd_canc["meses_para_canc"] > 0) & (df_atd_canc["meses_para_canc"] <= 4)
    ]

    total_canc = len(df_cancelados)
    pct_canc_sla = len(ultimos_meses_canc[
        ultimos_meses_canc["pct_sla_cumprido"] <= linhas_risco.get("pct_sla_cumprido", LIMITE_QUEBRA_SLA)
    ]["cliente_id"].unique()) / total_canc if total_canc > 0 else 0
    pct_canc_rec = len(ultimos_meses_canc[
        ultimos_meses_canc["reclamacoes_formais"] > 0
    ]["cliente_id"].unique()) / total_canc if total_canc > 0 else 0

    df_nps_canc = df_nps.merge(
        df_sit[["cliente_id", "situacao", "mes_cancelamento"]], on="cliente_id", how="inner"
    )
    df_nps_canc = df_nps_canc[df_nps_canc["situacao"] == "Cancelado"]
    df_nps_canc["mes_canc_dt"] = pd.to_datetime(df_nps_canc["mes_cancelamento"], format="%Y-%m")
    df_nps_canc["meses_para_canc"] = (
        (df_nps_canc["mes_canc_dt"].dt.year - df_nps_canc["mes_ref_dt"].dt.year) * 12
        + (df_nps_canc["mes_canc_dt"].dt.month - df_nps_canc["mes_ref_dt"].dt.month)
    )
    ultimos_meses_nps = df_nps_canc[
        (df_nps_canc["meses_para_canc"] > 0) & (df_nps_canc["meses_para_canc"] <= 6)
    ]
    pct_canc_detrator = len(ultimos_meses_nps[
        ultimos_meses_nps["classificacao_nps"] == "Detrator"
    ]["cliente_id"].unique()) / total_canc if total_canc > 0 else 0

    padroes_churn = {"SLA": pct_canc_sla, "Reclamacao": pct_canc_rec, "NPS": pct_canc_detrator}

    # --- Painel de strikes ------------------------------------------------
    df_atd_ativos = df_atd_ativos.sort_values(by=["cliente_id", "mes_ref_dt"])
    df_nps_ativos = df_nps[
        df_nps["cliente_id"].isin(df_ativos["cliente_id"])
    ].sort_values(by=["cliente_id", "mes_ref_dt"])

    ultimo_atd = df_atd_ativos.groupby("cliente_id").tail(1).set_index("cliente_id")

    # Última classificação de NPS pela regra única do domínio: a pesquisa
    # mais recente RESPONDIDA. Aqui era a última linha da tabela, sem
    # filtrar `respondeu` — o que perdia o strike de quem foi detrator e
    # depois ignorou o convite seguinte (3 clientes nesta base).
    ultimo_nps = ultima_classificacao_por_cliente(df_nps_ativos)

    # Janela de recência unificada com o motor do assistente: os dois
    # últimos meses COM MEDIÇÃO, não o mês corrente e o anterior pelo
    # calendário. Aqui era `mes_ref_dt >= max - DateOffset(months=1)`, o que
    # escondia em silêncio o strike de um cliente sem registro no mês mais
    # recente da base. Ver holder/dominio/strikes/recencia.py.
    janela = meses_recentes(df_atd_ativos)
    reclamacoes_recentes = (
        df_atd_ativos[df_atd_ativos["mes_ref"].isin(janela)]
        .groupby("cliente_id")["reclamacoes_formais"].sum()
    )

    strikes = pd.DataFrame(index=df_ativos["cliente_id"])
    strikes[COLUNAS_STRIKES[0]] = (
        ultimo_atd["pct_sla_cumprido"] <= linhas_risco.get("pct_sla_cumprido", LIMITE_QUEBRA_SLA)
    ).astype(int)
    strikes[COLUNAS_STRIKES[1]] = (
        ultimo_atd["tempo_medio_resolucao_h"] >= linhas_risco.get("tempo_medio_resolucao_h", 24.0)
    ).astype(int)
    strikes[COLUNAS_STRIKES[2]] = (reclamacoes_recentes > 0).astype(int).reindex(strikes.index).fillna(0)
    strikes[COLUNAS_STRIKES[3]] = (
        ultimo_nps == "Detrator"
    ).astype(int).reindex(strikes.index).fillna(0)

    strikes["Total_Strikes"] = strikes[COLUNAS_STRIKES].sum(axis=1)

    # Taxa de disparo de cada sinal sobre todos os ativos — sinal que
    # dispara pra quase todo mundo é fraco isoladamente.
    taxa_falso_alarme = {
        "SLA": strikes[COLUNAS_STRIKES[0]].mean(),
        "Reclamacao": strikes[COLUNAS_STRIKES[2]].mean(),
        "NPS": strikes[COLUNAS_STRIKES[3]].mean(),
    }

    return df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco, padroes_churn, strikes, taxa_falso_alarme


def carregar_e_preparar():
    """Lê pela porta de dados e prepara. É o que o dashboard chama."""
    return preparar(*fonte().carregar_tudo())
