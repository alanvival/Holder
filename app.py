import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import textwrap
import urllib
import json
from sqlalchemy import create_engine # <- NOVA IMPORTAÇÃO PARA O BANCO DE DADOS

import score_risco as sr  # infra compartilhada: conexão, faixas, histórico (fScoreRisco)
import modelo_risco as mr  # motor de verdade: regressão logística treinada/validada (AUC~0.95, Brier~0.085)

st.set_page_config(page_title="Dashboard Executivo CS", layout="wide")

# Identidade visual da Globalsys (ver design-tokens.md na raiz do repo —
# fonte da verdade dos tokens). As fontes (Space Grotesk nos títulos,
# Montserrat no corpo) e as cores já vêm do tema nativo do Streamlit
# (.streamlit/config.toml, chaves font/headingFont/primaryColor) — isso é
# necessário porque st.dataframe renderiza a grade em canvas
# (glide-data-grid), não HTML, então CSS de página não alcança o texto das
# células/cabeçalhos de tabela; só a fonte do tema nativo se propaga lá.
# Este bloco cobre só o que o tema não tem: raio de borda dos cards/tabelas
# e formato de pílula nos botões.
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        white-space: normal !important;
        word-wrap: break-word !important;
        font-size: 1.7rem !important;
        line-height: 1.2 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 20px !important;
        overflow: hidden;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 50px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# CARREGAMENTO E PREPARAÇÃO DE DADOS (CACHE)
