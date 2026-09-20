"""
Score de risco de cancelamento em duas camadas — precoce + confirmada.

NÃO é machine learning: é um score composto ponderado, auditável, cujos
pesos/faixas são calibrados por backtesting contra os cancelamentos reais
da base (ver testar_score_risco.py). Lê da mesma fonte que o dashboard
(SQL Server, banco 'holder', populado por ingestao.py) — nunca duplica os
dados em paralelo.

Arquitetura (por que duas camadas, não um score único):
- Camada PRECOCE: atraso de pagamento e chamados críticos, comparados
  contra a PRÓPRIA baseline do cliente (média móvel dos últimos 6 meses
  dele mesmo) — um cliente que sempre atrasou um pouco não deve disparar
  alerta por manter o padrão dele; o que importa é o desvio da baseline
  pessoal. São os sinais mais precoces (degradam antes dos outros).
- Camada CONFIRMADA: SLA cumprido, uso da plataforma, reclamações formais
  e classificação NPS mais recente, normalizados contra a base geral de
  clientes ATIVOS (aqui comparação cross-cliente faz sentido — são sinais
  de satisfação/entrega, não de comportamento individual). Degradam mais
  tarde, mas com mais confiança quando degradam.
- Combinação: risco_percentual = 0.35 * precoce + 0.65 * confirmada —
  pesos DEFAULT, não fixos; ajustáveis por config (ver PESO_PRECOCE/
  PESO_CONFIRMADO abaixo, não hardcoded em outro lugar do código).
"""
from __future__ import annotations

import json
import urllib.parse

import pandas as pd
from sqlalchemy import create_engine, text

SERVER = r"localhost\SQLEXPRESS"
DATABASE = "holder"

# Pesos default da combinação final — documentados aqui como ÚNICO ponto de
# configuração, não espalhados pelo código. Ajustáveis por cliente/empresa
# no futuro (mesma ideia de "prioridade configurável" do resto do
# dashboard), mas por enquanto um valor global.
PESO_PRECOCE = 0.35
PESO_CONFIRMADO = 0.65

# Faixas de ação — ponto de partida, recalibrar depois que houver histórico
# real de quantos clientes em cada faixa efetivamente cancelaram.
FAIXAS = [
    (0, 30, "Saudável"),
    (30, 55, "Atenção"),
    (55, 75, "Em risco"),
    (75, 101, "Crítico"),
]

_SINAIS_CONFIRMADO = ["pct_sla_cumprido", "uso_plataforma_pct", "reclamacoes_formais"]
_NPS_SCORE = {"Promotor": 0.0, "Neutro": 50.0, "Detrator": 100.0}


def _engine():
    params = urllib.parse.quote_plus(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"Trusted_Connection=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")


def faixa_de(risco_percentual: float) -> str:
    for lo, hi, nome in FAIXAS:
        if lo <= risco_percentual < hi:
            return nome
    return "Crítico"


def normalizar_risco(valor, p10, p90, invertido: bool = False):
    """Min-max com âncoras nos percentis 10/90 da base (evita que um outlier
    isolado sature o score) — clamped fora da faixa. Função utilitária
    única, reaproveitada por todo sinal da camada confirmada, nunca
    duplicada por sinal."""
    if valor is None or valor != valor:  # None ou NaN
        return None
    if invertido:
        valor, p10, p90 = -valor, -p10, -p90
    if p90 == p10:
        return 0.0
    score = (valor - p10) / (p90 - p10) * 100
    return max(0.0, min(100.0, score))


# --- Carregamento de dados (mesma fonte do dashboard) -----------------------

def carregar_dados():
    engine = _engine()
    df_cli = pd.read_sql("SELECT * FROM dClientes", engine)
    df_atd = pd.read_sql("SELECT * FROM fAtendimento", engine)
    df_sit = pd.read_sql("SELECT * FROM dSituacao", engine)
    df_nps = pd.read_sql("SELECT * FROM fPesquisa", engine)
    engine.dispose()
    return df_cli, df_atd, df_sit, df_nps


def calcular_percentis_base(df_atd: pd.DataFrame, df_sit: pd.DataFrame) -> dict:
    """p10/p90 de cada sinal da camada confirmada, sobre os meses de
    clientes ATIVOS — calculado a partir do dado real, nunca chutado. É a
    "base geral" contra a qual cada cliente é comparado na camada
    confirmada (diferente da camada precoce, que usa a baseline pessoal)."""
    ativos_ids = set(df_sit[df_sit["situacao"] == "Ativo"]["cliente_id"])
    base = df_atd[df_atd["cliente_id"].isin(ativos_ids)]
    percentis = {}
    for campo in _SINAIS_CONFIRMADO + ["chamados_criticos", "dias_atraso_pagamento"]:
        serie = base[campo].dropna()
        percentis[campo] = (float(serie.quantile(0.10)), float(serie.quantile(0.90))) if len(serie) else (0.0, 1.0)
    return percentis


