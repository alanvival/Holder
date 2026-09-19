import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Matriz de Ameaça e Triagem", layout="wide")

@st.cache_data
def carregar_dados_dispersao():
    df_cli = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='clientes')
    df_atd = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='atendimento_mensal')
    df_sit = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='situacao_clientes')

    df_ativos = df_sit[df_sit['situacao'] == 'Ativo'][['cliente_id']]
    df_atd_ativos = df_atd[df_atd['cliente_id'].isin(df_ativos['cliente_id'])].copy()

    df_agg = df_atd_ativos.groupby('cliente_id').agg(
        uso_plataforma=('uso_plataforma_pct', 'mean'),
        tempo_resolucao=('tempo_medio_resolucao_h', 'mean'),
        chamados_criticos=('chamados_criticos', 'sum'),
        valor_mensal=('cliente_id', lambda x: df_cli.loc[df_cli['cliente_id'] == x.iloc[0], 'valor_mensal'].values[0])
    ).reset_index()

    df_agg['tamanho_bolha'] = df_agg['chamados_criticos'] + 1 
    
    return df_agg

df_dados = carregar_dados_dispersao()

# ==============================================================================
# CÁLCULO DE EIXOS (MEDIANAS) E TRIAGEM FINANCEIRA
# ==============================================================================
mediana_uso = df_dados['uso_plataforma'].median()
mediana_tempo = df_dados['tempo_resolucao'].median()
mediana_ticket = df_dados['valor_mensal'].median()

def classificar_quadrante(row):
    if row['uso_plataforma'] < mediana_uso and row['tempo_resolucao'] > mediana_tempo:
        return 'Risco Máximo (Ameaça de Churn)'
    elif row['uso_plataforma'] >= mediana_uso and row['tempo_resolucao'] > mediana_tempo:
        return 'Paciência em Teste (Lentidão)'
    elif row['uso_plataforma'] < mediana_uso and row['tempo_resolucao'] <= mediana_tempo:
        return 'Desengajados (Rápido, mas sem uso)'
    else:
        return 'Saudáveis'

def avaliar_esforco_resgate(row):
    if row['Status'] == 'Risco Máximo (Ameaça de Churn)':
        if row['valor_mensal'] >= mediana_ticket:
            return '🔥 Resgate Prioritário (Alto Ticket)'
        else:
            return '🧊 Deixar Ir / Avaliar Fit (Baixo Ticket)'
    return 'Não se aplica'

df_dados['Status'] = df_dados.apply(classificar_quadrante, axis=1)
df_dados['Decisao_Estrategica'] = df_dados.apply(avaliar_esforco_resgate, axis=1)

# ==============================================================================
# DASHBOARD
# ==============================================================================
st.title("🎯 Triagem de Churn: Esforço de CS vs Retorno (MRR)")
st.markdown("O fundo do gráfico indica a ameaça de cancelamento. A **cor e intensidade da bolha** indicam o peso do cliente no seu faturamento.")

# 1. KPIs Rápidos
criticos_prioritarios = df_dados[df_dados['Decisao_Estrategica'] == '🔥 Resgate Prioritário (Alto Ticket)']
criticos_descartaveis = df_dados[df_dados['Decisao_Estrategica'] == '🧊 Deixar Ir / Avaliar Fit (Baixo Ticket)']

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total de Clientes no Quadrante Vermelho", len(criticos_prioritarios) + len(criticos_descartaveis))
with col2:
    st.metric("Devem ser Salvos (Ticket Alto)", len(criticos_prioritarios), delta="Resgate Urgente", delta_color="inverse")
with col3:
    st.metric("Podem Cancelar (Ticket Baixo)", len(criticos_descartaveis), delta="Economia de Esforço", delta_color="normal")

st.markdown("---")

# 2. GRÁFICO DE DISPERSÃO (Cores pelo Ticket)
fig = px.scatter(
    df_dados,
    x='uso_plataforma',
    y='tempo_resolucao',
    color='valor_mensal', # A cor agora mapeia quem paga mais
    color_continuous_scale='Greens', # Clientes mais escuros = Mais dinheiro
    size='tamanho_bolha',
    hover_name='cliente_id',
    hover_data={
        'tamanho_bolha': False,
        'uso_plataforma': ':.1f',
        'tempo_resolucao': ':.1f',
        'chamados_criticos': True,
        'valor_mensal': ':,.2f',
        'Decisao_Estrategica': True
    }
)

fig.add_hline(y=mediana_tempo, line_dash="dash", line_color="gray", line_width=2)
fig.add_vline(x=mediana_uso, line_dash="dash", line_color="gray", line_width=2)

max_x, min_x = df_dados['uso_plataforma'].max() + 5, df_dados['uso_plataforma'].min() - 5
max_y, min_y = df_dados['tempo_resolucao'].max() + 5, max(0, df_dados['tempo_resolucao'].min() - 5)

fig.add_shape(type="rect", x0=min_x, y0=mediana_tempo, x1=mediana_uso, y1=max_y, fillcolor="#FFCDD2", opacity=0.3, layer="below", line_width=0)
fig.add_shape(type="rect", x0=mediana_uso, y0=min_y, x1=max_x, y1=mediana_tempo, fillcolor="#C8E6C9", opacity=0.3, layer="below", line_width=0)

fig.update_layout(
    xaxis_title='Engajamento: Uso Médio da Plataforma (%) →',
    yaxis_title='Atrito: Tempo Médio de Resolução (Horas) →',
    xaxis=dict(range=[min_x, max_x]),
    yaxis=dict(range=[min_y, max_y]),
    template='plotly_white',
    height=600,
    coloraxis_colorbar=dict(title="Ticket (R$)")
)

st.plotly_chart(fig, use_container_width=True)

# 3. TABELA DE TRIAGEM
df_triagem = df_dados[df_dados['Status'] == 'Risco Máximo (Ameaça de Churn)'].copy()

if not df_triagem.empty:
    st.subheader("📋 Mesa de Triagem (Apenas Clientes no Quadrante Vermelho)")
    
    df_show = df_triagem[['cliente_id', 'Decisao_Estrategica', 'valor_mensal', 'uso_plataforma', 'tempo_resolucao', 'chamados_criticos']].copy()
    df_show = df_show.sort_values(by=['valor_mensal'], ascending=[False])
    df_show.columns = ['ID Cliente', 'Recomendação do Sistema', 'Ticket Mensal (R$)', 'Uso (%)', 'Resolução (h)', 'Problemas Críticos']
    
    def cor_decisao(val):
        if 'Resgate' in val: return 'color: white; background-color: #E74C3C; font-weight: bold'
        elif 'Deixar' in val: return 'color: black; background-color: #E5E7E9'
        return ''

    st.dataframe(
        df_show.style.map(cor_decisao, subset=['Recomendação do Sistema'])
        .format({'Ticket Mensal (R$)': 'R$ {:.2f}', 'Uso (%)': '{:.1f}%', 'Resolução (h)': '{:.1f}h'}),
        use_container_width=True, hide_index=True
    )