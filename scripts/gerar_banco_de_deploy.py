"""
Gera o `dados/holder.sqlite3` que sobe no deploy.

Script de apoio, não parte da aplicação. Roda na máquina de quem tem o SQL
Server local no ar e produz o arquivo versionado que o Streamlit Cloud lê:

    python scripts/gerar_banco_de_deploy.py

Por que copiar do SQL Server em vez de recalcular: `fScoreRisco` e
`fModeloRiscoLog` são resultado de treino, e `python -m holder.aplicacao.treino`
reescreveria o `modelo_risco.pkl` versionado. Copiar preserva exatamente o
modelo e as métricas que já foram validados — o deploy mostra o mesmo número
que a máquina local, não um número novo.

As quatro tabelas da carteira NÃO são copiadas: elas vêm da planilha, pela
ingestão normal (`HOLDER_BANCO=sqlite python -m holder.infra.etl.ingestao`),
que é a mesma origem dos dois lados e não depende do banco estar no ar.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

# Script solto: rodar `python scripts/x.py` coloca `scripts/` no sys.path, não
# a raiz do repo — mesmo prólogo de `gerar_pesos_alerta.py`.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# O dialeto é escolhido por variável de ambiente lida a cada `criar_engine()`,
# então dá pra ter os dois bancos abertos no mesmo processo alternando-a.
# Precisa vir antes de importar os módulos de persistência.
from holder.infra.dados import conexao  # noqa: E402
from holder.infra.persistencia import historico_score, log_treinos  # noqa: E402

TABELAS = {
    historico_score.TABELA: historico_score.DDL,
    log_treinos.TABELA: log_treinos.DDL,
}


def _com_dialeto(nome: str):
    os.environ[conexao.VARIAVEL_DE_AMBIENTE] = nome
    return conexao.criar_engine()


def main() -> None:
    print(f"Destino: {conexao.ARQUIVO_SQLITE}\n")

    origem = _com_dialeto("sqlserver")
    try:
        lidas = {t: pd.read_sql(f"SELECT * FROM {t}", origem) for t in TABELAS}
    finally:
        origem.dispose()

    destino = _com_dialeto("sqlite")
    try:
        with destino.begin() as conn:
            for tabela, ddl in TABELAS.items():
                # DROP antes do CREATE: o script é reexecutável, e regravar
                # por cima sem limpar duplicaria o histórico.
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS {tabela}")
                conn.exec_driver_sql(ddl["sqlite"])

        for tabela, df in lidas.items():
            df.to_sql(tabela, con=destino, if_exists="append", index=False)
            print(f"   OK   {len(df)} registros copiados para '{tabela}'.")
    finally:
        destino.dispose()

    print("\nBanco de deploy gerado. Rode a ingestão para as tabelas da carteira:")
    print("   HOLDER_BANCO=sqlite python -m holder.infra.etl.ingestao")


if __name__ == "__main__":
    main()
