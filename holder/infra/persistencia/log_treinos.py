"""
Log de treinos do modelo (tabela `fModeloRiscoLog` no SQL Server).

Uma linha por treino, com AUC, Brier e tamanho da amostra. É o que a seção
de metodologia do dashboard mostra — a prova de que o número exibido na tela
veio de um modelo validado, e não de pesos escolhidos à mão.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from ..dados import conexao

TABELA = "fModeloRiscoLog"

COLUNAS = ["treinado_em", "mes_ref_treino", "auc", "brier", "n_amostras", "n_positivos"]


def registrar(metricas: dict, mes_ref_treino: str | None = None) -> None:
    engine = conexao.criar_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text(f"""
                IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '{TABELA}')
                CREATE TABLE {TABELA} (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    treinado_em DATETIME2 DEFAULT SYSDATETIME(),
                    mes_ref_treino NVARCHAR(7) NULL,
                    auc FLOAT NOT NULL,
                    brier FLOAT NOT NULL,
                    n_amostras INT NOT NULL,
                    n_positivos INT NOT NULL
                )
            """))
            conn.execute(text(f"""
                INSERT INTO {TABELA} (mes_ref_treino, auc, brier, n_amostras, n_positivos)
                VALUES (:mes, :auc, :brier, :n, :npos)
            """), {
                "mes": mes_ref_treino,
                "auc": metricas["auc"],
                "brier": metricas["brier"],
                "n": metricas["n_amostras"],
                "npos": metricas["n_positivos"],
            })
    finally:
        engine.dispose()


def carregar() -> pd.DataFrame:
    """Devolve DataFrame vazio (com as colunas certas) se a tabela ainda não
    existe — o painel de metodologia precisa renderizar antes do primeiro
    treino."""
    engine = conexao.criar_engine()
    try:
        return pd.read_sql(f"SELECT * FROM {TABELA} ORDER BY treinado_em DESC", engine)
    except Exception:
        return pd.DataFrame(columns=COLUNAS)
    finally:
        engine.dispose()
