import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import textwrap

st.set_page_config(page_title="Dashboard Executivo CS", layout="wide")

# Força o Streamlit a quebrar a linha nos Cards (st.metric) em vez de cortar o texto
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        white-space: normal !important;
        word-wrap: break-word !important;
        font-size: 1.7rem !important; /* Reduz levemente a fonte para caber melhor */
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
    
    df_atd = df_atd.merge(df_sit[['cliente_id', 'situacao']], on='cliente_id', how='left')
    
    df_master = df_cli.merge(df_sit, on='cliente_id', how='inner')
    df_ativos = df_master[df_master['situacao'] == 'Ativo'].copy()
    
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

    df_cancelados = df_atd[df_atd['situacao'] == 'Cancelado']
    linhas_risco = {
        'pct_sla_cumprido': df_cancelados['pct_sla_cumprido'].median(),
        'tempo_medio_resolucao_h': df_cancelados['tempo_medio_resolucao_h'].median(),
        'chamados_abertos': df_cancelados['chamados_abertos'].median(),
        'reclamacoes_formais': df_cancelados['reclamacoes_formais'].mean()
    }
    
    return df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco

df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco = carregar_dados()

# ==============================================================================
# ESTRUTURA DE ABAS (TABS)
# ==============================================================================
st.title("🎯 Dashboard Integrado de Customer Success")

tab1, tab2 = st.tabs(["📊 Matriz Estratégica (Visão Geral)", "🔍 Monitor Individual (Análise de Risco)"])

# ------------------------------------------------------------------------------
# ABA 1: MATRIZ DE RISCO (HEATMAP) E RANKING
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("Deixe o mouse sobre qualquer quadro para ver os clientes classificados nele e a receita (MRR) aglomerada.")
    
    x_labels = ['1 - Saúde Crítica', '2 - Saúde Ruim', '3 - Saúde Média', '4 - Saúde Boa', '5 - Saúde Excelente']
    y_labels = ['1 - Ticket Muito Baixo', '2 - Ticket Baixo', '3 - Ticket Médio', '4 - Ticket Alto', '5 - Ticket Muito Alto']

    z_colors, hover_text, annotations = [], [], []

    for y in range(1, 6):
        z_row, hover_row = [], []
        for x in range(1, 6):
            clientes_quadrante = df_rfv[(df_rfv['R_Score'] == x) & (df_rfv['V_Score'] == y)]
            qtd = len(clientes_quadrante)
            mrr_total = clientes_quadrante['valor_mensal'].sum()
            
            lista_ids = clientes_quadrante['cliente_id'].tolist()
            if qtd > 0:
                clientes_formatados = "<br>".join(textwrap.wrap(", ".join(lista_ids), width=40))
            else:
                clientes_formatados = "Nenhum cliente"

            if y >= 4 and x <= 2: cor_z = 2
            elif y <= 2 and x >= 4: cor_z = 0
            elif x >= 4: cor_z = 0
            elif x <= 2 and y <= 2: cor_z = 1
            elif x == 3: cor_z = 1
            else: cor_z = 1
                
            z_row.append(cor_z)
            
            mrr_formatado = f"R$ {mrr_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            hover_content = (
                f"<b>Ticket:</b> Classe {y}<br>"
                f"<b>Saúde:</b> Classe {x}<br>"
                f"<b>Soma do Ticket (MRR):</b> {mrr_formatado}<br>"
                f"<b>Total de Clientes:</b> {qtd}<br><br>"
                f"<b>Clientes neste quadro:</b><br>{clientes_formatados}"
            )
            hover_row.append(hover_content)
            
            texto_celula = f"<b>{qtd}</b> clientes<br>({mrr_formatado})" if qtd > 0 else "-"
            annotations.append(
                dict(x=x_labels[x-1], y=y_labels[y-1], text=texto_celula, showarrow=False, 
                     font=dict(color="black" if cor_z != 2 else "white"))
            )
            
        z_colors.append(z_row)
        hover_text.append(hover_row)

    fig1 = go.Figure(data=go.Heatmap(
        z=z_colors, x=x_labels, y=y_labels, customdata=hover_text,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=[[0.0, '#A9DFBF'], [0.5, '#F9E79F'], [1.0, '#E74C3C']],
        showscale=False, xgap=3, ygap=3
    ))

    fig1.update_layout(
        annotations=annotations,
        xaxis=dict(title=dict(text='<b>← Classificação de Saúde do Cliente (Risco) →</b>'), side='bottom', automargin=True),
        yaxis=dict(title=dict(text='<b>← Classificação de Ticket (Valor Mensal) →</b>'), automargin=True),
        height=650, margin=dict(t=30, b=50, l=50, r=50),
        autosize=True
    )

    st.plotly_chart(fig1, use_container_width=True)

    # --- TABELA DE RANKING DE PRIORIZAÇÃO ---
    st.markdown("---")
    st.subheader("📋 Ranking de Priorização de Contato")
    st.markdown("Clientes ordenados pelo nível de urgência: **Maior risco associado à maior receita** no topo, até os clientes mais saudáveis e de menor ticket.")

    df_ranking = df_rfv.sort_values(by=['R_Score', 'V_Score'], ascending=[True, False]).copy()
    
    df_ranking_display = df_ranking[['cliente_id', 'segmento', 'valor_mensal', 'Fator_Risco', 'Categoria_Saude']].copy()
    df_ranking_display.columns = ['ID Cliente', 'Setor', 'Ticket Mensal (R$)', 'Total Falhas (SLA + Reclamações)', 'Status Estratégico']
    
    st.dataframe(
        df_ranking_display.style.background_gradient(cmap='Reds', subset=['Total Falhas (SLA + Reclamações)'])
        .format({'Ticket Mensal (R$)': 'R$ {:.2f}'}),
        use_container_width=True,
        hide_index=True
    )

