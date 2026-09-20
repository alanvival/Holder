"""
Score de risco de cancelamento — arquivo EM TRANSIÇÃO.

O que era infraestrutura aqui já saiu:

- a conexão com o SQL Server virou `holder/infra/dados/conexao.py` (e com
  ela morreu a terceira cópia da mesma string ODBC);
- a leitura das quatro tabelas virou
  `holder/infra/dados/adaptador_sqlserver.py`, atrás da porta de dados;
- a persistência do histórico mensal virou
  `holder/infra/persistencia/historico_score.py`.

O que sobrou é DOMÍNIO: as faixas de ação e a classificação de um score
nelas. Isso sai na fase 5 para `holder/dominio/risco/faixas.py`. Até lá,
este módulo reexporta as funções de infra para não quebrar o
`import score_risco as sr` de modelo_risco.py, app.py e previsao_risco.py.

O CÁLCULO do score mora em modelo_risco.py (regressão logística treinada e
validada — ver lá para a metodologia).
"""
from __future__ import annotations

from holder.infra.dados import conexao
from holder.infra.dados.porta import fonte
from holder.infra.persistencia import historico_score

# Mantidos para quem já importava daqui.
SERVER = conexao.SERVER
DATABASE = conexao.DATABASE

# Faixas de ação — ponto de partida, recalibrar depois que houver histórico
# real de quantos clientes em cada faixa efetivamente cancelaram.
FAIXAS = [
    (0, 30, "Saudável"),
    (30, 55, "Atenção"),
    (55, 75, "Em risco"),
    (75, 101, "Crítico"),
]


def faixa_de(risco_percentual: float) -> str:
    for lo, hi, nome in FAIXAS:
        if lo <= risco_percentual < hi:
            return nome
    return "Crítico"


def _num(v):
    if v is None or v != v:  # None ou NaN
        return None
    return round(float(v), 2)


# --- Reexportações de infra (transitórias) ---------------------------------

def _engine():
    return conexao.criar_engine()


def carregar_dados():
    """As quatro tabelas da carteira, na ordem
    (clientes, atendimento, situação, pesquisas). Vem da porta de dados, o
    que significa que `HOLDER_FONTE_DADOS=excel` passa a funcionar aqui —
    o padrão continua sendo o SQL Server, como sempre foi."""
    return fonte().carregar_tudo()


def _garantir_tabela_historico(engine):
    return historico_score.garantir_tabela(engine)


def carregar_historico(cliente_id: str | None = None, mes_ref: str | None = None):
    return historico_score.carregar_historico(cliente_id, mes_ref)
