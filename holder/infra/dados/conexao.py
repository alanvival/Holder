"""
O único lugar que sabe conectar no banco.

A mesma string ODBC estava escrita três vezes — no dashboard, no score de
risco e na ingestão — e só uma das três tinha `Encrypt=no`. Essa venceu: é a
mais simples e a mais rápida, e o resultado das consultas é idêntico. A
consequência é que o dashboard passa a conectar sem negociação de TLS, o que
é mudança de comportamento de infra (assumida de propósito), não de cálculo.

A barra invertida do nome da instância não é confiável dentro da URL
`mssql+pyodbc://host/db` do SQLAlchemy (`%5C` falha com "Provedor de Pipes
Nomeados: servidor não encontrado" mesmo com o SQL Server acessível), por
isso a string crua via `odbc_connect=`.

Desde o deploy, há um segundo destino: SQLite num arquivo. Ele existe porque
o adaptador de planilha (ADR 0002) resolve a leitura da carteira sem banco,
mas não resolve `fScoreRisco` nem `fModeloRiscoLog` — essas só existem como
tabela, e sem elas a aba "Score de Risco" não sobe. O SQL Server continua
sendo o padrão: quem roda local não configura nada e não vê diferença.
Ver `docs/adr/0004-sqlite-como-destino-de-deploy.md`.
"""
from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

from sqlalchemy import create_engine

SERVER = "localhost"
DATABASE = "holder"

DRIVER = "ODBC Driver 17 for SQL Server"

# Nome do banco de destino. `sqlserver` é o padrão porque é onde a ingestão
# local grava e de onde o dashboard lê em desenvolvimento; `sqlite` é o que
# o deploy usa, lendo o arquivo versionado em `dados/`.
VARIAVEL_DE_AMBIENTE = "HOLDER_BANCO"
PADRAO = "sqlserver"

RAIZ = Path(__file__).resolve().parents[3]
ARQUIVO_SQLITE = RAIZ / "dados" / "holder.sqlite3"


def dialeto(nome: str | None = None) -> str:
    """Qual banco usar — por argumento, por variável de ambiente
    (`HOLDER_BANCO`) ou o padrão. Nome desconhecido estoura em vez de cair
    num default silencioso, mesmo contrato de `porta.fonte()`."""
    escolhido = (nome or os.environ.get(VARIAVEL_DE_AMBIENTE) or PADRAO).lower()
    if escolhido not in ("sqlserver", "sqlite"):
        raise ValueError(f"Banco desconhecido: {escolhido!r}. Use 'sqlserver' ou 'sqlite'.")
    return escolhido


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
    `isolation_level="AUTOCOMMIT"` pra poder executar CREATE DATABASE.

    No SQLite, `database` é ignorado: não existe instância com vários bancos,
    existe um arquivo só. A ingestão pede o `master` pra criar o banco, e lá
    esse passo simplesmente não se aplica."""
    if dialeto() == "sqlite":
        ARQUIVO_SQLITE.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite:///{ARQUIVO_SQLITE}", **kwargs)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={string_odbc(database)}", **kwargs)
