"""
Adaptador de leitura da carteira a partir da planilha do desafio
(`INOVAAPPS_base_de_dados.xlsx`).

É a fonte do assistente, e é o que permite ele responder com o SQL Server
fora do ar. Também é a origem da ingestão que popula o banco e do JSON que
o front consome — ou seja, a mesma planilha alimenta os dois caminhos.

A leitura é preguiçosa e cacheada: acontece na primeira vez que alguém pede
uma tabela, e uma única vez por processo. Importar este módulo não toca em
disco.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
PLANILHA = RAIZ / "INOVAAPPS_base_de_dados.xlsx"

ABAS = ("clientes", "atendimento_mensal", "situacao_clientes", "pesquisas_nps")


@lru_cache(maxsize=1)
def _abas() -> dict:
    """Lê a planilha inteira uma vez por processo. Chamadas seguintes
    devolvem exatamente os mesmos objetos, sem reler nada."""
    return pd.read_excel(PLANILHA, sheet_name=None)


def aba(nome: str) -> pd.DataFrame:
    if nome not in ABAS:
        raise KeyError(f"Aba desconhecida: {nome!r}. Disponíveis: {', '.join(ABAS)}")
    return _abas()[nome]


class FonteExcel:
    def clientes(self) -> pd.DataFrame:
        return aba("clientes")

    def atendimento_mensal(self) -> pd.DataFrame:
        return aba("atendimento_mensal")

    def situacao_clientes(self) -> pd.DataFrame:
        return aba("situacao_clientes")

    def pesquisas_nps(self) -> pd.DataFrame:
        return aba("pesquisas_nps")

    def carregar_tudo(self):
        return (
            self.clientes(),
            self.atendimento_mensal(),
            self.situacao_clientes(),
            self.pesquisas_nps(),
        )
