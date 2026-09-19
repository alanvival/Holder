import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import ApiErro
from auth import exigir_login, tratar_erro
from formatacao import ROTULO_FAIXA, ROTULO_RESPONSAVEL, brl

st.set_page_config(page_title="Clientes · Holder", layout="wide")
api = exigir_login()

ROTULO_ORDEM = {
    "receita_em_risco": "Receita em risco",
    "score": "Score de risco",
    "valor_mensal": "Valor mensal",
    "cliente_id": "Código do cliente",
}
SEGMENTOS = ["Educacao", "Industria", "Logistica", "Saude", "Servicos", "Varejo"]


def _ou_nada(valor: str) -> str | None:
    return None if valor in ("Todas", "Todos") else valor


def _grafico(df: pd.DataFrame, colunas: list[str], titulo: str, eixo_y: str):
    figura = px.line(
        df,
        x="mes_ref",
        y=colunas,
        markers=True,
        title=titulo,
        labels={"mes_ref": "Mês", "value": eixo_y, "variable": ""},
        template="plotly_white",
    )
    figura.update_layout(
        xaxis_tickformat="%b/%Y",
        hovermode="x unified",
        height=320,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        legend={"orientation": "h"},
    )
    return figura


with st.sidebar:
    st.header("Filtros")
    situacao = st.selectbox("Situação", ["Todas", "ATIVO", "CANCELADO"], key="f_situacao")
    faixa = st.selectbox(
        "Faixa de risco",
        ["Todas", *ROTULO_FAIXA],
        format_func=lambda v: ROTULO_FAIXA.get(v, v),
        key="f_faixa",
    )
    plano = st.selectbox("Plano", ["Todos", "ESSENCIAL", "AVANCADO", "ENTERPRISE"], key="f_plano")
    segmento = st.selectbox("Segmento", ["Todos", *SEGMENTOS], key="f_segmento")
    busca = st.text_input("Buscar (código ou segmento)", key="f_busca")
    ordenar = st.selectbox(
        "Ordenar por", list(ROTULO_ORDEM), format_func=ROTULO_ORDEM.get, key="f_ordenar"
    )
    pagina = st.number_input("Página", min_value=1, value=1, step=1, key="f_pagina")

st.title("Clientes")

try:
    resultado = api.listar_clientes(
        situacao=_ou_nada(situacao),
        faixa=_ou_nada(faixa),
        plano=_ou_nada(plano),
        segmento=_ou_nada(segmento),
        busca=busca.strip() or None,
        ordenar=ordenar,
        pagina=int(pagina),
        tamanho=20,
    )
except ApiErro as erro:
    tratar_erro(erro)

st.caption(f"{resultado['total']} clientes encontrados · página {resultado['pagina']}")
if not resultado["itens"]:
    st.info("Nenhum cliente encontrado com esses filtros.")
    st.stop()

st.dataframe(
    pd.DataFrame(
        [
            {
                "Cliente": c["cliente_id"],
                "Segmento": c["segmento"],
                "Plano": c["plano"].title(),
                "Valor mensal": brl(c["valor_mensal"]),
                "Situação": (c["situacao"] or "—").title(),
                "Faixa": ROTULO_FAIXA.get(c["faixa"] or "", "—"),
                "Score": f"{c['score_risco']:.2f}" if c["score_risco"] is not None else "—",
                "Receita em risco": brl(c["receita_em_risco"]),
                "Posição na fila": c["posicao_fila"] if c["posicao_fila"] is not None else "—",
            }
            for c in resultado["itens"]
        ]
    ),
    hide_index=True,
    width="stretch",
)

st.divider()
escolhido = st.selectbox(
    "Ver detalhe do cliente", [c["cliente_id"] for c in resultado["itens"]], key="cliente_escolhido"
)
try:
    detalhe = api.cliente(escolhido)
    historico = api.historico(escolhido)
except ApiErro as erro:
    tratar_erro(erro)

st.subheader(f"{detalhe['cliente_id']} · {detalhe['segmento']} · {detalhe['plano'].title()}")
avaliacao = detalhe["avaliacao"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Valor mensal", brl(detalhe["valor_mensal"]))
col2.metric("Situação", (detalhe["situacao"] or "—").title())
col3.metric("Faixa", ROTULO_FAIXA[avaliacao["faixa"]] if avaliacao else "—")
col4.metric("Posição na fila", (avaliacao or {}).get("posicao_fila") or "—")

if avaliacao is None:
    st.info("Cliente sem avaliação de risco (apenas clientes ativos são avaliados).")
else:
    st.markdown("**Por quê**")
    if avaliacao["evidencias"]:
        st.markdown("\n".join(f"- {e['texto']}" for e in avaliacao["evidencias"]))
    else:
        st.markdown("- Nenhum sinal de risco disparado.")
    acao = avaliacao["acao_recomendada"]
    if acao:
        st.markdown("**O que fazer**")
        st.info(
            f"**{acao['titulo']}** — responsável: "
            f"{ROTULO_RESPONSAVEL.get(acao['responsavel'], acao['responsavel'])}, "
            f"prazo: {acao['prazo_dias']} dias\n\n{acao['descricao']}"
        )

atendimento = pd.DataFrame(historico["atendimento"])
if not atendimento.empty:
    atendimento["mes_ref"] = pd.to_datetime(atendimento["mes_ref"])
    grafico1, grafico2 = st.columns(2)
    grafico1.plotly_chart(
        _grafico(atendimento, ["uso_plataforma_pct"], "Uso da plataforma", "%"), width="stretch"
    )
    grafico2.plotly_chart(
        _grafico(atendimento, ["pct_sla_cumprido"], "SLA cumprido", "%"), width="stretch"
    )
    grafico3, grafico4 = st.columns(2)
    grafico3.plotly_chart(
        _grafico(
            atendimento,
            ["chamados_abertos", "chamados_criticos", "chamados_reabertos"],
            "Chamados",
            "qtd",
        ),
        width="stretch",
    )
    nps = pd.DataFrame(historico["nps"])
    if not nps.empty:
        nps["mes_ref"] = pd.to_datetime(nps["mes_ref"])
        respondidas = nps[nps["respondeu"]]
        grafico4.plotly_chart(
            _grafico(respondidas, ["nota_nps"], "Nota de NPS (pesquisas respondidas)", "nota"),
            width="stretch",
        )
        sem_resposta = int((~nps["respondeu"]).sum())
        if sem_resposta:
            grafico4.caption(f"{sem_resposta} pesquisa(s) sem resposta no período.")