# ------------------------------------------------------------------------------
# ABA 2: MONITOR INDIVIDUAL DE RISCO
# ------------------------------------------------------------------------------
with tab2:
    st.markdown("Selecione um cliente específico para cruzar seu comportamento histórico com as linhas de risco.")
    
    col_filtro1, col_filtro2 = st.columns(2)
    lista_clientes = sorted(df_atd['cliente_id'].unique())
    with col_filtro1:
        cliente_selecionado = st.selectbox("1. Selecione o Cliente:", lista_clientes)
        
    opcoes_metricas = {
        'pct_sla_cumprido': 'SLA Cumprido (%)',
        'tempo_medio_resolucao_h': 'Tempo Médio de Resolução (h)',
        'chamados_abertos': 'Chamados Abertos (Qtd)',
        'reclamacoes_formais': 'Reclamações Formais (Qtd)'
    }
    with col_filtro2:
        metrica_selecionada = st.selectbox("2. Métrica a Observar:", list(opcoes_metricas.keys()), format_func=lambda x: opcoes_metricas[x])

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

    st.subheader(f"Perfil: Cliente {cliente_selecionado} - Status: :{cor_status}[{status_cliente}]")
    
    # AJUSTE NAS COLUNAS: A coluna central (Saúde) agora tem mais espaço (1.5x maior que as outras)
    col_perfil1, col_perfil2, col_perfil3 = st.columns([1, 1.5, 1])
    
    with col_perfil1:
        st.metric("Receita Mensal (MRR)", mrr_formatado)
    with col_perfil2:
        st.metric("Saúde Estratégica", saude_display)
    with col_perfil3:
        st.metric("NPS: Vezes Detrator", f"{qtd_detrator} vezes")

    st.write("")

    st.subheader("Análise do Indicador de Atendimento")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        media_metrica = df_cli_atd[metrica_selecionada].mean()
        st.metric(f"Média do Cliente ({opcoes_metricas[metrica_selecionada]})", f"{media_metrica:.1f}" if pd.notna(media_metrica) else "N/A")
    with col_kpi2:
        limite = linhas_risco[metrica_selecionada]
        st.metric("Linha de Risco (Média de Cancelados)", f"{limite:.1f}")

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df_cli_atd['mes_ref_dt'], y=df_cli_atd[metrica_selecionada], mode='lines+markers+text',
        name=f'Evolução {cliente_selecionado}', text=df_cli_atd[metrica_selecionada].round(1),
        textposition='top center', line=dict(width=3, color='#2B5B84'), marker=dict(size=8)
    ))
    fig2.add_trace(go.Scatter(
        x=[df_cli_atd['mes_ref_dt'].min(), df_cli_atd['mes_ref_dt'].max()],
        y=[linhas_risco[metrica_selecionada], linhas_risco[metrica_selecionada]],
        mode='lines', name='Média de Risco (Contratos Cancelados)',
        line=dict(color='red', width=2, dash='dash')
    ))

    alerta_text = "⚠️ Alerta: Quanto menor o SLA, maior o risco." if metrica_selecionada == 'pct_sla_cumprido' else "⚠️ Alerta: Quanto maior este valor, maior o risco."
    st.caption(alerta_text)

    fig2.update_layout(
        xaxis_title='Mês', yaxis_title=opcoes_metricas[metrica_selecionada],
        template='plotly_white', hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        autosize=True
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Histórico de Satisfação (NPS)")
    if not df_cli_nps.empty:
        df_show_nps = df_cli_nps[['mes_ref', 'nota_nps', 'classificacao_nps']].copy()
        
        def cor_detrator(val):
            color = 'red' if val == 'Detrator' else ('green' if val == 'Promotor' else 'orange')
            return f'color: {color}; font-weight: bold'
            
        st.dataframe(df_show_nps.style.map(cor_detrator, subset=['classificacao_nps']), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma pesquisa de NPS registrada para este cliente.")