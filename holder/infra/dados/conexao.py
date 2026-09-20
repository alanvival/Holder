"""
O único lugar que sabe conectar no SQL Server.

A mesma string ODBC estava escrita três vezes — no dashboard, no score de
risco e na ingestão — e só uma das três tinha `Encrypt=no`. Essa venceu: é a
mais simples e a mais rápida, e o resultado das consultas é idêntico. A
consequência é que o dashboard passa a conectar sem negociação de TLS, o que
é mudança de comportamento de infra (assumida de propósito), não de cálculo.

A barra invertida do nome da instância não é confiável dentro da URL
`mssql+pyodbc://host/db` do SQLAlchemy (`%5C` falha com "Provedor de Pipes
Nomeados: servidor não encontrado" mesmo com o SQL Server acessível), por
isso a string crua via `odbc_connect=`.
"""
from __future__ import annotations

import urllib.parse

from sqlalchemy import create_engine

SERVER = r"localhost"
DATABASE = "holder"

DRIVER = "ODBC Driver 17 for SQL Server"


def string_odbc(database: str | None = None) -> str:
    """String de conexão ODBC. `Encrypt=no` evita a negociação de TLS que o
    driver 17 tenta por padrão antes de cair pra conexão sem criptografia —
    desnecessária numa instância local."""
    return urllib.parse.quote_plus(
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database or DATABASE};"
        f"Trusted_Connection=yes;"
        f"Encrypt=no;"
    )


def criar_engine(database: str | None = None, **kwargs):
    """Motor SQLAlchemy para o banco pedido (por padrão, `holder`).
    `kwargs` passa direto pro create_engine — a ingestão usa
    `isolation_level="AUTOCOMMIT"` pra poder executar CREATE DATABASE."""
    return create_engine(f"mssql+pyodbc:///?odbc_connect={string_odbc(database)}", **kwargs)