# --- Cálculo do score por cliente, num mês de referência específico --------

def _desvio_baseline_pessoal(valor_atual, baseline) -> float:
    """Score 0-100 de "o quanto o valor atual piorou em relação à própria
    baseline do cliente" — só conta desvio pra PIOR (uma melhora não deve
    reduzir o score abaixo de 0, já é o próprio clamp de normalizar_risco
    que faria isso, mas aqui a métrica já nasce direcional: mais atraso /
    mais chamados críticos = sempre pior, nunca "risco negativo")."""
    if valor_atual is None or valor_atual != valor_atual:
        return 0.0
    if baseline is None or baseline != baseline:
        return 0.0
    if baseline == 0:
        return 100.0 if valor_atual > 0 else 0.0
    variacao_pct = (valor_atual - baseline) / baseline * 100
    return max(0.0, min(100.0, variacao_pct))


def calcular_score_cliente(cliente_id: str, mes_ref: str, df_atd: pd.DataFrame, df_nps: pd.DataFrame, percentis: dict) -> dict | None:
    """
    Calcula o score de risco de UM cliente NUM mês de referência —
    usa só dado até esse mês (nunca "vaza" informação do futuro), o que é
    o que permite tanto rodar em produção (mês corrente) quanto
    retroativamente (filtro por data, backtesting).
    """
    hist = df_atd[(df_atd["cliente_id"] == cliente_id) & (df_atd["mes_ref"] <= mes_ref)].sort_values("mes_ref")
    if len(hist) == 0 or hist.iloc[-1]["mes_ref"] != mes_ref:
        return None

    atual = hist.iloc[-1]
    baseline_janela = hist.iloc[:-1].tail(6)  # média móvel de 6 meses ANTERIORES ao mês atual

    # --- Camada precoce: desvio da própria baseline -------------------
    baseline_atraso = baseline_janela["dias_atraso_pagamento"].mean() if len(baseline_janela) else None
    baseline_criticos = baseline_janela["chamados_criticos"].mean() if len(baseline_janela) else None
    score_atraso = _desvio_baseline_pessoal(atual["dias_atraso_pagamento"], baseline_atraso)
    score_criticos = _desvio_baseline_pessoal(atual["chamados_criticos"], baseline_criticos)
    score_precoce = round((score_atraso + score_criticos) / 2, 2)

    # --- Camada confirmada: normalizado contra a base geral de ativos -
    s_sla = normalizar_risco(atual["pct_sla_cumprido"], *percentis["pct_sla_cumprido"], invertido=True)
    s_uso = normalizar_risco(atual["uso_plataforma_pct"], *percentis["uso_plataforma_pct"], invertido=True)
    s_rec = normalizar_risco(atual["reclamacoes_formais"], *percentis["reclamacoes_formais"])

    nps_hist = df_nps[
        (df_nps["cliente_id"] == cliente_id) & (df_nps["respondeu"] == 1) & (df_nps["mes_ref"] <= mes_ref)
    ].sort_values("mes_ref")
    classificacao_nps_recente = nps_hist.iloc[-1]["classificacao_nps"] if len(nps_hist) else None
    s_nps = _NPS_SCORE.get(classificacao_nps_recente)

    componentes_confirmado = {"sla": s_sla, "uso_plataforma": s_uso, "reclamacoes": s_rec}
    disponiveis = [v for v in componentes_confirmado.values() if v is not None]
    media_disponiveis = sum(disponiveis) / len(disponiveis) if disponiveis else 0.0
    if s_nps is None:
        # "Sem resposta recente" -> usa a média dos outros sinais da camada
        # (regra explícita do design: NPS ausente não deve arrastar o score
        # pra baixo nem virar um None que quebra a média).
        s_nps = media_disponiveis
    componentes_confirmado["nps"] = s_nps

    # Só os sinais REALMENTE disponíveis entram na média (sla/uso/reclamações
    # podem ser None num mês sem chamado algum) — nps já foi resolvido acima
    # (nunca None a essa altura, usa média dos outros quando não há pesquisa).
    valores_confirmado = disponiveis + [s_nps]
    score_confirmado = round(sum(valores_confirmado) / len(valores_confirmado), 2)

    risco_percentual = round(PESO_PRECOCE * score_precoce + PESO_CONFIRMADO * score_confirmado, 2)

    return {
        "cliente_id": cliente_id,
        "mes_ref": mes_ref,
        "score_precoce": score_precoce,
        "score_confirmado": score_confirmado,
        "risco_percentual": risco_percentual,
        "faixa": faixa_de(risco_percentual),
        "sinais_detalhados": {
            "atraso_pagamento": {"valor_atual": _num(atual["dias_atraso_pagamento"]), "baseline_pessoal": _num(baseline_atraso), "contribuicao": score_atraso},
            "chamados_criticos": {"valor_atual": _num(atual["chamados_criticos"]), "baseline_pessoal": _num(baseline_criticos), "contribuicao": score_criticos},
            "sla_cumprido": {"valor_atual": _num(atual["pct_sla_cumprido"]), "contribuicao": s_sla},
            "uso_plataforma": {"valor_atual": _num(atual["uso_plataforma_pct"]), "contribuicao": s_uso},
            "reclamacoes": {"valor_atual": _num(atual["reclamacoes_formais"]), "contribuicao": s_rec},
            "nps": {"classificacao_recente": classificacao_nps_recente, "contribuicao": round(s_nps, 2)},
        },
    }


