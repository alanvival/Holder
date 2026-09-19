import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Dashboard de Atendimento", layout="wide")
st.title("📊 Análise de Atendimento ao Cliente")
st.markdown("Selecione a métrica no menu lateral para atualizar o gráfico dinamicamente.")

# 2. CARREGAMENTO DOS DADOS
@st.cache_data
def carregar_dados():
    df = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='atendimento_mensal')
    df['mes_ref_dt'] = pd.to_datetime(df['mes_ref'], format='%Y-%m')
    return df

df = carregar_dados()

# 3. MAPEAMENTO DINÂMICO DE COLUNAS
# Dicionário apenas para deixar as colunas antigas mais bonitas. 
# As colunas novas não precisam estar aqui!
nomes_conhecidos = {
    'pct_sla_cumprido': 'SLA Cumprido (%)',
    'chamados_abertos': 'Total de Chamados Abertos (Qtd)',
    'chamados_criticos': 'Chamados Críticos (Qtd)',
    'tempo_medio_resolucao_h': 'Tempo Médio de Resolução (Horas)',
    'reclamacoes_formais': 'Reclamações Formais (Qtd)',
    'uso_plataforma_pct': 'Uso da Plataforma (%)',
    'dias_atraso_pagamento': 'Dias de Atraso no Pagamento (Qtd)',
    'reunioes_previstas': 'Reuniões Previstas (Qtd)',
    'reunioes_realizadas': 'Reuniões Realizadas (Qtd)'
}

# O "Pulo do Gato": Pega automaticamente TODAS as colunas que contêm números no Excel
colunas_numericas = df.select_dtypes(include=['int64', 'float64']).columns.tolist()

# Lista de colunas que são números, mas não queremos no gráfico (se houver)
colunas_ignoradas = ['cliente_id'] 

# Constrói as opções dinamicamente
opcoes_metricas = {}
for col in colunas_numericas:
    if col not in colunas_ignoradas:
        if col in nomes_conhecidos:
            # Se já conhecemos, usa o nome formatado e bonito
            opcoes_metricas[col] = nomes_conhecidos[col]
        else:
            # Se for uma coluna nova adicionada hoje no Excel, usa o próprio nome da coluna!
            opcoes_metricas[col] = col 

# 4. BARRA LATERAL (MENU INTERATIVO)
st.sidebar.header("⚙️ Configurações do Gráfico")

# Dropdown dinâmico
coluna_selecionada = st.sidebar.selectbox(
    "1. Selecione a Métrica:",
    options=list(opcoes_metricas.keys()),
    format_func=lambda x: opcoes_metricas[x] 
)

tipo_agrupamento = st.sidebar.radio(
    "2. Tipo de Cálculo Global:",
    options=['Média', 'Soma']
)

# 5. PROCESSAMENTO DOS DADOS COM BASE NA ESCOLHA
df_clean = df.dropna(subset=[coluna_selecionada])

if tipo_agrupamento == 'Média':
    df_agrupado = df_clean.groupby('mes_ref_dt')[coluna_selecionada].mean().reset_index()
else:
    df_agrupado = df_clean.groupby('mes_ref_dt')[coluna_selecionada].sum().reset_index()

df_agrupado = df_agrupado.sort_values('mes_ref_dt')

# 6. CRIAÇÃO DO GRÁFICO INTERATIVO (PLOTLY)
titulo_grafico = f"Evolução Mensal: {opcoes_metricas[coluna_selecionada]} ({tipo_agrupamento})"

fig = px.line(
    df_agrupado,
    x='mes_ref_dt',
    y=coluna_selecionada,
    markers=True,
    title=titulo_grafico,
    labels={'mes_ref_dt': 'Mês de Referência', coluna_selecionada: opcoes_metricas[coluna_selecionada]},
    template='plotly_white'
)

fig.update_traces(
    line=dict(width=4, color='#2B5B84'), 
    marker=dict(size=10, color='#E74C3C'),
    fill='tozeroy',
    fillcolor='rgba(43, 91, 132, 0.1)'
)
fig.update_layout(xaxis_tickformat='%b/%Y', hovermode="x unified")

# 7. EXIBIR NO DASHBOARD
st.plotly_chart(fig, use_container_width=True)

with st.expander("Ver dados agrupados em formato de tabela"):
    st.dataframe(df_agrupado.style.format({coluna_selecionada: "{:.2f}"}))