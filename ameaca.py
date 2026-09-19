import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Matriz de Ameaça Dupla", layout="wide")

@st.cache_data
def carregar_dados_dispersao():
    # 1. Carregamento dos dados
    df_cli = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='clientes')
    df_atd = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='atendimento_mensal')
    df_sit = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='situacao_clientes')

    # 2. Filtrar apenas clientes Ativos
    df_ativos = df_sit[df_sit['situacao'] == 'Ativo'][['cliente_id']]
    df_atd_ativos = df_atd[df_atd['cliente_id'].isin(df_ativos['cliente_id'])].copy()

    # 3. Calcular a média histórica de Uso e Resolução, e a soma de Problemas Críticos
    df_agg = df_atd_ativos.groupby('cliente_id').agg(
        uso_plataforma=('uso_plataforma_pct', 'mean'),
        tempo_resolucao=('tempo_medio_resolucao_h', 'mean'),
        chamados_criticos=('chamados_criticos', 'sum'),
        valor_mensal=('cliente_id', lambda x: df_cli.loc[df_cli['cliente_id'] == x.iloc[0], 'valor_mensal'].values[0])
    ).reset_index()

    # Como o tamanho da bolha não pode ser zero no Plotly, criamos uma coluna ajustada
    df_agg['tamanho_bolha'] = df_agg['chamados_criticos'] + 1 
    
    return df_agg

df_dados = carregar_dados_dispersao()

# ==============================================================================
# CÁLCULO DOS EIXOS (MEDIANAS) PARA DIVIDIR OS QUADRANTES
# ==============================================================================
mediana_uso = df_dados['uso_plataforma'].median()
mediana_tempo = df_dados['tempo_resolucao'].median()

# Classificação para colorir as bolhas
def classificar_quadrante(row):
    if row['uso_plataforma'] < mediana_uso and row['tempo_resolucao'] > mediana_tempo:
        return '🚨 Risco Máximo (Baixo Uso, Muita Lentidão)'
    elif row['uso_plataforma'] >= mediana_uso and row['tempo_resolucao'] > mediana_tempo:
        return '⚠️ Paciência em Teste (Usa muito, mas sofre com Lentidão)'
    elif row['uso_plataforma'] < mediana_uso and row['tempo_resolucao'] <= mediana_tempo:
        return '🧊 Desengajados (Atendimento Rápido, mas Não Usam)'
    else:
        return '⭐ Saudáveis (Alto Uso, Atendimento Rápido)'

df_dados['Status'] = df_dados.apply(classificar_quadrante, axis=1)

# ==============================================================================
# CONSTRUÇÃO DO DASHBOARD
# ==============================================================================
st.title("🎯 Matriz de Ameaça Dupla (Causa Raiz de Churn)")
st.markdown("Cruzamento das métricas mais críticas apontadas pela análise de dados. O **tamanho da bolha** representa a quantidade de **chamados críticos** acumulados pelo cliente.")

# 1. KPIs Rápidos
col1, col2, col3 = st.columns(3)
criticos = df_dados[df_dados['Status'] == '🚨 Risco Máximo (Baixo Uso, Muita Lentidão)']

with col1:
    st.metric("Total de Clientes Ativos", len(df_dados))
with col2:
    st.metric("Clientes no Quadrante Crítico", len(criticos), delta="- Foco de Resgate", delta_color="inverse")
with col3:
    st.metric("MRR Ameaçado pela Lentidão", f"R$ {criticos['valor_mensal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("---")

# 2. GRÁFICO DE DISPERSÃO (QUADRANTES)
fig = px.scatter(
    df_dados,
    x='uso_plataforma',
    y='tempo_resolucao',
    color='Status',
    size='tamanho_bolha',
    hover_name='cliente_id',
    hover_data={
        'tamanho_bolha': False, # Oculta a variável artificial
        'Status': False,
        'uso_plataforma': ':.1f',
        'tempo_resolucao': ':.1f',
        'chamados_criticos': True,
        'valor_mensal': ':,.2f'
    },
    color_discrete_map={
        '🚨 Risco Máximo (Baixo Uso, Muita Lentidão)': '#E74C3C', # Vermelho
        '⚠️ Paciência em Teste (Usa muito, mas sofre com Lentidão)': '#F39C12', # Laranja
        '🧊 Desengajados (Atendimento Rápido, mas Não Usam)': '#95A5A6', # Cinza
        '⭐ Saudáveis (Alto Uso, Atendimento Rápido)': '#2ECC71' # Verde
    }
)

# Adicionando as linhas divisórias baseadas na mediana da base ativa
fig.add_hline(y=mediana_tempo, line_dash="dash", line_color="gray", line_width=2)
fig.add_vline(x=mediana_uso, line_dash="dash", line_color="gray", line_width=2)

# Adicionando Fundo Colorido aos Quadrantes (Opcional para dar cara de "Matriz")
max_x, min_x = df_dados['uso_plataforma'].max() + 5, df_dados['uso_plataforma'].min() - 5
max_y, min_y = df_dados['tempo_resolucao'].max() + 5, max(0, df_dados['tempo_resolucao'].min() - 5)

# Fundo Vermelho (Canto Superior Esquerdo: Baixo Uso, Alto Tempo)
fig.add_shape(type="rect", x0=min_x, y0=mediana_tempo, x1=mediana_uso, y1=max_y, fillcolor="#FFCDD2", opacity=0.3, layer="below", line_width=0)
# Fundo Verde (Canto Inferior Direito: Alto Uso, Baixo Tempo)
fig.add_shape(type="rect", x0=mediana_uso, y0=min_y, x1=max_x, y1=mediana_tempo, fillcolor="#C8E6C9", opacity=0.3, layer="below", line_width=0)

# Customização de Layout
fig.update_layout(
    xaxis_title='Engajamento: Uso Médio da Plataforma (%) → (Quanto MAIOR, melhor)',
    yaxis_title='Atrito: Tempo Médio de Resolução (Horas) → (Quanto MENOR, melhor)',
    xaxis=dict(range=[min_x, max_x]),
    yaxis=dict(range=[min_y, max_y]),
    template='plotly_white',
    height=600,
    legend=dict(title='', orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# 3. LISTA DE AÇÃO
if not criticos.empty:
    st.subheader("📋 Lista de Resgate Imediato")
    st.markdown("Clientes mapeados no quadrante vermelho. Estão com o uso afundando e sofrendo com a maior lentidão do suporte.")
    
    df_tabela = criticos[['cliente_id', 'valor_mensal', 'uso_plataforma', 'tempo_resolucao', 'chamados_criticos']].copy()
    df_tabela = df_tabela.sort_values(by=['valor_mensal', 'tempo_resolucao'], ascending=[False, False])
    df_tabela.columns = ['ID Cliente', 'Ticket Mensal (R$)', 'Uso Plataforma (%)', 'Tempo Médio Resolução (h)', 'Total Problemas Críticos']
    
    st.dataframe(
        df_tabela.style.background_gradient(cmap='Reds', subset=['Tempo Médio Resolução (h)', 'Total Problemas Críticos'])
        .format({'Ticket Mensal (R$)': 'R$ {:.2f}', 'Uso Plataforma (%)': '{:.1f}%', 'Tempo Médio Resolução (h)': '{:.1f}h'}),
        use_container_width=True, hide_index=True
    )