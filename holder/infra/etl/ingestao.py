"""
Ingestão: carrega a planilha do desafio no modelo dimensional do SQL Server.

É a origem de tudo que o dashboard e o score de risco leem. Roda com:

    python -m holder.infra.etl.ingestao

A leitura da planilha e o mapa de tabelas não moram mais aqui: vêm do
adaptador de Excel e do adaptador de SQL Server, que são a fonte única de
cada um. Antes, este arquivo tinha sua própria string ODBC (uma de três
cópias), seu próprio mapa aba→tabela e um caminho de planilha relativo ao
diretório de onde o processo foi iniciado.
"""
from __future__ import annotations

from sqlalchemy import text

from ..dados import adaptador_excel, conexao
from ..dados.adaptador_sqlserver import TABELAS


def _garantir_banco_existe() -> None:
    """Cria o banco `holder` se ele ainda não existir — evita que rodar a
    ingestão numa instância recém-instalada falhe logo na primeira
    conexão.

    Não se aplica ao SQLite: lá não há instância com vários bancos, e o
    arquivo é criado pelo próprio driver na primeira conexão."""
    if conexao.dialeto() == "sqlite":
        return

    engine_master = conexao.criar_engine("master", isolation_level="AUTOCOMMIT")
    try:
        with engine_master.connect() as conn:
            existe = conn.execute(
                text("SELECT 1 FROM sys.databases WHERE name = :nome"),
                {"nome": conexao.DATABASE},
            ).fetchone()
            if not existe:
                conn.execute(text(f"CREATE DATABASE [{conexao.DATABASE}]"))
                print(f"Banco '{conexao.DATABASE}' não existia — criado agora.")
    finally:
        engine_master.dispose()


def main() -> None:
    # O banco é garantido e o motor criado AQUI, não no nível do módulo:
    # antes, só importar este arquivo já conectava no `master` e podia
    # executar CREATE DATABASE — efeito colateral pesado e silencioso, que
    # tornava qualquer varredura de imports perigosa.
    _garantir_banco_existe()
    engine = conexao.criar_engine()

    print("Iniciando pipeline de ingestão via Pandas/SQLAlchemy...\n")

    for aba, tabela in TABELAS.items():
        print(f"-> Processando aba '{aba}'...")
        try:
            df = adaptador_excel.aba(aba)
            # if_exists="replace" recria a tabela a cada execução;
            # index=False não insere o índice do pandas como coluna.
            df.to_sql(name=tabela, con=engine, if_exists="replace", index=False)
            print(f"   OK   {len(df)} registros gravados na tabela '{tabela}'.")
        except Exception as e:
            print(f"   FALHA ao gravar a tabela '{tabela}': {e}")

    engine.dispose()
    print("\nPipeline finalizado com sucesso.")


if __name__ == "__main__":
    main()
