import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import textwrap

st.set_page_config(page_title="Matriz de Risco Heatmap", layout="wide")

@st.cache_data
def carregar_e_calcular_rfv():
    # 1. Carregamento
    df_cli = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='clientes')
    df_atd = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='atendimento_mensal')
    df_sit = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='situacao_clientes')

    df_master = df_cli.merge(df_sit, on='cliente_id', how='inner')
    df_ativos = df_master[df_master['situacao'] == 'Ativo'].copy()
    
    df_atd_ativos = df_atd[df_atd['cliente_id'].isin(df_ativos['cliente_id'])].copy()

    # 2. Cálculo de Quebras e Reclamações
    df_atd_ativos['quebra_sla'] = df_atd_ativos['pct_sla_cumprido'] < 80.0
    agrupamento = df_atd_ativos.groupby('cliente_id').agg(
        meses_abaixo_sla=('quebra_sla', 'sum'),
        total_reclamacoes=('reclamacoes_formais', 'sum'),
        uso_medio=('uso_plataforma_pct', 'mean')
    ).reset_index()

    rfv = df_ativos[['cliente_id', 'valor_mensal', 'segmento']].merge(agrupamento, on='cliente_id', how='left')

    # 3. Definição dos Scores (1 a 5)
    # V_Score: 1 = Ticket Baixo | 5 = Ticket Muito Alto
    rfv['V_Score'] = pd.qcut(rfv['valor_mensal'], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    
    # R_Score: 1 = Saúde Ruim (Alto Risco) | 5 = Saúde Excelente (Baixo Risco)
    rfv['Fator_Risco'] = rfv['meses_abaixo_sla'] + rfv['total_reclamacoes']
    rfv['R_Rank'] = rfv['Fator_Risco'].rank(method='first', ascending=False)
    rfv['R_Score'] = pd.qcut(rfv['R_Rank'], 5, labels=[1, 2, 3, 4, 5]).astype(int)

    return rfv

df_rfv = carregar_e_calcular_rfv()

# ==============================================================================
# PREPARAÇÃO DA MATRIZ 5x5 (HEATMAP)
# ==============================================================================
# Eixos nominais (Rótulos de 1 a 5)
x_labels = ['1 - Saúde Crítica', '2 - Saúde Ruim', '3 - Saúde Média', '4 - Saúde Boa', '5 - Saúde Excelente']
y_labels = ['1 - Ticket Muito Baixo', '2 - Ticket Baixo', '3 - Ticket Médio', '4 - Ticket Alto', '5 - Ticket Muito Alto']

# Matrizes vazias para preencher o gráfico
z_colors = []      # Controla a cor do quadrado (0=Verde, 1=Amarelo, 2=Vermelho)
hover_text = []    # O texto que aparece ao passar o mouse
annotations = []   # O texto fixo que fica dentro do quadrado

# Lógica de varredura (Y de 1 a 5, X de 1 a 5)
for y in range(1, 6):
    z_row = []
    hover_row = []
    for x in range(1, 6):
        # Filtra os clientes que caíram neste cruzamento exato
        clientes_quadrante = df_rfv[(df_rfv['R_Score'] == x) & (df_rfv['V_Score'] == y)]
        qtd = len(clientes_quadrante)
        mrr_total = clientes_quadrante['valor_mensal'].sum()
        
        # Formatação da lista de clientes para caber na caixinha preta do hover
        lista_ids = clientes_quadrante['cliente_id'].tolist()
        if qtd > 0:
            clientes_str = ", ".join(lista_ids)
            # Quebra a linha a cada 40 caracteres para não ficar uma tripa infinita
            clientes_formatados = "<br>".join(textwrap.wrap(clientes_str, width=40))
        else:
            clientes_formatados = "Nenhum cliente"

        # ---------------------------------------------------------
        # DEFINIÇÃO DA COR DA CÉLULA (ESTILO SEMÁFORO)
        # ---------------------------------------------------------
        # Z=0 (Verde), Z=1 (Amarelo), Z=2 (Vermelho)
        if y >= 4 and x <= 2:
            cor_z = 2  # ALERTA: Ticket Alto e Saúde Crítica (Vermelho)
        elif y <= 2 and x >= 4:
            cor_z = 0  # SEGURO: Ticket Baixo e Saúde Boa (Verde)
        elif x >= 4:
            cor_z = 0  # SEGURO: Saúde Boa (Verde)
        elif x <= 2 and y <= 2:
            cor_z = 1  # ATENÇÃO: Ticket Baixo e Saúde Crítica (Amarelo)
        elif x == 3:
            cor_z = 1  # ATENÇÃO: Saúde Média (Amarelo)
        else:
            cor_z = 1  # ATENÇÃO: Casos intermediários (Amarelo)
            
        z_row.append(cor_z)
        
        # ---------------------------------------------------------
        # MONTAGEM DO HOVER (TEXTO AO PASSAR O MOUSE)
        # ---------------------------------------------------------
        mrr_formatado = f"R$ {mrr_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        hover_content = (
            f"<b>Ticket:</b> Classe {y}<br>"
            f"<b>Saúde:</b> Classe {x}<br>"
            f"<b>Soma do Ticket (MRR):</b> {mrr_formatado}<br>"
            f"<b>Total de Clientes:</b> {qtd}<br><br>"
            f"<b>Clientes neste quadro:</b><br>{clientes_formatados}"
        )
        hover_row.append(hover_content)
        
        # ---------------------------------------------------------
        # TEXTO FIXO NO QUADRADO
        # ---------------------------------------------------------
        if qtd > 0:
            texto_celula = f"<b>{qtd}</b> clientes<br>({mrr_formatado})"
        else:
            texto_celula = "-"
            
        annotations.append(
            dict(
                x=x_labels[x-1], y=y_labels[y-1],
                text=texto_celula,
                showarrow=False,
                font=dict(color="black" if cor_z != 2 else "white", size=12)
            )
        )
        
    z_colors.append(z_row)
    hover_text.append(hover_row)

# ==============================================================================
# CONSTRUÇÃO DO DASHBOARD
# ==============================================================================
st.title("🎯 Matriz de Risco Operacional vs Valor")
st.markdown("Deixe o mouse sobre qualquer quadro para ver os clientes classificados nele e a receita (MRR) aglomerada.")

# Criando o Heatmap
fig = go.Figure(data=go.Heatmap(
    z=z_colors,
    x=x_labels,
    y=y_labels,
    customdata=hover_text,
    hovertemplate="%{customdata}<extra></extra>", # <extra></extra> remove caixas secundárias indesejadas
    colorscale=[
        [0.0, '#A9DFBF'], # 0 = Verde (Seguro)
        [0.5, '#F9E79F'], # 1 = Amarelo (Atenção)
        [1.0, '#E74C3C']  # 2 = Vermelho (Perigo)
    ],
    showscale=False, # Oculta a barra de cores lateral (já é intuitivo)
    xgap=3, # Espaçamento entre os blocos como na sua imagem
    ygap=3
))

# Adiciona o texto de Qtd e MRR dentro dos blocos
fig.update_layout(
    annotations=annotations,
    xaxis=dict(
        title=dict(
            text='<b>← Classificação de Saúde do Cliente (Risco) →</b>', 
            font=dict(size=14)
        ), 
        side='bottom'
    ),
    yaxis=dict(
        title=dict(
            text='<b>← Classificação de Ticket (Valor Mensal) →</b>', 
            font=dict(size=14)
        )
    ),
    height=700,
    margin=dict(t=30, b=50, l=50, r=50)
)

st.plotly_chart(fig, use_container_width=True)