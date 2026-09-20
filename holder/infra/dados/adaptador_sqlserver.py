"""
Adaptador de leitura da carteira a partir do SQL Server — o modelo
dimensional populado pela ingestão (`holder/infra/etl/ingestao.py`).

É a fonte do dashboard e do score de risco.
"""
from __future__ import annotations

import pandas as pd

from . import conexao

# Tabela do banco por nome de domínio. O prefixo d/f é do modelo
# dimensional (dimensão/fato) e não vaza pra fora deste módulo.
TABELAS = {
    "clientes": "dClientes",
    "atendimento_mensal": "fAtendimento",
    "situacao_clientes": "dSituacao",
    "pesquisas_nps": "fPesquisa",
}


class FonteSqlServer:
    def _ler(self, nome: str) -> pd.DataFrame:
        engine = conexao.criar_engine()
        try:
            return pd.read_sql(f"SELECT * FROM {TABELAS[nome]}", engine)
        finally:
            engine.dispose()

    def clientes(self) -> pd.DataFrame:
        return self._ler("clientes")

    def atendimento_mensal(self) -> pd.DataFrame:
        return self._ler("atendimento_mensal")

    def situacao_clientes(self) -> pd.DataFrame:
        return self._ler("situacao_clientes")

    def pesquisas_nps(self) -> pd.DataFrame:
        return self._ler("pesquisas_nps")

    def carregar_tudo(self):
        """As quatro tabelas com UM motor de conexão só, não quatro — é como
        o dashboard e o score de risco sempre leram, e abrir conexão por
        tabela numa instância local é justamente o que deixava a leitura
        errática."""
        engine = conexao.criar_engine()
        try:
            return (
                pd.read_sql(f"SELECT * FROM {TABELAS['clientes']}", engine),
                pd.read_sql(f"SELECT * FROM {TABELAS['atendimento_mensal']}", engine),
                pd.read_sql(f"SELECT * FROM {TABELAS['situacao_clientes']}", engine),
                pd.read_sql(f"SELECT * FROM {TABELAS['pesquisas_nps']}", engine),
            )
        finally:
            engine.dispose()
