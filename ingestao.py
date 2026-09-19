import pandas as pd
from sqlalchemy import create_engine
import urllib

# ==============================================================================
# CONFIGURAÇÕES DE CONEXÃO - SQL SERVER
# ==============================================================================
# Geralmente o SQL Express local é acessado desta forma:
SERVER = r'localhost' 
DATABASE = 'holder'

# Cria a string ODBC utilizando a Autenticação Nativa do Windows (Trusted_Connection)
params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)

# Inicializa o motor de conexão
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# ==============================================================================
# INGESTÃO DAS TABELAS
# ==============================================================================
def main():
    excel_file = "INOVAAPPS_base_de_dados.xlsx"
    
    # Mapeamento estrito solicitado: aba de origem -> tabela de destino
    pipeline_tables = {
        "clientes": "dClientes",
        "atendimento_mensal": "fAtendimento",
        "pesquisas_nps": "fPesquisa",
        "situacao_clientes": "dSituacao"
    }
    
    print("Iniciando pipeline de ingestão via Pandas/SQLAlchemy...\n")
    
    for sheet, table_name in pipeline_tables.items():
        print(f"-> Processando aba '{sheet}'...")
        
        try:
            # Leitura da aba específica mantendo as colunas originais
            df = pd.read_excel(excel_file, sheet_name=sheet)
            
            # Gravação no SQL Server:
            # if_exists="replace" -> Recria a tabela a cada execução
            # index=False         -> Não insere o índice do Pandas como coluna no SQL
            df.to_sql(name=table_name, con=engine, if_exists="replace", index=False)
            
            print(f"   ✓ Sucesso! {len(df)} registros gravados na tabela '{table_name}'.")
        except Exception as e:
            print(f"   ❌ Erro ao gravar a tabela '{table_name}': {e}")
            
    print("\nPipeline finalizado com sucesso.")

if __name__ == "__main__":
    main()