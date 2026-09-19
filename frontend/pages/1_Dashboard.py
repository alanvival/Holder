import pandas as pd
import streamlit as st

from api_client import ApiErro
from auth import exigir_login, tratar_erro
from formatacao import ROTULO_FAIXA, ROTULO_RESPONSAVEL, brl

st.set_page_config(page_title="Dashboard · Holder", layout="wide")
api = exigir_login()

with st.sidebar:
    if st.button("Reprocessar análise", key="botao_reprocessar"):
        try:
            api.executar_analise()
        except ApiErro as erro:
            tratar_erro(erro)
        st.rerun()

st.title("Com quais clientes falar primeiro?")

try:
    resumo = api.resumo_dashboard()
    fila = api.fila(limite=10)
except ApiErro as erro:
    tratar_erro(erro)

if resumo["mes_referencia"] is None:
    st.info(
        "Nenhuma análise executada ainda. Importe a planilha no backend "
        "(`python -m scripts.importar_base`) e recarregue esta página."
    )
    st.stop()

st.caption(
    f"Mês de referência: {resumo['mes_referencia']} · "
    f"análise executada em {resumo['executado_em']} (UTC)"
)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Clientes ativos", resumo["clientes_ativos"])
col2.metric("Receita ativa (mês)", brl(resumo["receita_ativa"]))
col3.metric("Receita em risco (mês)", brl(resumo["receita_em_risco"]))
col4.metric("Na fila de atenção", resumo["qtd_na_fila"])

st.subheader("Fila priorizada")
if not fila:
    st.success("Nenhum cliente em faixa Crítico ou Atenção no momento.")
else:
    tabela = pd.DataFrame(
        [
            {
                "Posição": item["posicao"],
                "Cliente": item["cliente_id"],
                "Segmento": item["segmento"],
                "Plano": item["plano"].title(),
                "Faixa": ROTULO_FAIXA[item["faixa"]],
                "Score": item["score_risco"],
                "Receita em risco": brl(item["receita_em_risco"]),
                "Por quê": " · ".join(item["principais_motivos"]),
                "O que fazer": (item["acao_recomendada"] or {}).get("titulo", "—"),
                "Responsável": ROTULO_RESPONSAVEL.get(
                    (item["acao_recomendada"] or {}).get("responsavel", ""), "—"
                ),
            }
            for item in fila
        ]
    )
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0.0, max_value=1.0, format="%.2f"
            ),
            "Por quê": st.column_config.TextColumn("Por quê", width="large"),
        },
    )

col_faixa, col_dimensao = st.columns(2)
with col_faixa:
    st.markdown("**Clientes ativos por faixa de risco**")
    st.bar_chart(pd.Series({ROTULO_FAIXA[f]: q for f, q in resumo["por_faixa"].items()}))
with col_dimensao:
    st.markdown("**Clientes com sinal disparado, por dimensão**")
    st.bar_chart(pd.Series(resumo["por_dimensao"]))