# ==============================================================================
@st.cache_data
def carregar_dados():
    # --- CONEXÃO COM O SQL SERVER LOCALHOST ---
    # Utilizando autenticação do Windows (Trusted_Connection=yes).
    # O driver 'ODBC Driver 17 for SQL Server' é o padrão mais comum.
    # Instância nomeada padrão do SQL Server Express: "SQLEXPRESS" (não a
    # instância default "localhost" pura). Connection string ODBC crua via
    # odbc_connect= (mesmo padrão de ingestao.py) — a barra invertida do nome
    # da instância não é confiável dentro da URL "mssql+pyodbc://host/db"
    # do SQLAlchemy (%5C falha com "Provedor de Pipes Nomeados: servidor não
    # encontrado" mesmo com o SQL Server rodando e acessível).
    params = urllib.parse.quote_plus(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        r"SERVER=localhost\SQLEXPRESS;"
        "DATABASE=holder;"
        "Trusted_Connection=yes;"
    )
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    
    # Lendo as tabelas do banco de dados no lugar das abas do Excel
    df_cli = pd.read_sql("SELECT * FROM dClientes", engine)
    df_atd = pd.read_sql("SELECT * FROM fAtendimento", engine)
    df_sit = pd.read_sql("SELECT * FROM dSituacao", engine)
    df_nps = pd.read_sql("SELECT * FROM fPesquisa", engine)
    
    # --- O RESTANTE DO CÓDIGO CONTINUA INTACTO A PARTIR DAQUI ---
    df_atd['mes_ref_dt'] = pd.to_datetime(df_atd['mes_ref'], format='%Y-%m')
    df_nps['mes_ref_dt'] = pd.to_datetime(df_nps['mes_ref'], format='%Y-%m')
    
    # Criação da métrica de abandono e limpeza
    df_atd['reunioes_ausentes'] = df_atd['reunioes_previstas'] - df_atd['reunioes_realizadas']
    df_atd = df_atd.drop(columns=['reunioes_previstas', 'reunioes_realizadas'])
    
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
        if row['V_Score'] >= 4 and row['R_Score'] <= 2: return 'Ação Imediata'
        elif row['V_Score'] >= 4 and row['R_Score'] >= 3: return 'Proteger e Expandir'
        elif row['V_Score'] <= 3 and row['R_Score'] <= 2: return 'Avaliar Fit'
        else: return 'Fluxo Normal'
    df_rfv['Categoria_Saude'] = df_rfv.apply(categorizar, axis=1)

    # --------------------------------------------------------------------------
    # PADRÃO DOS CANCELADOS (AGORA DINÂMICO)
    # --------------------------------------------------------------------------
    df_atd_canc = df_atd[df_atd['situacao'] == 'Cancelado'].copy()
    
    # Varre todas as colunas numéricas da aba de atendimento, excluindo IDs/Datas se houver
    colunas_excluidas = ['cliente_id', 'mes_ref', 'mes_ref_dt', 'mes_cancelamento']
    colunas_numericas = [col for col in df_atd.select_dtypes(include='number').columns if col not in colunas_excluidas]
    
    linhas_risco = {}
    for col in colunas_numericas:
        if col in ['reclamacoes_formais', 'reunioes_ausentes']:
            linhas_risco[col] = df_atd_canc[col].mean()
        else:
            linhas_risco[col] = df_atd_canc[col].median()
    
    # Assinatura de Churn (Últimos meses antes da saída)
    df_atd_canc['mes_canc_dt'] = pd.to_datetime(df_atd_canc['mes_cancelamento'], format='%Y-%m')
    df_atd_canc['meses_para_canc'] = (df_atd_canc['mes_canc_dt'].dt.year - df_atd_canc['mes_ref_dt'].dt.year) * 12 + (df_atd_canc['mes_canc_dt'].dt.month - df_atd_canc['mes_ref_dt'].dt.month)
    ultimos_meses_canc = df_atd_canc[(df_atd_canc['meses_para_canc'] > 0) & (df_atd_canc['meses_para_canc'] <= 4)]
    
    total_canc = len(df_cancelados)
    pct_canc_sla = len(ultimos_meses_canc[ultimos_meses_canc['pct_sla_cumprido'] <= linhas_risco.get('pct_sla_cumprido', 80.0)]['cliente_id'].unique()) / total_canc if total_canc > 0 else 0
    pct_canc_rec = len(ultimos_meses_canc[ultimos_meses_canc['reclamacoes_formais'] > 0]['cliente_id'].unique()) / total_canc if total_canc > 0 else 0
    
    df_nps_canc = df_nps.merge(df_sit[['cliente_id', 'situacao', 'mes_cancelamento']], on='cliente_id', how='inner')
    df_nps_canc = df_nps_canc[df_nps_canc['situacao'] == 'Cancelado']
    df_nps_canc['mes_canc_dt'] = pd.to_datetime(df_nps_canc['mes_cancelamento'], format='%Y-%m')
    df_nps_canc['meses_para_canc'] = (df_nps_canc['mes_canc_dt'].dt.year - df_nps_canc['mes_ref_dt'].dt.year) * 12 + (df_nps_canc['mes_canc_dt'].dt.month - df_nps_canc['mes_ref_dt'].dt.month)
    ultimos_meses_nps = df_nps_canc[(df_nps_canc['meses_para_canc'] > 0) & (df_nps_canc['meses_para_canc'] <= 6)]
    pct_canc_detrator = len(ultimos_meses_nps[ultimos_meses_nps['classificacao_nps'] == 'Detrator']['cliente_id'].unique()) / total_canc if total_canc > 0 else 0

    padroes_churn = {'SLA': pct_canc_sla, 'Reclamacao': pct_canc_rec, 'NPS': pct_canc_detrator}

    # --------------------------------------------------------------------------
    # NOVO SISTEMA DE STRIKES (Focado na Realidade ATUAL / Sem memória longa)
    # --------------------------------------------------------------------------
    df_atd_ativos = df_atd_ativos.sort_values(by=['cliente_id', 'mes_ref_dt'])
    df_nps_ativos = df_nps[df_nps['cliente_id'].isin(df_ativos['cliente_id'])].sort_values(by=['cliente_id', 'mes_ref_dt'])
    
    ultimo_atd = df_atd_ativos.groupby('cliente_id').tail(1).set_index('cliente_id')
    ultimo_nps = df_nps_ativos.groupby('cliente_id').tail(1).set_index('cliente_id')
    
    max_mes_ativos = df_atd_ativos['mes_ref_dt'].max()
    reclamacoes_recentes = df_atd_ativos[df_atd_ativos['mes_ref_dt'] >= (max_mes_ativos - pd.DateOffset(months=1))].groupby('cliente_id')['reclamacoes_formais'].sum()

    strikes = pd.DataFrame(index=df_ativos['cliente_id'])
    
    strikes['Strike 1 (SLA Crítico Atual)'] = (ultimo_atd['pct_sla_cumprido'] <= linhas_risco.get('pct_sla_cumprido', 80.0)).astype(int)
    strikes['Strike 2 (Lentidão Atual)'] = (ultimo_atd['tempo_medio_resolucao_h'] >= linhas_risco.get('tempo_medio_resolucao_h', 24.0)).astype(int)
    strikes['Strike 3 (Reclamação Recente)'] = (reclamacoes_recentes > 0).astype(int).reindex(strikes.index).fillna(0)
    strikes['Strike 4 (Último NPS Detrator)'] = (ultimo_nps['classificacao_nps'] == 'Detrator').astype(int).reindex(strikes.index).fillna(0)

    colunas_strikes = ['Strike 1 (SLA Crítico Atual)', 'Strike 2 (Lentidão Atual)', 'Strike 3 (Reclamação Recente)', 'Strike 4 (Último NPS Detrator)']
    strikes['Total_Strikes'] = strikes[colunas_strikes].sum(axis=1)
    
    taxa_falso_alarme = {
        'SLA': strikes['Strike 1 (SLA Crítico Atual)'].mean(),
        'Reclamacao': strikes['Strike 3 (Reclamação Recente)'].mean(),
        'NPS': strikes['Strike 4 (Último NPS Detrator)'].mean()
    }
    
    return df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco, padroes_churn, strikes, taxa_falso_alarme

