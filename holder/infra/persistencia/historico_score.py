"""
Persistência do histórico mensal do score de risco (tabela `fScoreRisco` no
SQL Server).

O schema é estável entre versões do motor de cálculo: a troca da heurística
inicial pelo modelo treinado não exigiu mudar nem esta tabela nem o painel
que a consome.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from ..dados import conexao

TABELA = "fScoreRisco"


def tabela_existe(engine, nome: str) -> bool:
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT 1 FROM sys.tables WHERE name = :nome"), {"nome": nome}
            ).fetchone()
            is not None
        )


def garantir_tabela(engine) -> None:
    # Só tenta o CREATE TABLE (que precisa de um lock de schema, mesmo com
    # IF NOT EXISTS) quando a tabela realmente não existe ainda — checar
    # primeiro com uma leitura simples evita que múltiplos processos rodando
    # ao mesmo tempo (o Streamlit + um script de terminal, por exemplo)
    # fiquem serializados esperando esse lock a cada leitura, depois que a
    # tabela já foi criada uma vez. Era a causa real do "Running..." que
    # travava por 10-60s: não era lentidão de conexão, era contenção de lock
    # entre processos concorrentes.
    if tabela_existe(engine, TABELA):
        return
    with engine.begin() as conn:
        conn.execute(text(f"""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '{TABELA}')
            CREATE TABLE {TABELA} (
                cliente_id NVARCHAR(10) NOT NULL,
                mes_ref NVARCHAR(7) NOT NULL,
                score_precoce FLOAT NOT NULL,
                score_confirmado FLOAT NOT NULL,
                risco_percentual FLOAT NOT NULL,
                faixa NVARCHAR(20) NOT NULL,
                sinais_detalhados NVARCHAR(MAX) NOT NULL,
                CONSTRAINT pk_{TABELA} PRIMARY KEY (cliente_id, mes_ref)
            )
        """))


def carregar_historico(cliente_id: str | None = None, mes_ref: str | None = None) -> pd.DataFrame:
    engine = conexao.criar_engine()
    try:
        garantir_tabela(engine)
        filtros, params = [], {}
        if cliente_id:
            filtros.append("cliente_id = :cliente_id")
            params["cliente_id"] = cliente_id
        if mes_ref:
            filtros.append("mes_ref = :mes_ref")
            params["mes_ref"] = mes_ref
        where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        return pd.read_sql(
            text(f"SELECT * FROM {TABELA} {where} ORDER BY mes_ref"), engine, params=params
        )
    finally:
        engine.dispose()
