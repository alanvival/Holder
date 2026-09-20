"""
Dashboard executivo de Customer Success.

    streamlit run holder/interfaces/dashboard/app.py

Este arquivo tinha 667 linhas e fazia tudo: conexão com o banco, preparação
dos dados, estilo e as três abas inteiras. Hoje é só a montagem — o cálculo
está em `holder/dominio/`, o estilo em `estilo.py` e cada aba no seu módulo.

Tudo roda dentro de `main()`, e não no nível do módulo, para que importar
este arquivo não dispare uma interface. `st.set_page_config` é a primeira
chamada, por exigência do Streamlit.
"""
from __future__ import annotations

import streamlit as st

from holder.dominio.carteira import carregar_e_preparar

from . import estilo, matriz, monitor, score

ABAS = [
    "Matriz Estratégica (Visão Geral)",
    "Monitor Individual (Análise de Risco)",
    "Score de Risco (Preditivo)",
]


@st.cache_data
def carregar_dados():
    """O cálculo mora em holder/dominio/carteira/preparacao.py — aqui fica
    só o cache, que é detalhe do Streamlit e não regra de negócio."""
    return carregar_e_preparar()


def main() -> None:
    st.set_page_config(page_title="Dashboard Executivo CS", layout="wide")
    estilo.aplicar()

    # `padroes_churn` e `taxa_falso_alarme` são calculados pela preparação e
    # não são exibidos por nenhuma aba hoje — eram assim antes da divisão
    # também. Ficam nomeados em vez de descartados pra deixar a lacuna
    # visível, em vez de parecer que a preparação devolve o que ninguém pediu.
    (df_cli, df_atd, df_sit, df_nps, df_rfv,
     linhas_risco, padroes_churn, strikes, taxa_falso_alarme) = carregar_dados()

    st.title("Dashboard Integrado de Customer Success")
    tab1, tab2, tab3 = st.tabs(ABAS)

    with tab1:
        matriz.renderizar(df_rfv, strikes)
    with tab2:
        monitor.renderizar(df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco)
    with tab3:
        score.renderizar(df_cli, df_sit)


main()
