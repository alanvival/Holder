"""
Aba 2 — Monitor Individual.

A evolução de um cliente num indicador de atendimento, comparada à linha de
corte tirada de quem já cancelou. Responde "por que este cliente".
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .estilo import modulo_header

NOMES_DE_INDICADOR = {
    'uso_plataforma_pct': 'Uso da Plataforma (%)',
    'pct_sla_cumprido': 'SLA Cumprido (%)',
    'tempo_medio_resolucao_h': 'Tempo Médio de Resolução (h)',
    'dias_atraso_pagamento': 'Dias de Atraso no Pagamento',
    'reclamacoes_formais': 'Reclamações Formais (Qtd)',
    'chamados_abertos': 'Chamados Abertos (Qtd)',
    'chamados_criticos': 'Chamados Críticos (Qtd)',
    'chamados_reabertos': 'Chamados Reabertos (Qtd)',
    'chamados_dentro_sla': 'Chamados Dentro do SLA (Qtd)',
    'reunioes_ausentes': 'Faltas em Reuniões (Qtd)',
}

COLUNAS_NAO_PLOTAVEIS = ['cliente_id', 'mes_ref', 'mes_ref_dt', 'mes_cancelamento']

# Indicadores em que MENOR é pior — o aviso embaixo do gráfico se inverte.
INDICADORES_INVERSOS = ['uso_plataforma_pct', 'pct_sla_cumprido', 'chamados_dentro_sla']


def _formatar_reais(valor) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def renderizar(df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco) -> None:
    with st.container(border=True):
        modulo_header(
            "Monitor Individual",
            "Evolução de um cliente específico num indicador de atendimento, comparado à linha de corte tirada de quem já cancelou.",
        )

        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            cliente = st.selectbox("1. Selecione o Cliente:", sorted(df_atd['cliente_id'].unique()), key="cli_aba2")

        colunas_disponiveis = [
            col for col in df_atd.select_dtypes(include='number').columns
            if col not in COLUNAS_NAO_PLOTAVEIS
        ]
        opcoes = {
            col: NOMES_DE_INDICADOR.get(col, col.replace('_', ' ').title())
            for col in colunas_disponiveis
        }

        with col_filtro2:
            indicador = st.selectbox("2. Métrica a Observar:", list(opcoes.keys()), format_func=lambda x: opcoes[x])

        st.markdown("---")

        df_cli_atd = df_atd[df_atd['cliente_id'] == cliente].sort_values('mes_ref_dt')
        df_cli_nps = df_nps[df_nps['cliente_id'] == cliente].sort_values('mes_ref_dt')
        status = df_sit[df_sit['cliente_id'] == cliente]['situacao'].values[0]
        cor_status = "red" if status == "Cancelado" else "green"

        ultimo_nps = df_cli_nps.iloc[-1]['classificacao_nps'] if not df_cli_nps.empty else "Sem pesquisa"
        mrr = _formatar_reais(df_cli[df_cli['cliente_id'] == cliente]['valor_mensal'].values[0])

        if status == 'Ativo':
            cat_saude = df_rfv[df_rfv['cliente_id'] == cliente]['Categoria_Saude'].values[0]
            nota_saude = df_rfv[df_rfv['cliente_id'] == cliente]['R_Score'].values[0]
            saude = f"{cat_saude} (Nota {nota_saude}/5)"
        else:
            saude = "Contrato Cancelado"

        st.subheader(f"Perfil: Cliente {cliente} - Status: :{cor_status}[{status}]")
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col1: st.metric("Receita Mensal (MRR)", mrr)
        with col2: st.metric("Saúde Estratégica", saude)
        with col3: st.metric("Último NPS", ultimo_nps)

        st.write("")
        st.subheader("Análise do Indicador de Atendimento")

        col_kpi1, col_kpi2, _ = st.columns(3)
        with col_kpi1:
            st.metric(f"Média do Cliente ({opcoes[indicador]})", f"{df_cli_atd[indicador].mean():.1f}")
        with col_kpi2:
            st.metric("Linha de corte (perfil de quem cancelou)", f"{linhas_risco[indicador]:.1f}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_cli_atd['mes_ref_dt'], y=df_cli_atd[indicador],
            mode='lines+markers+text', name='Evolução',
            text=df_cli_atd[indicador].round(1), textposition='top center',
            line=dict(width=3, color='#0156FC'),
        ))
        fig.add_trace(go.Scatter(
            x=[df_cli_atd['mes_ref_dt'].min(), df_cli_atd['mes_ref_dt'].max()],
            y=[linhas_risco[indicador], linhas_risco[indicador]],
            mode='lines', name='Linha de corte',
            line=dict(color='red', width=2, dash='dash'),
        ))
        fig.update_layout(xaxis_title='Mês', yaxis_title=opcoes[indicador], template='plotly_white', hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        if indicador in INDICADORES_INVERSOS:
            st.caption("Aviso: Quanto menor este indicador, maior o risco de cancelamento.")
        elif indicador in NOMES_DE_INDICADOR:
            st.caption("Aviso: Quanto maior este indicador, maior o risco de cancelamento.")
        else:
            st.caption("Aviso: Indicador sem direção declarada. O gráfico plota o valor do cliente contra a mediana da base cancelada.")
