import os
import urllib.parse

import pandas as pd
import pyodbc
from sqlalchemy import create_engine

# ==============================================================================
# CONFIGURAÇÕES DE CONEXÃO - SQL SERVER
# ==============================================================================
# O SQL Express local é uma instância nomeada: localhost\SQLEXPRESS.
# Pode ser sobrescrito pela variável de ambiente SQLSERVER_HOST.
SERVER = os.getenv("SQLSERVER_HOST", r"localhost\SQLEXPRESS")
DATABASE = 'holder'


def _odbc(database: str) -> str:
    """String ODBC com Autenticação Nativa do Windows (Trusted_Connection)."""
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={database};"
        f"Trusted_Connection=yes;"
    )


def garantir_banco() -> None:
    """Cria o banco de dados se ele ainda não existir (CREATE DATABASE exige autocommit)."""
    with pyodbc.connect(_odbc("master"), autocommit=True) as conexao:
        conexao.execute(f"IF DB_ID(N'{DATABASE}') IS NULL CREATE DATABASE [{DATABASE}]")


# Inicializa o motor de conexão
params = urllib.parse.quote_plus(_odbc(DATABASE))
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
    garantir_banco()
    print(f"Banco '{DATABASE}' pronto em {SERVER}.\n")
    
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