import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ==============================================================================
# 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS
# ==============================================================================
print("Carregando e cruzando os dados...")
df_cli = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='clientes')
df_atd = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='atendimento_mensal')
df_nps = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='pesquisas_nps')
df_sit = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='situacao_clientes')

# Agrupar histórico de atendimento por cliente
df_atd_agg = df_atd.groupby('cliente_id').agg(
    total_reclamacoes=('reclamacoes_formais', 'sum'),
    avg_resolucao=('tempo_medio_resolucao_h', 'mean'),
    avg_sla=('pct_sla_cumprido', 'mean')
).reset_index()

# Cruzar tabelas: Clientes + Atendimento + Situação
df_master = df_cli[['cliente_id', 'valor_mensal']].merge(df_atd_agg, on='cliente_id', how='left')
df_master = df_master.merge(df_sit[['cliente_id', 'situacao']], on='cliente_id', how='left')

# Criar a regra de Perfil do Cliente (Bons, Ruins, Medianos)
# Baseado na mediana (metade dos clientes está acima, metade abaixo)
mediana_ticket = df_master['valor_mensal'].median()
mediana_reclamacoes = df_master['total_reclamacoes'].median()

def categorizar_perfil(row):
    if row['valor_mensal'] >= mediana_ticket and row['total_reclamacoes'] <= mediana_reclamacoes:
        return 'Ótimo (Ticket Alto, Pouca Rec.)'
    elif row['valor_mensal'] <= mediana_ticket and row['total_reclamacoes'] > mediana_reclamacoes:
        return 'Risco (Ticket Baixo, Muita Rec.)'
    else:
        return 'Mediano / Em Observação'

df_master['perfil_cliente'] = df_master.apply(categorizar_perfil, axis=1)

# Prepara dados de NPS apenas para os Cancelados (Comportamento pré-cancelamento)
df_nps_cancelados = df_nps.merge(df_sit[['cliente_id', 'situacao']], on='cliente_id')
df_nps_cancelados = df_nps_cancelados[
    (df_nps_cancelados['situacao'] == 'Cancelado') & 
    (df_nps_cancelados['classificacao_nps'] != 'Sem resposta')
]
contagem_nps = df_nps_cancelados['classificacao_nps'].value_counts().reset_index()
contagem_nps.columns = ['NPS', 'Quantidade']

# ==============================================================================
# 2. CONSTRUÇÃO DO PAINEL GRÁFICO (DASHBOARD)
# ==============================================================================
sns.set_theme(style="whitegrid", rc={"axes.spines.right": False, "axes.spines.top": False})
fig, axes = plt.subplots(2, 2, figsize=(18, 12), facecolor='#F4F6F9')
fig.suptitle('Análise Comportamental e Motivos de Cancelamento (Churn)', fontsize=20, fontweight='bold', y=0.98)

# ---------------------------------------------------------
# GRÁFICO 1: Matriz de Perfil de Clientes (Dispersão)
# ---------------------------------------------------------
ax1 = axes[0, 0]
sns.scatterplot(
    data=df_master, x='valor_mensal', y='total_reclamacoes', 
    hue='situacao', style='perfil_cliente', 
    palette={'Ativo': '#2E86C1', 'Cancelado': '#E74C3C'}, 
    s=120, alpha=0.8, ax=ax1
)
# Linhas desenhando os quadrantes baseados na mediana
ax1.axvline(mediana_ticket, color='gray', linestyle='--', alpha=0.5)
ax1.axhline(mediana_reclamacoes, color='gray', linestyle='--', alpha=0.5)
ax1.set_title('Matriz de Risco: Ticket vs Total de Reclamações', fontsize=14, fontweight='bold')
ax1.set_xlabel('Valor Mensal (Ticket em R$)')
ax1.set_ylabel('Total de Reclamações Formais')
ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0., fontsize=9)

# ---------------------------------------------------------
# GRÁFICO 2: Comportamento de NPS Pré-Cancelamento
# ---------------------------------------------------------
ax2 = axes[0, 1]
# Ordenando as cores para refletir o semáforo de NPS
cores_nps = {'Detrator': '#E74C3C', 'Neutro': '#F1C40F', 'Promotor': '#2ECC71'}
sns.barplot(data=contagem_nps, x='NPS', y='Quantidade', palette=cores_nps, ax=ax2)
ax2.set_title('Pesquisas Respondidas ANTES do Cancelamento', fontsize=14, fontweight='bold')
ax2.set_xlabel('Classificação do NPS')
ax2.set_ylabel('Meses Totais em cada Status')
for p in ax2.patches:
    ax2.annotate(f"{int(p.get_height())} meses", (p.get_x() + p.get_width() / 2., p.get_height()),
                 ha='center', va='bottom', fontsize=11, fontweight='bold')

# ---------------------------------------------------------
# GRÁFICO 3: Impacto do Tempo de Resolução no Churn
# ---------------------------------------------------------
ax3 = axes[1, 0]
sns.boxplot(data=df_master, x='situacao', y='avg_resolucao', 
            palette={'Ativo': '#AED6F1', 'Cancelado': '#F5B7B1'}, width=0.5, ax=ax3)
ax3.set_title('Tempo Médio de Resolução (Horas): Ativos vs Cancelados', fontsize=14, fontweight='bold')
ax3.set_xlabel('Situação Atual do Cliente')
ax3.set_ylabel('Média Histórica de Resolução (h)')

# ---------------------------------------------------------
# GRÁFICO 4: Impacto da Quebra de SLA no Churn
# ---------------------------------------------------------
ax4 = axes[1, 1]
sns.boxplot(data=df_master, x='situacao', y='avg_sla', 
            palette={'Ativo': '#AED6F1', 'Cancelado': '#F5B7B1'}, width=0.5, ax=ax4)
# Adiciona a meta visual
ax4.axhline(90, color='red', linestyle=':', label='Meta 90% SLA')
ax4.set_title('% de SLA Cumprido: Ativos vs Cancelados', fontsize=14, fontweight='bold')
ax4.set_xlabel('Situação Atual do Cliente')
ax4.set_ylabel('Média Histórica de SLA (%)')
ax4.legend()

# Ajuste de layout para nada ficar sobreposto
plt.tight_layout(rect=[0, 0, 0.9, 0.95]) # Dá espaço para a legenda lateral
plt.savefig('dashboard_churn_clientes.png', dpi=300, bbox_inches='tight')
print("✓ Painel de Análise gerado com sucesso: 'dashboard_churn_clientes.png'")
plt.show()