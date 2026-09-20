"""
A porta de leitura da carteira.

As quatro tabelas do domínio — clientes, atendimento mensal, situação e
pesquisas de NPS — sempre com os mesmos nomes, independentemente de onde
vieram. Existem dois adaptadores e eles coexistem de propósito: ver
`docs/adr/0002-porta-de-dados-com-dois-adaptadores.md`. Em resumo: o modelo
dimensional no SQL Server é narrativa técnica que vale manter de pé, e a
leitura direta da planilha é o que permite o assistente responder sem o
banco no ar.

O que esta porta unifica é o **acesso**, não a fonte. Os dois adaptadores
precisam devolver as mesmas quatro tabelas com os mesmos tipos; divergência
entre eles não aparece como erro, e sim como número diferente.
"""
from __future__ import annotations

import os
from typing import Protocol

import pandas as pd


class FonteDaCarteira(Protocol):
    """O contrato que qualquer adaptador de dados precisa cumprir."""

    def clientes(self) -> pd.DataFrame: ...
    def atendimento_mensal(self) -> pd.DataFrame: ...
    def situacao_clientes(self) -> pd.DataFrame: ...
    def pesquisas_nps(self) -> pd.DataFrame: ...

    def carregar_tudo(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """As quatro tabelas de uma vez, na ordem
        (clientes, atendimento, situação, pesquisas) — a ordem que o
        dashboard e o modelo de risco já consomem."""
        ...


# Nome do adaptador padrão. `sqlserver` continua sendo o default porque é de
# lá que o dashboard e o score de risco leem hoje; a planilha é a origem da
# ingestão e a fonte do assistente.
VARIAVEL_DE_AMBIENTE = "HOLDER_FONTE_DADOS"
PADRAO = "sqlserver"


def fonte(nome: str | None = None) -> FonteDaCarteira:
    """Devolve o adaptador pedido — por argumento, por variável de ambiente
    (`HOLDER_FONTE_DADOS`) ou o padrão. Importa sob demanda pra que escolher
    a planilha não exija driver de SQL Server instalado, e vice-versa."""
    nome = (nome or os.environ.get(VARIAVEL_DE_AMBIENTE) or PADRAO).lower()

    if nome == "sqlserver":
        from .adaptador_sqlserver import FonteSqlServer

        return FonteSqlServer()
    if nome == "excel":
        from .adaptador_excel import FonteExcel

        return FonteExcel()

    raise ValueError(f"Fonte de dados desconhecida: {nome!r}. Use 'sqlserver' ou 'excel'.")
