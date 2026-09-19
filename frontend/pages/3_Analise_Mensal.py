import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import ApiErro
from auth import exigir_login, tratar_erro

st.set_page_config(page_title="Análise mensal · Holder", layout="wide")
api = exigir_login()

try:
    variaveis = api.variaveis_metricas()
except ApiErro as erro:
    tratar_erro(erro)
rotulos = {v["codigo"]: v["rotulo"] for v in variaveis}
nomes_agregacao = {"media": "Média", "soma": "Soma"}

with st.sidebar:
    st.header("Configurações do gráfico")
    variavel = st.selectbox("Métrica", list(rotulos), format_func=rotulos.get, key="m_variavel")
    agregacao = st.radio(
        "Cálculo", list(nomes_agregacao), format_func=nomes_agregacao.get, key="m_agregacao"
    )

st.title("Evolução mensal da carteira")

try:
    pontos = api.metrica_mensal(variavel, agregacao)
except ApiErro as erro:
    tratar_erro(erro)

if not pontos:
    st.info("Sem dados para esta métrica. Importe a planilha no backend.")
    st.stop()

df = pd.DataFrame(pontos)
df["mes_ref"] = pd.to_datetime(df["mes_ref"])
titulo = f"{rotulos[variavel]} — {nomes_agregacao[agregacao]} mensal"
figura = px.line(
    df,
    x="mes_ref",
    y="valor",
    markers=True,
    title=titulo,
    labels={"mes_ref": "Mês de referência", "valor": rotulos[variavel]},
    template="plotly_white",
)
figura.update_traces(
    line={"width": 4, "color": "#0156FC"},
    marker={"size": 10, "color": "#000A1E"},
    fill="tozeroy",
    fillcolor="rgba(1, 86, 252, 0.08)",
)
figura.update_layout(xaxis_tickformat="%b/%Y", hovermode="x unified")
st.plotly_chart(figura, width="stretch")

with st.expander("Ver dados em tabela"):
    st.dataframe(
        df.rename(columns={"mes_ref": "Mês", "valor": rotulos[variavel]}),
        hide_index=True,
        width="stretch",
    )
