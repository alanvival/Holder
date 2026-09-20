"""
O único lugar que sabe conectar no SQL Server.

A mesma string ODBC estava escrita três vezes — no dashboard, no score de
risco e na ingestão — e só uma das três tinha `Encrypt=no`. Essa venceu: é
a mais simples e a mais rápida, e o resultado das consultas é idêntico. A
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

SERVER = "localhost"
DATABASE = "holder"

DRIVER = "ODBC Driver 17 for SQL Server"

# Login SQL do Jenkins (CI) — mantido como credencial PRIMÁRIA de propósito
# (é o que o pipeline usa). Numa máquina de dev onde esse login SQL não
# existe (só autenticação do Windows configurada), `criar_engine` cai pra
# Trusted_Connection sozinho — ver `_TENTATIVAS_AUTH` abaixo.
USERNAME = "holder_jenkins"
PASSWORD = "Holder@123456"


def _string_odbc_base(database: str | None) -> str:
    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database or DATABASE};"
        f"Encrypt=no;"
    )


def string_odbc(database: str | None = None) -> str:
    """String de conexão ODBC com o login SQL do Jenkins. `Encrypt=no` evita
    a negociação de TLS que o driver 17 tenta por padrão antes de cair pra
    conexão sem criptografia — desnecessária numa instância local."""
    return urllib.parse.quote_plus(
        f"{_string_odbc_base(database)}UID={USERNAME};PWD={PASSWORD};"
    )


def _string_odbc_trusted(database: str | None = None) -> str:
    """Mesma string, mas com autenticação do Windows — fallback pra quando
    o login SQL do Jenkins não existe na instância (comum em máquina de dev,
    que normalmente só tem o usuário Windows configurado como admin do
    SQL Server)."""
    return urllib.parse.quote_plus(f"{_string_odbc_base(database)}Trusted_Connection=yes;")


def criar_engine(database: str | None = None, **kwargs):
    """Motor SQLAlchemy para o banco pedido (por padrão, `holder`).
    `kwargs` passa direto pro create_engine — a ingestão usa
    `isolation_level="AUTOCOMMIT"` pra poder executar CREATE DATABASE.

    Tenta o login SQL do Jenkins primeiro (credencial de CI, sempre a
    preferida); se a conexão falhar — login inválido, usuário inexistente
    nesta instância etc. — cai pra autenticação do Windows automaticamente,
    sem precisar de nenhum ajuste manual por máquina. Um erro de rede/
    timeout genuíno (SQL Server fora do ar) falha nas duas tentativas e
    sobe a exceção real da segunda, que é a mais informativa nesse caso.
    """
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={string_odbc(database)}", **kwargs)
    try:
        with engine.connect():
            pass
        return engine
    except Exception:
        engine.dispose()
        return create_engine(
            f"mssql+pyodbc:///?odbc_connect={_string_odbc_trusted(database)}", **kwargs
        )
