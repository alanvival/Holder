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

from holder.dominio.carteira import calcular_rfv, carregar_e_preparar

# Imports ABSOLUTOS, não relativos: o `streamlit run` executa este arquivo
# como script (`__name__ == "__main__"`, sem pacote), e `from . import ...`
# levanta "attempted relative import with no known parent package". Os
# outros módulos do dashboard podem usar import relativo à vontade — eles
# são importados como parte do pacote. Só este, que é o ponto de entrada,
# não pode.
from holder.interfaces.dashboard import estilo, matriz, monitor, score

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


@st.cache_data
def carregar_rfv_periodo(df_cli, df_atd, df_sit, df_nps, meses):
    """RFV da Matriz Estratégica recalculada pro período escolhido no
    seletor da aba — nunca chamado pra linhas_risco/padroes_churn (esses
    ignoram o período de propósito, calculados uma vez em carregar_dados)."""
    return calcular_rfv(df_cli, df_atd, df_sit, df_nps, meses=meses)


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
        meses_periodo = st.selectbox(
            "Período considerado (clientes ativos)",
            options=[3, 6, 9, 12],
            index=3,
            format_func=lambda m: f"Últimos {m} meses" if m != 12 else "Último 1 ano",
            help=(
                "Filtra o histórico de atendimento E de NPS dos clientes ATIVOS usado nesta "
                "aba (matriz e ranking) — um cliente com falhas reais no período mas NPS bom "
                "no mesmo período tem a saúde ajustada pra cima. As linhas de corte tiradas de "
                "quem já cancelou continuam usando a base inteira, sem esse filtro."
            ),
        )
        df_rfv_periodo = carregar_rfv_periodo(df_cli, df_atd, df_sit, df_nps, meses_periodo)
        matriz.renderizar(df_rfv_periodo, strikes)
    with tab2:
        monitor.renderizar(df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco)
    with tab3:
        score.renderizar(df_cli, df_sit)


main()