df_cli, df_atd, df_sit, df_nps, df_rfv, linhas_risco, padroes_churn, strikes, taxa_falso_alarme = carregar_dados()

# ==============================================================================
# O CÓDIGO ABAIXO PERMANECE EXATAMENTE IGUAL (A PARTIR DE st.title)
# ==============================================================================

# ==============================================================================
# ESTRUTURA DE ABAS (TABS)
# ==============================================================================
st.title("Dashboard Integrado de Customer Success")

tab1, tab2, tab3 = st.tabs([
    "Matriz Estratégica (Visão Geral)",
    "Monitor Individual (Análise de Risco)",
    "Score de Risco (Preditivo)",
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
    st.subheader("Ranking de Priorização de Contato")
    df_ranking = df_rfv.sort_values(by=['R_Score', 'V_Score'], ascending=[True, False]).copy()
    df_ranking_display = df_ranking[['cliente_id', 'segmento', 'valor_mensal', 'Fator_Risco', 'Categoria_Saude']].copy()
    df_ranking_display.columns = ['ID Cliente', 'Setor', 'Ticket Mensal (R$)', 'Total Falhas (SLA + Reclamações)', 'Status Estratégico']
    
    st.dataframe(df_ranking_display.style.background_gradient(cmap='Reds', subset=['Total Falhas (SLA + Reclamações)']).format({'Ticket Mensal (R$)': 'R$ {:.2f}'}), use_container_width=True, hide_index=True)

        # Filtra clientes com pelo menos 1 strike e ordena do pior (mais strikes) para o melhor
    strikes_grafico = strikes[strikes['Total_Strikes'] > 0].sort_values('Total_Strikes', ascending=False).reset_index()
    
    if not strikes_grafico.empty:
        st.subheader("Painel de Strikes (Exclusivo para Problemas Ativos Hoje)")
        
        # Prepara o dataframe para a tabela visual
        df_tabela = strikes_grafico[[
            'cliente_id', 
            'Total_Strikes', 
            'Strike 1 (SLA Crítico Atual)', 
            'Strike 2 (Lentidão Atual)', 
            'Strike 3 (Reclamação Recente)', 
            'Strike 4 (Último NPS Detrator)'
        ]].copy()
        
        # Renomeia colunas para a interface
        df_tabela.columns = [
            'ID Cliente', 
            'Total de Infrações', 
            'SLA Crítico', 
            'Lentidão na Resolução', 
            'Reclamação Recente', 
            'NPS Detrator'
        ]
        
        # Mapeia 1 para círculo vermelho e 0 para vazio
        colunas_alerta = ['SLA Crítico', 'Lentidão na Resolução', 'Reclamação Recente', 'NPS Detrator']
        for col in colunas_alerta:
            df_tabela[col] = df_tabela[col].map({1: '🔴', 0: ''})
            
        # Exibe o dataframe com formatação no total de infrações
        st.dataframe(
            df_tabela.style.background_gradient(cmap='Reds', subset=['Total de Infrações']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("🎉 Excelente notícia! Após limpar os falsos positivos, nenhum cliente ativo possui múltiplos problemas simultâneos não resolvidos hoje.")

# ------------------------------------------------------------------------------
# ABA 2: MONITOR INDIVIDUAL
# ------------------------------------------------------------------------------
with tab2:
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1: 
        cliente_selecionado = st.selectbox("1. Selecione o Cliente:", sorted(df_atd['cliente_id'].unique()), key="cli_aba2")
    
    # Dicionário de nomes atualizado (sem as antigas, adicionando a nova)
    nomes_conhecidos = {
        'uso_plataforma_pct': 'Uso da Plataforma (%)',
        'pct_sla_cumprido': 'SLA Cumprido (%)',
        'tempo_medio_resolucao_h': 'Tempo Médio de Resolução (h)',
        'dias_atraso_pagamento': 'Dias de Atraso no Pagamento',
        'reclamacoes_formais': 'Reclamações Formais (Qtd)',
        'chamados_abertos': 'Chamados Abertos (Qtd)',
        'chamados_criticos': 'Chamados Críticos (Qtd)',
        'chamados_reabertos': 'Chamados Reabertos (Qtd)',
        'chamados_dentro_sla': 'Chamados Dentro do SLA (Qtd)',
        'reunioes_ausentes': 'Faltas em Reuniões (Qtd)'
    }
    
    colunas_excluidas = ['cliente_id', 'mes_ref', 'mes_ref_dt', 'mes_cancelamento']
    colunas_disponiveis = [col for col in df_atd.select_dtypes(include='number').columns if col not in colunas_excluidas]
    
    opcoes_metricas = {}
    for col in colunas_disponiveis:
        if col in nomes_conhecidos:
            opcoes_metricas[col] = nomes_conhecidos[col]
        else:
            opcoes_metricas[col] = col.replace('_', ' ').title()
    
    with col_filtro2: 
        metrica_selecionada = st.selectbox("2. Métrica a Observar:", list(opcoes_metricas.keys()), format_func=lambda x: opcoes_metricas[x])

    st.markdown("---")
    
    df_cli_atd = df_atd[df_atd['cliente_id'] == cliente_selecionado].sort_values('mes_ref_dt')
    df_cli_nps = df_nps[df_nps['cliente_id'] == cliente_selecionado].sort_values('mes_ref_dt')
    status_cliente = df_sit[df_sit['cliente_id'] == cliente_selecionado]['situacao'].values[0]
    cor_status = "red" if status_cliente == "Cancelado" else "green"
    
    if not df_cli_nps.empty:
        ultimo_nps = df_cli_nps.iloc[-1]['classificacao_nps']
    else:
        ultimo_nps = "Sem pesquisa"
    
    mrr_cliente = df_cli[df_cli['cliente_id'] == cliente_selecionado]['valor_mensal'].values[0]
    mrr_formatado = f"R$ {mrr_cliente:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if status_cliente == 'Ativo':
        cat_saude = df_rfv[df_rfv['cliente_id'] == cliente_selecionado]['Categoria_Saude'].values[0]
        nota_saude = df_rfv[df_rfv['cliente_id'] == cliente_selecionado]['R_Score'].values[0]
        saude_display = f"{cat_saude} (Nota {nota_saude}/5)"
    else:
        saude_display = "Contrato Cancelado"

    st.subheader(f"Perfil: Cliente {cliente_selecionado} - Status: :{cor_status}[{status_cliente}]")
    col_perfil1, col_perfil2, col_perfil3 = st.columns([1, 1.5, 1])
    with col_perfil1: st.metric("Receita Mensal (MRR)", mrr_formatado)
    with col_perfil2: st.metric("Saúde Estratégica", saude_display)
    with col_perfil3: st.metric("Último NPS", ultimo_nps)
    
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

    metricas_inversas = ['uso_plataforma_pct', 'pct_sla_cumprido', 'chamados_dentro_sla']
    
    if metrica_selecionada in metricas_inversas:
        st.caption("Aviso: Quanto menor este indicador, maior o risco de cancelamento.")
    elif metrica_selecionada in nomes_conhecidos:
        st.caption("Aviso: Quanto maior este indicador, maior o risco de cancelamento.")
    else:
        st.caption("Aviso: Nova métrica detectada. O gráfico plota o valor do cliente vs. a mediana da base cancelada para avaliação de desvio padrão.")

# ------------------------------------------------------------------------------
# ABA 3: SCORE DE RISCO (PREDITIVO) — regressão logística treinada e
# validada contra os cancelamentos reais (AUC~0.95, Brier~0.085 — ver
# testar_modelo_risco.py), não um score de pesos escolhidos à mão.
# Histórico salvo em SQL Server (fScoreRisco) por modelo_risco.py —
# rodar `python modelo_risco.py` pra treinar/atualizar antes de abrir esta
# aba pela primeira vez (ou depois que houver cancelamentos novos).
# ------------------------------------------------------------------------------
with tab3:
    @st.cache_data(ttl=600)
    def _carregar_score_atual():
        # Lê do histórico já salvo (mês mais recente) em vez de recalcular
        # na hora — mais rápido, e é exatamente o valor persistido pelo job
        # mensal (modelo_risco.salvar_historico_mes), não um recorte à parte.
        hist = sr.carregar_historico()
        if hist.empty:
            return []
        mes_mais_recente = hist["mes_ref"].max()
        ativos_ids = set(df_sit[df_sit["situacao"] == "Ativo"]["cliente_id"])
        linhas = hist[(hist["mes_ref"] == mes_mais_recente) & (hist["cliente_id"].isin(ativos_ids))]
        resultados = []
        for _, r in linhas.iterrows():
            resultados.append({
                "cliente_id": r["cliente_id"], "mes_ref": r["mes_ref"],
                "score_precoce": r["score_precoce"], "score_confirmado": r["score_confirmado"],
                "risco_percentual": r["risco_percentual"], "faixa": r["faixa"],
                "sinais_detalhados": json.loads(r["sinais_detalhados"]),
            })
        resultados.sort(key=lambda r: r["risco_percentual"], reverse=True)
        return resultados

    @st.cache_data(ttl=600)
    def _carregar_historico_score():
        return sr.carregar_historico()

    resultados = _carregar_score_atual()
    historico_score = _carregar_historico_score()

    if not resultados:
        st.warning("Sem score calculado ainda. Rode `python score_risco.py` no terminal pra popular o histórico.")
    else:
        df_score = pd.DataFrame(resultados)
        df_score = df_score.merge(df_cli[['cliente_id', 'plano', 'porte', 'segmento']], on='cliente_id', how='left')

        mes_atual = df_score['mes_ref'].iloc[0]
        mes_anterior_ref = (pd.Period(mes_atual, freq='M') - 1).strftime('%Y-%m')

        # Tendência: compara o risco% deste mês com o do mês anterior salvo
        # no histórico — alimenta a seta subiu/caiu/estável e o alerta de
        # "cruzou de faixa".
        hist_anterior = historico_score[historico_score['mes_ref'] == mes_anterior_ref][['cliente_id', 'risco_percentual', 'faixa']]
        hist_anterior = hist_anterior.rename(columns={'risco_percentual': 'risco_anterior', 'faixa': 'faixa_anterior'})
        df_score = df_score.merge(hist_anterior, on='cliente_id', how='left')

        def _tendencia(row):
            if pd.isna(row.get('risco_anterior')):
                return '—'
            delta = row['risco_percentual'] - row['risco_anterior']
            if delta > 3:
                return '↑ subindo'
            if delta < -3:
                return '↓ caindo'
            return '→ estável'
        df_score['tendencia'] = df_score.apply(_tendencia, axis=1)
        df_score['cruzou_faixa'] = df_score.apply(
            lambda r: bool(pd.notna(r.get('faixa_anterior')) and r['faixa_anterior'] != r['faixa']), axis=1
        )
        df_score['estagio_predominante'] = df_score.apply(
            lambda r: 'Precoce' if r['score_precoce'] > r['score_confirmado'] else 'Confirmado', axis=1
        )

        st.caption(f"Score calculado com base no mês mais recente disponível: **{mes_atual}** · {len(df_score)} clientes ativos avaliados.")

        # --- Filtros -----------------------------------------------------
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            faixas_sel = st.multiselect("Faixa de risco", ['Crítico', 'Em risco', 'Atenção', 'Saudável'],
                                         default=['Crítico', 'Em risco', 'Atenção', 'Saudável'])
        with col_f2:
            planos_sel = st.multiselect("Plano", sorted(df_score['plano'].dropna().unique()), default=None)
        with col_f3:
            segmentos_sel = st.multiselect("Segmento", sorted(df_score['segmento'].dropna().unique()), default=None)
        with col_f4:
            estagio_sel = st.multiselect("Estágio predominante", ['Precoce', 'Confirmado'], default=None)

        df_filtrado = df_score[df_score['faixa'].isin(faixas_sel)]
        if planos_sel:
            df_filtrado = df_filtrado[df_filtrado['plano'].isin(planos_sel)]
        if segmentos_sel:
            df_filtrado = df_filtrado[df_filtrado['segmento'].isin(segmentos_sel)]
        if estagio_sel:
            df_filtrado = df_filtrado[df_filtrado['estagio_predominante'].isin(estagio_sel)]

        modo = st.radio("Modo de visualização", ["Lista ranqueada", "Cards por faixa", "Linha do tempo (cliente)"], horizontal=True)

        cores_faixa = {'Crítico': '#E74C3C', 'Em risco': '#F5B041', 'Atenção': '#F9E79F', 'Saudável': '#A9DFBF'}

        # --- Modo 1: Lista ranqueada --------------------------------------
        if modo == "Lista ranqueada":
            st.subheader(f"{len(df_filtrado)} cliente(s) — ordenado por risco decrescente")
            for _, r in df_filtrado.iterrows():
                alerta = " 🔔 cruzou de faixa" if r['cruzou_faixa'] else ""
                icone_estagio = "👁️" if r['estagio_predominante'] == 'Precoce' else "🚨"
                with st.expander(f"{icone_estagio} **{r['cliente_id']}** — {r['risco_percentual']:.0f}% · {r['faixa']} · {r['tendencia']}{alerta}"):
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.metric("Risco de cancelamento", f"{r['risco_percentual']:.0f}%")
                        st.write(f"**Faixa:** {r['faixa']}")
                        st.write(f"**Estágio predominante:** {r['estagio_predominante']}")
                        st.write(f"**Tendência (vs. mês anterior):** {r['tendencia']}")
                        st.write(f"**Plano/Porte/Segmento:** {r['plano']} · {r['porte']} · {r['segmento']}")
                    with col_b:
                        sinais = r['sinais_detalhados']
                        nomes = {
                            'atraso_pagamento': 'Atraso de pagamento', 'chamados_criticos': 'Chamados críticos',
                            'sla_cumprido': 'SLA cumprido', 'uso_plataforma': 'Uso da plataforma',
                            'tempo_resolucao': 'Tempo de resolução',
                            'reclamacoes': 'Reclamações', 'nps': 'NPS',
                        }
                        contrib = {nomes.get(k, k): v.get('contribuicao', 0) or 0 for k, v in sinais.items()}
                        fig_expl = go.Figure(go.Bar(
                            x=list(contrib.values()), y=list(contrib.keys()), orientation='h',
                            marker_color=['#0156FC' if k in ('atraso_pagamento', 'chamados_criticos') else '#1D1DDB' for k in sinais.keys()],
                        ))
                        fig_expl.update_layout(
                            height=220, margin=dict(l=0, r=10, t=10, b=10),
                            xaxis=dict(range=[0, 100], title='contribuição pro score (0-100)'),
                            template='plotly_white',
                        )
                        st.plotly_chart(fig_expl, use_container_width=True)
                        if sinais.get('nps', {}).get('classificacao_recente'):
                            st.caption(f"Último NPS: {sinais['nps']['classificacao_recente']}")
                        baseline_atraso = sinais.get('atraso_pagamento', {}).get('baseline_pessoal')
                        if baseline_atraso is not None:
                            st.caption(
                                f"Atraso atual: {sinais['atraso_pagamento']['valor_atual']} dias "
                                f"(baseline pessoal: {baseline_atraso:.1f})"
                            )

        # --- Modo 2: Cards por faixa ---------------------------------------
        elif modo == "Cards por faixa":
            cols = st.columns(4)
            for col, faixa in zip(cols, ['Crítico', 'Em risco', 'Atenção', 'Saudável']):
                with col:
                    subset = df_filtrado[df_filtrado['faixa'] == faixa]
                    st.markdown(f"##### {faixa} ({len(subset)})")
                    for _, r in subset.sort_values('risco_percentual', ascending=False).iterrows():
                        st.markdown(
                            f"<div style='background:{cores_faixa[faixa]}22;border-left:4px solid {cores_faixa[faixa]};"
                            f"border-radius:8px;padding:8px 10px;margin-bottom:6px;'>"
                            f"<b>{r['cliente_id']}</b> — {r['risco_percentual']:.0f}%<br>"
                            f"<span style='font-size:12px;color:#555;'>{r['tendencia']}</span></div>",
                            unsafe_allow_html=True,
                        )

        # --- Modo 3: Linha do tempo individual ------------------------------
        else:
            cliente_timeline = st.selectbox("Cliente:", sorted(df_filtrado['cliente_id'].unique()) or sorted(df_score['cliente_id'].unique()))
            hist_cliente = historico_score[historico_score['cliente_id'] == cliente_timeline].sort_values('mes_ref')
            if hist_cliente.empty:
                st.info("Sem histórico salvo pra esse cliente ainda.")
            else:
                fig_tl = go.Figure()
                fig_tl.add_trace(go.Scatter(
                    x=hist_cliente['mes_ref'], y=hist_cliente['risco_percentual'],
                    mode='lines+markers+text', text=hist_cliente['risco_percentual'].round(0),
                    textposition='top center', line=dict(width=3, color='#0156FC'), name='Risco %',
                ))
                for lo, hi, nome in sr.FAIXAS:
                    fig_tl.add_hrect(y0=lo, y1=min(hi, 100), fillcolor=cores_faixa[nome], opacity=0.15, line_width=0)
                fig_tl.update_layout(
                    xaxis_title='Mês', yaxis_title='Risco de cancelamento (%)', yaxis=dict(range=[0, 100]),
                    template='plotly_white', hovermode='x unified',
                )
                st.plotly_chart(fig_tl, use_container_width=True)
                st.caption("Faixas de fundo: verde = Saudável, amarelo claro = Atenção, laranja = Em risco, vermelho = Crítico.")

        st.markdown("---")
        with st.expander("Sobre este score (metodologia)"):
            log_treinos = mr.carregar_log_treinos()
            if not log_treinos.empty:
                ultimo = log_treinos.iloc[0]
                linha_validacao = f"**AUC = {ultimo['auc']:.3f}** · **Brier = {ultimo['brier']:.3f}** (validação cruzada 5-fold, treinado em {pd.to_datetime(ultimo['treinado_em']).strftime('%d/%m/%Y')}, {int(ultimo['n_amostras'])} amostras)."
            else:
                linha_validacao = "Sem log de treino ainda — rode `python modelo_risco.py`."
            st.markdown(f"""
            **Regressão logística treinada e validada** contra os cancelamentos reais da base —
            não é um score de pesos escolhidos à mão. {linha_validacao}

            - **Alvo do treino:** cada mês de cada cliente cancelado vira `y=1` só se estiver dentro
              dos 3 meses imediatamente antes do cancelamento (meses mais antigos são excluídos do
              treino, não viram `y=0`) — o modelo aprende "esse mês parece pré-cancelamento", não
              "esse cliente é do tipo que cancela".
            - **Variáveis:** SLA cumprido, tempo de resolução, reclamações, uso da plataforma,
              atraso de pagamento, chamados críticos e NPS mais recente conhecido.
            - **Explicabilidade:** cada sinal no detalhe do cliente mostra coeficiente × desvio —
              "precoce"/"confirmado" agora é só rótulo de apresentação (atraso/críticos vs. os
              demais), não um segundo cálculo paralelo.

            Faixas: Saudável (0–29%) · Atenção (30–54%) · Em risco (55–74%) · Crítico (75–100%).
            Backtest retroativo nos 22 clientes já cancelados: ver `testar_modelo_risco.py`.
            """)