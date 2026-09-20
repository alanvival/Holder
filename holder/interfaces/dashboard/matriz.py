"""
Aba 1 — Matriz Estratégica.

Três módulos: a matriz valor × saúde, o ranking de priorização de contato e
o painel de strikes. Responde às perguntas "com quais clientes falar" e "em
que ordem".
"""
from __future__ import annotations

import textwrap

import plotly.graph_objects as go
import streamlit as st

from .estilo import CORES_FAIXA, cores_por_corte, modulo_header

COLUNAS_STRIKES_ORIGEM = [
    "Strike 1 (SLA Crítico Atual)",
    "Strike 2 (Lentidão Atual)",
    "Strike 3 (Reclamação Recente)",
    "Strike 4 (Último NPS Detrator)",
]

COLUNAS_STRIKES_EXIBICAO = [
    "SLA Crítico",
    "Lentidão na Resolução",
    "Reclamação Recente",
    "NPS Detrator",
]


def _renderizar_matriz(df_rfv) -> None:
    modulo_header(
        "Matriz Estratégica",
        "Cruza valor (ticket mensal) e saúde do cliente pra mostrar onde concentrar esforço comercial e de retenção.",
    )
    x_labels = ['1 - Saúde Crítica', '2 - Saúde Ruim', '3 - Saúde Média', '4 - Saúde Boa', '5 - Saúde Excelente']
    y_labels = ['1 - Ticket Muito Baixo', '2 - Ticket Baixo', '3 - Ticket Médio', '4 - Ticket Alto', '5 - Ticket Muito Alto']
    z_colors, hover_text, annotations = [], [], []

    for y in range(1, 6):
        z_row, hover_row = [], []
        for x in range(1, 6):
            clientes_quadrante = df_rfv[(df_rfv['R_Score'] == x) & (df_rfv['V_Score'] == y)]
            qtd, mrr_total = len(clientes_quadrante), clientes_quadrante['valor_mensal'].sum()
            lista_ids = clientes_quadrante['cliente_id'].tolist()
            clientes_formatados = "<br>".join(textwrap.wrap(", ".join(lista_ids), width=40)) if qtd > 0 else "Nenhum cliente"

            if y >= 4 and x <= 2: cor_z = 2
            elif y <= 2 and x >= 4: cor_z = 0
            elif x >= 4: cor_z = 0
            elif x <= 2 and y <= 2: cor_z = 1
            else: cor_z = 1

            z_row.append(cor_z)
            mrr_formatado = f"R$ {mrr_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            hover_row.append(f"<b>Ticket:</b> Classe {y}<br><b>Saúde:</b> Classe {x}<br><b>MRR:</b> {mrr_formatado}<br><b>Qtd:</b> {qtd}<br><br>{clientes_formatados}")
            annotations.append(dict(x=x_labels[x-1], y=y_labels[y-1], text=f"<b>{qtd}</b> clientes<br>({mrr_formatado})" if qtd > 0 else "-", showarrow=False, font=dict(color="black" if cor_z != 2 else "white")))

        z_colors.append(z_row)
        hover_text.append(hover_row)

    fig = go.Figure(data=go.Heatmap(
        z=z_colors, x=x_labels, y=y_labels, customdata=hover_text,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=[[0.0, CORES_FAIXA['Saudável']], [0.5, CORES_FAIXA['Atenção']], [1.0, CORES_FAIXA['Crítico']]],
        showscale=False, xgap=3, ygap=3,
    ))
    fig.update_layout(
        annotations=annotations,
        xaxis=dict(title=dict(text='<b>← Classificação de Saúde do Cliente (Risco) →</b>'), side='bottom', automargin=True),
        yaxis=dict(title=dict(text='<b>← Classificação de Ticket (Valor Mensal) →</b>'), automargin=True),
        height=650, margin=dict(t=30, b=50, l=50, r=50),
    )
    st.plotly_chart(fig, use_container_width=True)


def _renderizar_ranking(df_rfv) -> None:
    modulo_header(
        "Ranking de Priorização de Contato",
        "Clientes ordenados por risco (pior primeiro) — por quem começar esta semana.",
    )
    df_ranking = df_rfv.sort_values(by=['R_Score', 'V_Score'], ascending=[True, False]).copy()
    df_display = df_ranking[['cliente_id', 'segmento', 'valor_mensal', 'Fator_Risco', 'Categoria_Saude']].copy()
    df_display.columns = ['ID Cliente', 'Setor', 'Ticket Mensal (R$)', 'Total Falhas (SLA + Reclamações)', 'Status Estratégico']

    # Cortes por quartil da própria coluna — mesma ideia de "4 baldes
    # discretos" da matriz, calibrada aos valores reais desta métrica (não é
    # um percentual 0-100 como o score de risco, então os cortes fixos de lá
    # não serviriam aqui).
    cortes_falhas = tuple(df_display['Total Falhas (SLA + Reclamações)'].quantile([0.25, 0.5, 0.75]))
    st.dataframe(
        df_display.style
            .apply(lambda s: cores_por_corte(s, cortes_falhas), subset=['Total Falhas (SLA + Reclamações)'])
            .format({'Ticket Mensal (R$)': 'R$ {:.2f}'}),
        use_container_width=True, hide_index=True,
    )


def _renderizar_strikes(strikes) -> None:
    com_strike = strikes[strikes['Total_Strikes'] > 0].sort_values('Total_Strikes', ascending=False).reset_index()

    if com_strike.empty:
        modulo_header("Painel de Strikes", "Problemas ativos hoje, por cliente.")
        st.success("Nenhum cliente ativo apresenta problemas simultâneos não resolvidos hoje.")
        return

    modulo_header(
        "Painel de Strikes",
        "Problemas ativos hoje, por cliente — quanto mais colunas marcadas, maior a urgência de contato.",
    )
    st.caption("● marcado = alerta em aberto nesta coluna agora · célula vazia = sem problema ativo nesse indicador.")

    df_tabela = com_strike[['cliente_id', 'Total_Strikes'] + COLUNAS_STRIKES_ORIGEM].copy()
    df_tabela.columns = ['ID Cliente', 'Total de Infrações'] + COLUNAS_STRIKES_EXIBICAO

    # Marcador tipográfico (não emoji) pra alerta ativo — a cor vem do
    # Styler, não de um pictograma colorido embutido no texto.
    for col in COLUNAS_STRIKES_EXIBICAO:
        df_tabela[col] = df_tabela[col].map({1: '●', 0: ''})

    def pinta_alerta(s):
        return [f"color: {CORES_FAIXA['Crítico']}; font-weight: 700;" if v == '●' else '' for v in s]

    # Total de infrações vai de 1 a 4 (tabela já filtrada por >0) — cortes
    # fixos nessa escala pequena, mesma paleta de faixa do resto do app.
    st.dataframe(
        df_tabela.style
            .apply(lambda s: cores_por_corte(s, (1, 2, 3)), subset=['Total de Infrações'])
            .apply(pinta_alerta, subset=COLUNAS_STRIKES_EXIBICAO),
        use_container_width=True, hide_index=True,
    )


def renderizar(df_rfv, strikes) -> None:
    with st.container(border=True):
        _renderizar_matriz(df_rfv)
    with st.container(border=True):
        _renderizar_ranking(df_rfv)
    with st.container(border=True):
        _renderizar_strikes(strikes)
