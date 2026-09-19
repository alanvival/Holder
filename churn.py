import pandas as pd
import plotly.express as px

def analisar_fatores_churn():
    print("Iniciando varredura analítica de métricas...")
    
    # 1. Carregar dados
    df_atd = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='atendimento_mensal')
    df_sit = pd.read_excel('INOVAAPPS_base_de_dados.xlsx', sheet_name='situacao_clientes')
    
    # Criar uma métrica derivada vital: Taxa de Presença em Reuniões
    df_atd['taxa_presenca_reuniao_pct'] = df_atd.apply(
        lambda x: (x['reunioes_realizadas'] / x['reunioes_previstas'] * 100) if x['reunioes_previstas'] > 0 else 100.0, 
        axis=1
    )
    
    # Colunas que serão analisadas
    metricas = [
        'chamados_abertos', 'chamados_criticos', 'chamados_reabertos', 
        'chamados_dentro_sla', 'pct_sla_cumprido', 'tempo_medio_resolucao_h', 
        'reclamacoes_formais', 'uso_plataforma_pct', 'dias_atraso_pagamento', 
        'taxa_presenca_reuniao_pct'
    ]
    
    # 2. Consolidação da Vida do Cliente (Média Histórica)
    df_agg = df_atd.groupby('cliente_id')[metricas].mean().reset_index()
    
    # 3. Cruzamento com Situação
    df_master = df_agg.merge(df_sit[['cliente_id', 'situacao']], on='cliente_id', how='inner')
    
    # Criar Variável Alvo para matemática (Cancelado = 1, Ativo = 0)
    df_master['churn_binario'] = (df_master['situacao'] == 'Cancelado').astype(int)
    
    # ==========================================================================
    # CÁLCULO DE CORRELAÇÃO E IMPACTO
    # ==========================================================================
    correlacoes = []
    for col in metricas:
        corr = df_master[col].corr(df_master['churn_binario'])
        correlacoes.append({'Métrica': col, 'Impacto_Matematico': corr})
        
    df_corr = pd.DataFrame(correlacoes)
    
    # Limpeza de nomes para o gráfico
    nomes_amigaveis = {
        'uso_plataforma_pct': 'Queda no Uso da Plataforma',
        'pct_sla_cumprido': 'Queda no Cumprimento de SLA',
        'taxa_presenca_reuniao_pct': 'Abandono de Reuniões (Ghosting)',
        'chamados_dentro_sla': 'Menos Chamados no Prazo',
        'reclamacoes_formais': 'Aumento de Reclamações',
        'tempo_medio_resolucao_h': 'Lentidão na Resolução',
        'chamados_reabertos': 'Retrabalho (Chamados Reabertos)',
        'dias_atraso_pagamento': 'Atraso de Pagamentos',
        'chamados_criticos': 'Volume de Problemas Críticos',
        'chamados_abertos': 'Volume Total de Chamados'
    }
    
    df_corr['Nome Amigável'] = df_corr['Métrica'].map(nomes_amigaveis)
    
    # Separar o que atrai o churn do que afasta o churn para o gráfico
    df_corr['Direção'] = df_corr['Impacto_Matematico'].apply(lambda x: 'Gatilho de Cancelamento (Sobe antes do Churn)' if x > 0 else 'Fator de Retenção (Cai antes do Churn)')
    df_corr['Força Absoluta'] = df_corr['Impacto_Matematico'].abs()
    df_corr = df_corr.sort_values(by='Força Absoluta', ascending=True)

    # ==========================================================================
    # RAIO-X: COMPARATIVO MÉDIO
    # ==========================================================================
    comparativo = df_master.groupby('situacao')[metricas].mean().T
    comparativo.columns = ['Média dos Ativos', 'Média dos Cancelados']
    comparativo['Variação (Piora)'] = ((comparativo['Média dos Cancelados'] - comparativo['Média dos Ativos']) / comparativo['Média dos Ativos']) * 100
    
    print("\n" + "="*80)
    print("🕵️ RAIO-X DEFINITIVO: COMPORTAMENTO MÉDIO (ATIVOS VS CANCELADOS)")
    print("="*80)
    pd.options.display.float_format = '{:.2f}'.format
    print(comparativo.sort_values(by='Variação (Piora)', ascending=False))
    print("="*80 + "\n")

    # ==========================================================================
    # GRÁFICO (PLOTLY)
    # ==========================================================================
    fig = px.bar(
        df_corr, 
        x='Impacto_Matematico', 
        y='Nome Amigável', 
        color='Direção',
        color_discrete_map={
            'Gatilho de Cancelamento (Sobe antes do Churn)': '#E74C3C', # Vermelho
            'Fator de Retenção (Cai antes do Churn)': '#2B5B84'        # Azul
        },
        title='Análise de Causa Raiz: O que mais influencia o Cancelamento?'
    )
    
    fig.update_layout(
        xaxis_title="← Protege o Cliente (Retenção) | Força de Impacto | Expulsa o Cliente (Churn) →",
        yaxis_title="",
        template="plotly_white",
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Adiciona uma linha no zero
    fig.add_vline(x=0, line_width=2, line_color="black")
    
    fig.show()

if __name__ == "__main__":
    analisar_fatores_churn()