"""
Infra compartilhada do score de risco de cancelamento — conexão com o SQL
Server (mesma fonte do dashboard), faixas de ação, carregamento de dados e
persistência do histórico mensal (tabela fScoreRisco).

O CÁLCULO do score em si mora em modelo_risco.py (regressão logística
treinada e validada — ver lá para a metodologia). Este módulo existia
antes como uma v1 heurística (score de pesos ponderados); foi substituída
pelo modelo treinado depois de confirmado, por validação cruzada real,
que uma regressão logística simples generaliza melhor (AUC~0.95 vs. a
v1 heurística sem essa validação formal) — ver testar_modelo_risco.py.
"""
from __future__ import annotations

import urllib.parse

import pandas as pd
from sqlalchemy import create_engine, text

SERVER = r"localhost\SQLEXPRESS"
DATABASE = "holder"

# Faixas de ação — ponto de partida, recalibrar depois que houver histórico
# real de quantos clientes em cada faixa efetivamente cancelaram.
FAIXAS = [
    (0, 30, "Saudável"),
    (30, 55, "Atenção"),
    (55, 75, "Em risco"),
    (75, 101, "Crítico"),
]


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


def _num(v):
    if v is None or v != v:  # None ou NaN
        return None
    return round(float(v), 2)


# --- Carregamento de dados (mesma fonte do dashboard) -----------------------

def carregar_dados():
    engine = _engine()
    df_cli = pd.read_sql("SELECT * FROM dClientes", engine)
    df_atd = pd.read_sql("SELECT * FROM fAtendimento", engine)
    df_sit = pd.read_sql("SELECT * FROM dSituacao", engine)
    df_nps = pd.read_sql("SELECT * FROM fPesquisa", engine)
    engine.dispose()
    return df_cli, df_atd, df_sit, df_nps


# --- Persistência do histórico mensal (SQL Server, tabela fScoreRisco) -----
# Schema estável entre versões do motor de cálculo — troca de v1 (heurística)
# pra v2 (modelo_risco.py, regressão logística) não exigiu mudar isso nem o
# painel (app.py) que consome.

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
