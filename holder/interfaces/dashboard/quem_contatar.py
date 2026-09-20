"""
Aba 1 — Quem Contatar.

Resposta direta ao "teste de completude" do desafio INOVAAPPS 2026: ao
abrir a solução, alguém que trabalha com a carteira precisa conseguir
responder três perguntas — com quais clientes falar, por que cada um, e em
que ordem. Antes essas três respostas ficavam espalhadas (a aba que abria
primeiro era a Matriz, uma visão geral; a lista com motivo ficava na 3ª
aba, Score de Risco) — um avaliador com pouco tempo podia nem chegar lá.

Une os dois conceitos de risco que o projeto mantém deliberadamente
separados (ver docs/adr/0001-dois-conceitos-de-risco.md):
- **Score de risco** (modelo treinado, AUC~0.95) decide EM QUE ORDEM —
  é o que responde "quão bem separa" e "com quanta antecedência aparece",
  duas das três perguntas que o próprio desafio lista como estruturantes.
- **Índice de alerta** (pesos derivados dos dados, não chutados) explica
  POR QUÊ — a lista de sinais que fundamenta o alerta.

"Quanto está em jogo" (a terceira pergunta estruturante do desafio) vira
receita mensal em risco = valor do contrato × probabilidade do modelo —
um cálculo de expectativa, não um peso escolhido à mão — usada como
critério de ordenação padrão, com o percentual de risco também sempre
visível pra quem preferir ordenar só por urgência.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from holder.dominio.alerta import indice_de_um_cliente, pesos_dos_sinais
from holder.dominio.risco import ACAO_POR_FAIXA
from holder.dominio.risco.faixas import NOMES as FAIXAS_NOMES
from holder.infra.persistencia import historico_score

from .estilo import CORES_FAIXA, modulo_header

COMANDO_DE_TREINO = "python -m holder.aplicacao.treino"


def _moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(ttl=600)
def _montar_lista(df_cli: pd.DataFrame, ativos_ids: frozenset) -> pd.DataFrame:
    hist = historico_score.carregar_historico()
    if hist.empty:
        return pd.DataFrame()

    mes_atual = hist["mes_ref"].max()
    linhas = hist[(hist["mes_ref"] == mes_atual) & (hist["cliente_id"].isin(ativos_ids))].copy()
    if linhas.empty:
        return pd.DataFrame()

    linhas = linhas.merge(
        df_cli[["cliente_id", "valor_mensal", "segmento", "porte"]], on="cliente_id", how="left"
    )
    linhas["receita_em_risco"] = linhas["valor_mensal"] * linhas["risco_percentual"] / 100
    linhas["acao_sugerida"] = linhas["faixa"].map(ACAO_POR_FAIXA)

    # pesos_dos_sinais() agrega a base inteira (fatores de churn) — calcular
    # uma vez aqui e reaproveitar pra cada cliente evita recalcular isso 58x
    # (um por cliente ativo), que é o que fazia essa lista demorar demais
    # pra abrir na primeira tentativa.
    pesos = pesos_dos_sinais()
    linhas["sinais"] = linhas["cliente_id"].apply(
        lambda cid: (indice_de_um_cliente(cid, pesos) or {}).get("sinais", [])
    )

    return linhas.sort_values("receita_em_risco", ascending=False).reset_index(drop=True)


def _linha_contato(r: pd.Series, posicao: int) -> None:
    cor = CORES_FAIXA[r["faixa"]]
    with st.container(border=True):
        col_pos, col_score, col_meta, col_receita, col_badge = st.columns([0.5, 1.1, 2.6, 1.6, 1.2])
        with col_pos:
            st.markdown(
                f"<div style='font-family:\"Space Grotesk\",sans-serif;font-weight:700;"
                f"font-size:1.1rem;color:rgba(0,10,30,0.32);margin-top:4px;'>#{posicao}</div>",
                unsafe_allow_html=True,
            )
        with col_score:
            st.markdown(
                f"<div style='font-family:\"Space Grotesk\",sans-serif;font-weight:700;"
                f"font-size:1.6rem;line-height:1;color:{cor};'>{r['risco_percentual']:.0f}%</div>"
                f"<div style='font-family:\"Montserrat\",sans-serif;font-size:0.72rem;"
                f"color:rgba(0,10,30,0.5);margin-top:2px;'>risco previsto</div>",
                unsafe_allow_html=True,
            )
        with col_meta:
            st.markdown(
                f"<div style='font-family:\"Montserrat\",sans-serif;'>"
                f"<b style='font-size:1.05rem;'>{r['cliente_id']}</b> "
                f"<span style='color:rgba(0,10,30,0.55);'>· {r['segmento']} · {r['porte']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_receita:
            st.markdown(
                f"<div style='font-family:\"Space Grotesk\",sans-serif;font-weight:700;"
                f"font-size:1.05rem;color:#000A1E;'>{_moeda(r['receita_em_risco'])}</div>"
                f"<div style='font-family:\"Montserrat\",sans-serif;font-size:0.72rem;"
                f"color:rgba(0,10,30,0.5);margin-top:2px;'>receita mensal em risco</div>",
                unsafe_allow_html=True,
            )
        with col_badge:
            st.markdown(
                f"<div style='margin-top:6px;display:inline-block;background:{cor}33;"
                f"border:1px solid {cor};color:#000A1E;border-radius:12px;padding:4px 12px;"
                f"font-family:\"Montserrat\",sans-serif;font-size:0.78rem;font-weight:600;'>"
                f"{r['faixa']}</div>",
                unsafe_allow_html=True,
            )

        sinais = r["sinais"]
        if sinais:
            st.markdown(
                f"<div style='margin-top:10px;font-family:\"Montserrat\",sans-serif;font-size:0.85rem;'>"
                f"<b>Por quê:</b> {' · '.join(sinais)}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Sem sinais adicionais no índice de alerta — o risco vem do padrão histórico capturado pelo modelo treinado.")
        st.markdown(
            f"<div style='font-family:\"Montserrat\",sans-serif;font-size:0.85rem;margin-top:2px;'>"
            f"<b>O que fazer:</b> {r['acao_sugerida']}</div>",
            unsafe_allow_html=True,
        )


def renderizar(df_cli: pd.DataFrame, df_sit: pd.DataFrame) -> None:
    ativos_ids = frozenset(df_sit[df_sit["situacao"] == "Ativo"]["cliente_id"])
    lista = _montar_lista(df_cli, ativos_ids)

    with st.container(border=True):
        modulo_header(
            "Quem Contatar",
            "As 3 perguntas do desafio, respondidas juntas: quem, por quê, e em que ordem. "
            "Ordenado por receita mensal em risco (valor do contrato × probabilidade do modelo).",
        )

        if lista.empty:
            st.warning(f"Sem score calculado ainda. Rode `{COMANDO_DE_TREINO}` no terminal pra popular.")
            return

        faixas_padrao = [n for n in FAIXAS_NOMES[::-1] if n != "Saudável"]
        faixas_sel = st.multiselect("Faixa de risco", FAIXAS_NOMES[::-1], default=faixas_padrao)
        filtrado = lista[lista["faixa"].isin(faixas_sel)]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Clientes pra contatar", len(filtrado))
        with col2:
            st.metric("Receita mensal em risco (soma)", _moeda(filtrado["receita_em_risco"].sum()))

        if filtrado.empty:
            st.success("Nenhum cliente ativo nas faixas selecionadas.")
            return

        for posicao, (_, r) in enumerate(filtrado.iterrows(), start=1):
            _linha_contato(r, posicao)
