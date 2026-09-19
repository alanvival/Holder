import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import textwrap

st.set_page_config(page_title="Dashboard Executivo CS", layout="wide")

st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        white-space: normal !important;
        word-wrap: break-word !important;
        font-size: 1.7rem !important; 
        line-height: 1.2 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# CARREGAMENTO E PREPARAÇÃO DE DADOS (CACHE)
# ==============================================================================
@st.cache_data
def carregar_dados():
    df_cli = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='clientes')
    df_atd = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='atendimento_mensal')
    df_sit = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='situacao_clientes')
    df_nps = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='pesquisas_nps')
    
    df_atd['mes_ref_dt'] = pd.to_datetime(df_atd['mes_ref'], format='%Y-%m')
    df_nps['mes_ref_dt'] = pd.to_datetime(df_nps['mes_ref'], format='%Y-%m')
    
    df_atd = df_atd.merge(df_sit[['cliente_id', 'situacao', 'mes_cancelamento']], on='cliente_id', how='left')
    
    df_master = df_cli.merge(df_sit, on='cliente_id', how='inner')
    df_ativos = df_master[df_master['situacao'] == 'Ativo'].copy()
    df_cancelados = df_master[df_master['situacao'] == 'Cancelado'].copy()
    
    df_atd_ativos = df_atd[df_atd['cliente_id'].isin(df_ativos['cliente_id'])].copy()
    df_atd_ativos['quebra_sla'] = df_atd_ativos['pct_sla_cumprido'] < 80.0
    
    agrupamento = df_atd_ativos.groupby('cliente_id').agg(
        meses_abaixo_sla=('quebra_sla', 'sum'),
        total_reclamacoes=('reclamacoes_formais', 'sum'),
        uso_medio=('uso_plataforma_pct', 'mean')
    ).reset_index()

    df_rfv = df_ativos[['cliente_id', 'valor_mensal', 'segmento']].merge(agrupamento, on='cliente_id', how='left')
    df_rfv['V_Score'] = pd.qcut(df_rfv['valor_mensal'], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df_rfv['Fator_Risco'] = df_rfv['meses_abaixo_sla'] + df_rfv['total_reclamacoes']
    df_rfv['R_Rank'] = df_rfv['Fator_Risco'].rank(method='first', ascending=False)
    df_rfv['R_Score'] = pd.qcut(df_rfv['R_Rank'], 5, labels=[1, 2, 3, 4, 5]).astype(int)

    def categorizar(row):
        if row['V_Score'] >= 4 and row['R_Score'] <= 2: return '🚨 Ação Imediata'
        elif row['V_Score'] >= 4 and row['R_Score'] >= 3: return '⭐ Proteger e Expandir'
        elif row['V_Score'] <= 3 and row['R_Score'] <= 2: return '⚠️ Avaliar Fit'
        else: return '🔄 Fluxo Normal'
    df_rfv['Categoria_Saude'] = df_rfv.apply(categorizar, axis=1)

    # --------------------------------------------------------------------------
    # PADRÃO DOS CANCELADOS
    # --------------------------------------------------------------------------
    df_atd_canc = df_atd[df_atd['situacao'] == 'Cancelado'].copy()
    
    # CORREÇÃO: Inclusão de todas as métricas do seletor para evitar o KeyError
    linhas_risco = {
        'pct_sla_cumprido': df_atd_canc['pct_sla_cumprido'].median(),
        'tempo_medio_resolucao_h': df_atd_canc['tempo_medio_resolucao_h'].median(),
        'chamados_abertos': df_atd_canc['chamados_abertos'].median(),
        'reclamacoes_formais': df_atd_canc['reclamacoes_formais'].mean()
    }
    
    # Assinatura de Churn (Últimos meses antes da saída)
    df_atd_canc['mes_canc_dt'] = pd.to_datetime(df_atd_canc['mes_cancelamento'], format='%Y-%m')
    df_atd_canc['meses_para_canc'] = (df_atd_canc['mes_canc_dt'].dt.year - df_atd_canc['mes_ref_dt'].dt.year) * 12 + (df_atd_canc['mes_canc_dt'].dt.month - df_atd_canc['mes_ref_dt'].dt.month)
    ultimos_meses_canc = df_atd_canc[(df_atd_canc['meses_para_canc'] > 0) & (df_atd_canc['meses_para_canc'] <= 4)]
    
    total_canc = len(df_cancelados)
    pct_canc_sla = len(ultimos_meses_canc[ultimos_meses_canc['pct_sla_cumprido'] <= linhas_risco['pct_sla_cumprido']]['cliente_id'].unique()) / total_canc
    pct_canc_rec = len(ultimos_meses_canc[ultimos_meses_canc['reclamacoes_formais'] > 0]['cliente_id'].unique()) / total_canc
    
    df_nps_canc = df_nps.merge(df_sit[['cliente_id', 'situacao', 'mes_cancelamento']], on='cliente_id', how='inner')
    df_nps_canc = df_nps_canc[df_nps_canc['situacao'] == 'Cancelado']
    df_nps_canc['mes_canc_dt'] = pd.to_datetime(df_nps_canc['mes_cancelamento'], format='%Y-%m')
    df_nps_canc['meses_para_canc'] = (df_nps_canc['mes_canc_dt'].dt.year - df_nps_canc['mes_ref_dt'].dt.year) * 12 + (df_nps_canc['mes_canc_dt'].dt.month - df_nps_canc['mes_ref_dt'].dt.month)
    ultimos_meses_nps = df_nps_canc[(df_nps_canc['meses_para_canc'] > 0) & (df_nps_canc['meses_para_canc'] <= 6)]
    pct_canc_detrator = len(ultimos_meses_nps[ultimos_meses_nps['classificacao_nps'] == 'Detrator']['cliente_id'].unique()) / total_canc

    padroes_churn = {'SLA': pct_canc_sla, 'Reclamacao': pct_canc_rec, 'NPS': pct_canc_detrator}

    # --------------------------------------------------------------------------
    # NOVO SISTEMA DE STRIKES (Focado na Realidade ATUAL / Sem memória longa)
    # --------------------------------------------------------------------------
    df_atd_ativos = df_atd_ativos.sort_values(by=['cliente_id', 'mes_ref_dt'])
    df_nps_ativos = df_nps[df_nps['cliente_id'].isin(df_ativos['cliente_id'])].sort_values(by=['cliente_id', 'mes_ref_dt'])
    
    # Pega estritamente a ÚLTIMA foto de atendimento e do NPS de cada cliente
    ultimo_atd = df_atd_ativos.groupby('cliente_id').tail(1).set_index('cliente_id')
    ultimo_nps = df_nps_ativos.groupby('cliente_id').tail(1).set_index('cliente_id')
    
    # Reclamações podem ser em meses sem chamado, então olhamos apenas uma janela curta (últimos 2 meses)
    max_mes_ativos = df_atd_ativos['mes_ref_dt'].max()
    reclamacoes_recentes = df_atd_ativos[df_atd_ativos['mes_ref_dt'] >= (max_mes_ativos - pd.DateOffset(months=1))].groupby('cliente_id')['reclamacoes_formais'].sum()

    strikes = pd.DataFrame(index=df_ativos['cliente_id'])
    
    # A REGRA É CLARA: Se recuperou no último mês, o strike sai.
    strikes['Strike 1 (SLA Crítico Atual)'] = (ultimo_atd['pct_sla_cumprido'] <= linhas_risco['pct_sla_cumprido']).astype(int)
    strikes['Strike 2 (Lentidão Atual)'] = (ultimo_atd['tempo_medio_resolucao_h'] >= linhas_risco['tempo_medio_resolucao_h']).astype(int)
    strikes['Strike 3 (Reclamação Recente)'] = (reclamacoes_recentes > 0).astype(int).reindex(strikes.index).fillna(0)
    strikes['Strike 4 (Último NPS Detrator)'] = (ultimo_nps['classificacao_nps'] == 'Detrator').astype(int).reindex(strikes.index).fillna(0)

    colunas_strikes = ['Strike 1 (SLA Crítico Atual)', 'Strike 2 (Lentidão Atual)', 'Strike 3 (Reclamação Recente)', 'Strike 4 (Último NPS Detrator)']
    strikes['Total_Strikes'] = strikes[colunas_strikes].sum(axis=1)
    
    # Cálculo da Taxa de Falso Positivo (Quantos ativos estão tocando o alarme à toa?)
    taxa_falso_alarme = {
        'SLA': strikes['Strike 1 (SLA Crítico Atual)'].mean(),
        'Reclamacao': strikes['Strike 3 (Reclamação Recente)'].mean(),
        'NPS': strikes['Strike 4 (Último NPS Detrator)'].mean()
    }
    
    return df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco, padroes_churn, strikes, taxa_falso_alarme

df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco, padroes_churn, strikes, taxa_falso_alarme = carregar_dados()

# ==============================================================================
# ESTRUTURA DE ABAS (TABS)
# ==============================================================================
st.title("🎯 Dashboard Integrado de Customer Success")

tab1, tab2, tab3 = st.tabs([
    "📊 Matriz Estratégica (Visão Geral)", 
    "🔍 Monitor Individual (Análise de Risco)",
    "📉 Radar de Strikes (Filtro Vigente)"
])

# ------------------------------------------------------------------------------
# ABA 1: MATRIZ ESTRATÉGICA
# ------------------------------------------------------------------------------
with tab1:
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

    fig1 = go.Figure(data=go.Heatmap(z=z_colors, x=x_labels, y=y_labels, customdata=hover_text, hovertemplate="%{customdata}<extra></extra>", colorscale=[[0.0, '#A9DFBF'], [0.5, '#F9E79F'], [1.0, '#E74C3C']], showscale=False, xgap=3, ygap=3))
    fig1.update_layout(annotations=annotations, xaxis=dict(title=dict(text='<b>← Classificação de Saúde do Cliente (Risco) →</b>'), side='bottom', automargin=True), yaxis=dict(title=dict(text='<b>← Classificação de Ticket (Valor Mensal) →</b>'), automargin=True), height=650, margin=dict(t=30, b=50, l=50, r=50))
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Ranking de Priorização de Contato")
    df_ranking = df_rfv.sort_values(by=['R_Score', 'V_Score'], ascending=[True, False]).copy()
    df_ranking_display = df_ranking[['cliente_id', 'segmento', 'valor_mensal', 'Fator_Risco', 'Categoria_Saude']].copy()
    df_ranking_display.columns = ['ID Cliente', 'Setor', 'Ticket Mensal (R$)', 'Total Falhas (SLA + Reclamações)', 'Status Estratégico']
    
    st.dataframe(df_ranking_display.style.background_gradient(cmap='Reds', subset=['Total Falhas (SLA + Reclamações)']).format({'Ticket Mensal (R$)': 'R$ {:.2f}'}), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# ABA 2: MONITOR INDIVIDUAL
# ------------------------------------------------------------------------------
with tab2:
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1: cliente_selecionado = st.selectbox("1. Selecione o Cliente:", sorted(df_atd['cliente_id'].unique()), key="cli_aba2")
    opcoes_metricas = {'pct_sla_cumprido': 'SLA Cumprido (%)', 'tempo_medio_resolucao_h': 'Tempo Médio de Resolução (h)', 'chamados_abertos': 'Chamados Abertos (Qtd)', 'reclamacoes_formais': 'Reclamações Formais (Qtd)'}
    with col_filtro2: metrica_selecionada = st.selectbox("2. Métrica a Observar:", list(opcoes_metricas.keys()), format_func=lambda x: opcoes_metricas[x])

    st.markdown("---")
    
    df_cli_atd = df_atd[df_atd['cliente_id'] == cliente_selecionado].sort_values('mes_ref_dt')
    df_cli_nps = df_nps[df_nps['cliente_id'] == cliente_selecionado].sort_values('mes_ref_dt')
    status_cliente = df_sit[df_sit['cliente_id'] == cliente_selecionado]['situacao'].values[0]
    cor_status = "red" if status_cliente == "Cancelado" else "green"
    qtd_detrator = len(df_cli_nps[df_cli_nps['classificacao_nps'] == 'Detrator'])
    
    mrr_cliente = df_cli[df_cli['cliente_id'] == cliente_selecionado]['valor_mensal'].values[0]
    mrr_formatado = f"R$ {mrr_cliente:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if status_cliente == 'Ativo':
        cat_saude = df_rfv[df_rfv['cliente_id'] == cliente_selecionado]['Categoria_Saude'].values[0]
        nota_saude = df_rfv[df_rfv['cliente_id'] == cliente_selecionado]['R_Score'].values[0]
        saude_display = f"{cat_saude} (Nota {nota_saude}/5)"
    else:
        saude_display = "Contrato Cancelado"

    # CORREÇÃO: Reinserção dos cards de MRR, Saúde e Detratores
    st.subheader(f"Perfil: Cliente {cliente_selecionado} - Status: :{cor_status}[{status_cliente}]")
    col_perfil1, col_perfil2, col_perfil3 = st.columns([1, 1.5, 1])
    with col_perfil1: st.metric("Receita Mensal (MRR)", mrr_formatado)
    with col_perfil2: st.metric("Saúde Estratégica", saude_display)
    with col_perfil3: st.metric("NPS: Vezes Detrator", f"{qtd_detrator} vezes")
    
    st.write("")
    st.subheader("Análise do Indicador de Atendimento")
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1: st.metric(f"Média do Cliente ({opcoes_metricas[metrica_selecionada]})", f"{df_cli_atd[metrica_selecionada].mean():.1f}")
    with col_kpi2: st.metric("Linha de Risco (Média de Cancelados)", f"{linhas_risco[metrica_selecionada]:.1f}")

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_cli_atd['mes_ref_dt'], y=df_cli_atd[metrica_selecionada], mode='lines+markers+text', name=f'Evolução', text=df_cli_atd[metrica_selecionada].round(1), textposition='top center', line=dict(width=3, color='#2B5B84')))
    fig2.add_trace(go.Scatter(x=[df_cli_atd['mes_ref_dt'].min(), df_cli_atd['mes_ref_dt'].max()], y=[linhas_risco[metrica_selecionada], linhas_risco[metrica_selecionada]], mode='lines', name='Linha de Risco', line=dict(color='red', width=2, dash='dash')))
    fig2.update_layout(xaxis_title='Mês', yaxis_title=opcoes_metricas[metrica_selecionada], template='plotly_white', hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 3: RADAR DE STRIKES
# ------------------------------------------------------------------------------
with tab3:
    st.markdown("Nesta aba, usamos a lógica de **Sinal Vigente**. Se o cliente teve problemas graves no passado, mas a última pesquisa NPS é Promotor e o SLA do último mês foi recuperado, os strikes dele foram **perdoados**. Só exibimos a foto do risco atual.")
    
    st.subheader("🎯 Quão bem este sinal separa o joio do trigo?")
    st.markdown("Um bom sinal precisa ter forte aderência em quem cancela e **baixo alarme falso** na base ativa atual.")
    
    col_pat1, col_pat2, col_pat3 = st.columns(3)
    
    with col_pat1:
        st.metric("Sinal de SLA Crítico", f"{padroes_churn['SLA']*100:.0f}% dos cancelados", f"Alarme Falso (Ativos com este sinal): {taxa_falso_alarme['SLA']*100:.1f}%", delta_color="inverse")
    with col_pat2:
        st.metric("Sinal de Reclamações", f"{padroes_churn['Reclamacao']*100:.0f}% dos cancelados", f"Alarme Falso (Ativos com este sinal): {taxa_falso_alarme['Reclamacao']*100:.1f}%", delta_color="inverse")
    with col_pat3:
        st.metric("Sinal Último NPS Detrator", f"{padroes_churn['NPS']*100:.0f}% dos cancelados", f"Alarme Falso (Ativos com este sinal): {taxa_falso_alarme['NPS']*100:.1f}%", delta_color="inverse")

    st.markdown("---")
    
    strikes_grafico = strikes[strikes['Total_Strikes'] > 0].sort_values('Total_Strikes', ascending=True).reset_index()
    
    if not strikes_grafico.empty:
        st.subheader("🚨 Painel de Strikes (Exclusivo para Problemas Ativos Hoje)")
        st.markdown(f"O gráfico agora é preciso: clientes como o **C061** (que deram NPS promotor recentemente) tiveram suas falhas antigas desconsideradas.")
        
        df_melt = strikes_grafico.melt(
            id_vars=['cliente_id', 'Total_Strikes'], 
            value_vars=['Strike 1 (SLA Crítico Atual)', 'Strike 2 (Lentidão Atual)', 'Strike 3 (Reclamação Recente)', 'Strike 4 (Último NPS Detrator)'], 
            var_name='Motivo da Falta', 
            value_name='Ocorreu'
        )
        df_melt = df_melt[df_melt['Ocorreu'] == 1]
        
        cor_strikes = {
            'Strike 1 (SLA Crítico Atual)': '#F1C40F',    
            'Strike 2 (Lentidão Atual)': '#E67E22',       
            'Strike 3 (Reclamação Recente)': '#E74C3C',    
            'Strike 4 (Último NPS Detrator)': '#8E44AD'    
        }

        fig_strikes = px.bar(
            df_melt, 
            y='cliente_id', 
            x='Ocorreu', 
            color='Motivo da Falta', 
            orientation='h',
            color_discrete_map=cor_strikes,
            title="Clientes Ativos com Múltiplos Problemas Não Resolvidos"
        )
        
        fig_strikes.update_layout(
            barmode='stack',
            xaxis_title="Quantidade de Problemas Simultâneos HOJE",
            yaxis_title="ID do Cliente",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            template="plotly_white",
            height=max(400, len(strikes_grafico) * 40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_strikes, use_container_width=True)
    else:
        st.success("🎉 Excelente notícia! Após limpar os falsos positivos, nenhum cliente ativo possui múltiplos problemas simultâneos não resolvidos hoje.")