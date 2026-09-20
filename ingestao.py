import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse

# ==============================================================================
# CONFIGURAÇÕES DE CONEXÃO - SQL SERVER
# ==============================================================================
# Instância nomeada padrão do SQL Server Express (instalador cria
# "SQLEXPRESS", não a instância default "localhost" pura).
SERVER = r'localhost\SQLEXPRESS'
DATABASE = 'holder'


def _string_conexao(database: str) -> str:
    params = urllib.parse.quote_plus(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={database};"
        f"Trusted_Connection=yes;"
    )
    return f"mssql+pyodbc:///?odbc_connect={params}"


def _garantir_banco_existe():
    """Cria o banco DATABASE se ele ainda não existir — evita que rodar
    ingestao.py numa instância recém-instalada (sem o banco 'holder' criado
    manualmente ainda) falhe logo na primeira conexão."""
    engine_master = create_engine(_string_conexao("master"), isolation_level="AUTOCOMMIT")
    with engine_master.connect() as conn:
        existe = conn.execute(
            text("SELECT 1 FROM sys.databases WHERE name = :nome"), {"nome": DATABASE}
        ).fetchone()
        if not existe:
            conn.execute(text(f"CREATE DATABASE [{DATABASE}]"))
            print(f"Banco '{DATABASE}' não existia — criado agora.")
    engine_master.dispose()


# ==============================================================================
# INGESTÃO DAS TABELAS
# ==============================================================================
def main():
    # O banco é garantido e o motor criado AQUI, não no nível do módulo:
    # antes, só importar este arquivo já conectava no `master` e podia
    # executar CREATE DATABASE — efeito colateral pesado e silencioso, que
    # tornava qualquer varredura de imports perigosa.
    _garantir_banco_existe()
    engine = create_engine(_string_conexao(DATABASE))

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
            
    engine.dispose()
    print("\nPipeline finalizado com sucesso.")

if __name__ == "__main__":
    main()