def _num(v):
    if v is None or v != v:
        return None
    return round(float(v), 2)


def calcular_risco_todos_clientes(mes_ref: str | None = None, apenas_ativos: bool = True) -> list[dict]:
    """Score de todos os clientes num mês (default: mês mais recente
    disponível) — é o que alimenta a lista ranqueada, os cards por faixa e
    a matriz heatmap com percentual."""
    df_cli, df_atd, df_sit, df_nps = carregar_dados()
    if mes_ref is None:
        mes_ref = df_atd["mes_ref"].max()

    percentis = calcular_percentis_base(df_atd, df_sit)

    candidatos = df_atd["cliente_id"].unique().tolist()
    if apenas_ativos:
        ativos_ids = set(df_sit[df_sit["situacao"] == "Ativo"]["cliente_id"])
        candidatos = [c for c in candidatos if c in ativos_ids]

    resultados = []
    for cliente_id in candidatos:
        r = calcular_score_cliente(cliente_id, mes_ref, df_atd, df_nps, percentis)
        if r:
            resultados.append(r)

    resultados.sort(key=lambda r: r["risco_percentual"], reverse=True)
    return resultados


# --- Persistência do histórico mensal (SQL Server, tabela fScoreRisco) -----

def _garantir_tabela_historico(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fScoreRisco')
            CREATE TABLE fScoreRisco (
                cliente_id NVARCHAR(10) NOT NULL,
                mes_ref NVARCHAR(7) NOT NULL,
                score_precoce FLOAT NOT NULL,
                score_confirmado FLOAT NOT NULL,
                risco_percentual FLOAT NOT NULL,
                faixa NVARCHAR(20) NOT NULL,
                sinais_detalhados NVARCHAR(MAX) NOT NULL,
                CONSTRAINT pk_fScoreRisco PRIMARY KEY (cliente_id, mes_ref)
            )
        """))


def salvar_historico_mes(mes_ref: str | None = None, apenas_ativos: bool = False) -> int:
    """
    Job mensal: calcula o score de todo mundo num mês e salva o resultado
    histórico (upsert — apaga e reinsere as linhas desse mes_ref, idempotente
    de rodar de novo). apenas_ativos=False por padrão aqui (diferente de
    calcular_risco_todos_clientes) porque o histórico salvo é a base de
    backtesting — precisa incluir clientes que já cancelaram, calculado nos
    meses em que eles ainda tinham dado disponível.
    """
    resultados = calcular_risco_todos_clientes(mes_ref=mes_ref, apenas_ativos=apenas_ativos)
    if not resultados:
        return 0
    mes_ref_real = resultados[0]["mes_ref"]

    linhas = [
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
    ]
    df_linhas = pd.DataFrame(linhas)

    engine = _engine()
    _garantir_tabela_historico(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fScoreRisco WHERE mes_ref = :mes"), {"mes": mes_ref_real})
    df_linhas.to_sql("fScoreRisco", con=engine, if_exists="append", index=False)
    engine.dispose()
    return len(linhas)


def recalcular_historico_completo() -> dict:
    """Recalcula e salva o score de TODOS os meses disponíveis na base —
    usado uma vez pra popular o histórico completo (backtesting, linha do
    tempo, tendência) sem esperar os próximos meses acontecerem de verdade."""
    _, df_atd, _, _ = carregar_dados()
    meses = sorted(df_atd["mes_ref"].unique())
    total_por_mes = {}
    for mes in meses:
        total_por_mes[mes] = salvar_historico_mes(mes_ref=mes, apenas_ativos=False)
    return total_por_mes


def carregar_historico(cliente_id: str | None = None, mes_ref: str | None = None) -> pd.DataFrame:
    engine = _engine()
    _garantir_tabela_historico(engine)
    filtros, params = [], {}
    if cliente_id:
        filtros.append("cliente_id = :cliente_id")
        params["cliente_id"] = cliente_id
    if mes_ref:
        filtros.append("mes_ref = :mes_ref")
        params["mes_ref"] = mes_ref
    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    df = pd.read_sql(text(f"SELECT * FROM fScoreRisco {where} ORDER BY mes_ref"), engine, params=params)
    engine.dispose()
    return df


if __name__ == "__main__":
    print("Recalculando histórico completo de score de risco...")
    resumo = recalcular_historico_completo()
    for mes, qtd in resumo.items():
        print(f"  {mes}: {qtd} clientes")
    print("Concluído.")
