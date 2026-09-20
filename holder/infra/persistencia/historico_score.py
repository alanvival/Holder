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


# O catálogo de tabelas tem nome diferente em cada banco. O dialeto vem do
# próprio engine (`engine.dialect.name`), e não da variável de ambiente, pra
# não existir duas fontes de verdade sobre onde estamos gravando.
CONSULTA_TABELA_EXISTE = {
    "mssql": "SELECT 1 FROM sys.tables WHERE name = :nome",
    "sqlite": "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :nome",
}

DDL = {
    "mssql": f"""
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
    """,
    # TEXT/REAL em vez de NVARCHAR/FLOAT: o SQLite tem afinidade de tipo, não
    # tipo declarado, então o que importa aqui é o que o pandas devolve na
    # leitura — str e float, iguais aos do SQL Server.
    "sqlite": f"""
        CREATE TABLE IF NOT EXISTS {TABELA} (
            cliente_id TEXT NOT NULL,
            mes_ref TEXT NOT NULL,
            score_precoce REAL NOT NULL,
            score_confirmado REAL NOT NULL,
            risco_percentual REAL NOT NULL,
            faixa TEXT NOT NULL,
            sinais_detalhados TEXT NOT NULL,
            PRIMARY KEY (cliente_id, mes_ref)
        )
    """,
}


def tabela_existe(engine, nome: str) -> bool:
    with engine.connect() as conn:
        return (
            conn.execute(
                text(CONSULTA_TABELA_EXISTE[engine.dialect.name]), {"nome": nome}
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
        conn.execute(text(DDL[engine.dialect.name]))


def salvar_mes(df_linhas: pd.DataFrame, mes_ref: str) -> int:
    """Substitui o histórico daquele mês: apaga e regrava. É idempotente de
    propósito — recalcular o mesmo mês duas vezes não duplica linha."""
    engine = conexao.criar_engine()
    try:
        garantir_tabela(engine)
        with engine.begin() as conn:
            conn.execute(text(f"DELETE FROM {TABELA} WHERE mes_ref = :mes"), {"mes": mes_ref})
        df_linhas.to_sql(TABELA, con=engine, if_exists="append", index=False)
        return len(df_linhas)
    finally:
        engine.dispose()


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
