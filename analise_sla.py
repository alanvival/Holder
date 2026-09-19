import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configuração de estilo geral para deixar o gráfico mais moderno
plt.style.use('ggplot')
plt.rcParams['font.family'] = 'sans-serif'

def plot_sla_mensal(excel_path: str):
    # 1. Leitura dos dados
    print("Carregando dados da aba 'atendimento_mensal'...")
    df = pd.read_excel(excel_path, sheet_name='atendimento_mensal')
    
    # 2. Limpeza de dados
    # Remover meses em que o cliente não abriu chamado (pct_sla_cumprido fica nulo)
    df_clean = df.dropna(subset=['pct_sla_cumprido']).copy()
    
    # Converter a coluna mes_ref (string 'YYYY-MM') para formato DateTime
    df_clean['mes_ref_dt'] = pd.to_datetime(df_clean['mes_ref'], format='%Y-%m')
    
    # 3. Agrupamento (Análise)
    # Calcula a média do pct_sla_cumprido de todos os clientes, agrupado por mês
    sla_mensal = df_clean.groupby('mes_ref_dt')['pct_sla_cumprido'].mean().reset_index()
    sla_mensal = sla_mensal.sort_values('mes_ref_dt')
    
    # ==============================================================================
    # CRIAÇÃO DO GRÁFICO ESTILIZADO
    # ==============================================================================
    fig, ax = plt.subplots(figsize=(14, 7), facecolor='#F7F9FC')
    ax.set_facecolor('#F7F9FC')
    
    # Plotagem da linha principal
    ax.plot(
        sla_mensal['mes_ref_dt'], 
        sla_mensal['pct_sla_cumprido'], 
        marker='o', 
        markersize=8,
        linewidth=3, 
        color='#2B5B84', 
        label='Média Geral de SLA Cumprido (%)'
    )
    
    # Área sombreada abaixo da linha para dar noção de volume/preenchimento
    ax.fill_between(
        sla_mensal['mes_ref_dt'], 
        sla_mensal['pct_sla_cumprido'], 
        alpha=0.2, 
        color='#2B5B84'
    )
    
    # Linha de Meta Simbólica (ex: 90%)
    meta_sla = 90.0
    ax.axhline(
        y=meta_sla, 
        color='#E74C3C', 
        linestyle='--', 
        linewidth=2, 
        alpha=0.8, 
        label=f'Meta de SLA ({meta_sla}%)'
    )
    
    # Rótulos de dados: exibir o percentual acima de cada ponto no gráfico
    for x, y in zip(sla_mensal['mes_ref_dt'], sla_mensal['pct_sla_cumprido']):
        ax.annotate(
            f"{y:.1f}%",
            (x, y),
            textcoords="offset points",
            xytext=(0, 10),
            ha='center',
            fontsize=10,
            fontweight='bold',
            color='#333333'
        )
    
    # ==============================================================================
    # FORMATAÇÃO E DESIGN DO GRÁFICO
    # ==============================================================================
    ax.set_title('Evolução Mensal: Média de SLA Cumprido', fontsize=18, fontweight='bold', pad=20, color='#1A1A1A')
    ax.set_ylabel('SLA Cumprido (%)', fontsize=12, fontweight='bold', labelpad=15, color='#333333')
    ax.set_xlabel('Mês de Referência', fontsize=12, fontweight='bold', labelpad=15, color='#333333')
    
    # Formatação do Eixo X (Datas)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b/%Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    fig.autofmt_xdate(rotation=45) # Rotaciona os meses para não encavalarem
    
    # Ajuste dos limites do Eixo Y (para dar respiro visual ao redor da linha)
    min_y = max(0, sla_mensal['pct_sla_cumprido'].min() - 5)
    ax.set_ylim(min_y, 105)
    
    # Remoção das bordas superior e direita para um visual mais limpo (Tufte style)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    # Grid sutil apenas no eixo Y
    ax.grid(True, axis='y', linestyle=':', color='#DDDDDD', alpha=0.8)
    ax.grid(False, axis='x')
    
    # Posicionamento da Legenda
    ax.legend(loc='lower right', frameon=True, facecolor='white', edgecolor='#CCCCCC', fontsize=11)
    
    plt.tight_layout()
    
    # Salvar e Mostrar
    arquivo_saida = 'grafico_sla_mensal.png'
    plt.savefig(arquivo_saida, dpi=300, bbox_inches='tight')
    print(f"✓ Gráfico salvo como '{arquivo_saida}'.")
    
    plt.show()

if __name__ == "__main__":
    plot_sla_mensal("INOVAAPPS_base_de_dados.xlsx")