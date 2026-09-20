"""
Centraliza todas as conexões com o SQL Server.

Estratégia de autenticação:

1. Tenta utilizar o login SQL holder_jenkins.
2. Caso o login não exista ou falhe, tenta autenticação Windows.
3. Através da conexão Windows, cria automaticamente:
   - O login SQL holder_jenkins na instância;
   - O usuário holder_jenkins dentro do banco holder;
   - As permissões necessárias no banco.
4. Tenta novamente conectar utilizando o login SQL.

A configuração utiliza Encrypt=no, adequada para instâncias locais
ou ambientes controlados onde não é necessária criptografia TLS.
"""

from __future__ import annotations

import urllib.parse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


SERVER = "localhost"
DATABASE = "holder"

DRIVER = "ODBC Driver 17 for SQL Server"

# Credenciais utilizadas pelo Jenkins
USERNAME = "holder_jenkins"
PASSWORD = "Holder@123456"


def _string_odbc_base(database: str | None = None) -> str:
    """
    Retorna a parte comum da string ODBC.
    """

    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database or DATABASE};"
        f"Encrypt=no;"
    )


def string_odbc(database: str | None = None) -> str:
    """
    String ODBC utilizando autenticação SQL Server.
    """

    connection_string = (
        f"{_string_odbc_base(database)}"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
    )

    return urllib.parse.quote_plus(connection_string)


def _string_odbc_trusted(database: str | None = None) -> str:
    """
    String ODBC utilizando autenticação integrada do Windows.
    """

    connection_string = (
        f"{_string_odbc_base(database)}"
        f"Trusted_Connection=yes;"
    )

    return urllib.parse.quote_plus(connection_string)


def _criar_engine_sql(database: str | None = None, **kwargs) -> Engine:
    """
    Cria uma engine utilizando o login SQL do Jenkins.
    """

    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={string_odbc(database)}",
        **kwargs,
    )


def _criar_engine_windows(database: str | None = None, **kwargs) -> Engine:
    """
    Cria uma engine utilizando autenticação Windows.
    """

    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={_string_odbc_trusted(database)}",
        **kwargs,
    )


def _login_existe(engine: Engine) -> bool:
    """
    Verifica se o login SQL existe na instância do SQL Server.
    """

    consulta = text(
        """
        SELECT 1
        FROM sys.server_principals
        WHERE name = :username
        """
    )

    with engine.connect() as connection:
        resultado = connection.execute(
            consulta,
            {"username": USERNAME},
        ).first()

    return resultado is not None


def _criar_login_sql(engine: Engine) -> None:
    """
    Cria o login SQL caso ele ainda não exista.

    A criação é feita utilizando SQL dinâmico para permitir
    o uso seguro dos valores configurados nas variáveis.
    """

    senha_escaped = PASSWORD.replace("'", "''")
    usuario_escaped = USERNAME.replace("]", "]]")

    comando = text(
        f"""
        IF NOT EXISTS (
            SELECT 1
            FROM sys.server_principals
            WHERE name = :username
        )
        BEGIN
            CREATE LOGIN [{usuario_escaped}]
            WITH PASSWORD = '{senha_escaped}',
            CHECK_POLICY = OFF,
            CHECK_EXPIRATION = OFF;
        END
        """
    )

    with engine.connect() as connection:
        connection.execute(
            comando,
            {"username": USERNAME},
        )
        connection.commit()


def _configurar_usuario_banco(engine: Engine) -> None:
    """
    Cria o usuário dentro do banco e concede permissões.

    db_datareader: permite consultar dados.
    db_datawriter: permite inserir, atualizar e excluir dados.

    db_ddladmin: permite criar e alterar objetos do banco,
    necessário caso a aplicação crie tabelas ou estruturas.

    db_owner pode ser utilizado caso a aplicação precise de
    permissões administrativas completas no banco.
    """

    usuario_escaped = USERNAME.replace("]", "]]")

    comando = text(
        f"""
        IF NOT EXISTS (
            SELECT 1
            FROM sys.database_principals
            WHERE name = :username
        )
        BEGIN
            CREATE USER [{usuario_escaped}]
            FOR LOGIN [{usuario_escaped}];
        END;

        ALTER ROLE db_datareader
        ADD MEMBER [{usuario_escaped}];

        ALTER ROLE db_datawriter
        ADD MEMBER [{usuario_escaped}];

        ALTER ROLE db_ddladmin
        ADD MEMBER [{usuario_escaped}];
        """
    )

    with engine.connect() as connection:
        connection.execute(
            comando,
            {"username": USERNAME},
        )
        connection.commit()


def _garantir_login_e_usuario() -> None:
    """
    Garante que o login SQL e o usuário do banco existam.

    A conexão Windows precisa ter permissão para criar logins
    e usuários no SQL Server.
    """

    engine_windows = _criar_engine_windows(DATABASE)

    try:
        with engine_windows.connect():
            pass

        print(
            f"[SQL Server] Conectado via Windows. "
            f"Verificando login '{USERNAME}'."
        )

        if not _login_existe(engine_windows):
            print(
                f"[SQL Server] Login '{USERNAME}' não existe. "
                "Criando login..."
            )

            _criar_login_sql(engine_windows)

            print(
                f"[SQL Server] Login '{USERNAME}' criado com sucesso."
            )
        else:
            print(
                f"[SQL Server] Login '{USERNAME}' já existe."
            )

        _configurar_usuario_banco(engine_windows)

        print(
            f"[SQL Server] Usuário '{USERNAME}' configurado "
            f"no banco '{DATABASE}'."
        )

    finally:
        engine_windows.dispose()


def criar_engine(database: str | None = None, **kwargs) -> Engine:
    """
    Cria uma engine SQLAlchemy.

    Fluxo:

    1. Tenta conexão com o login SQL do Jenkins.
    2. Se funcionar, retorna a engine.
    3. Se falhar, conecta via Windows.
    4. Cria o login e o usuário, caso necessário.
    5. Tenta novamente usando autenticação SQL.
    6. Se tudo falhar, propaga a exceção final.

    kwargs são encaminhados diretamente ao create_engine.
    """

    database = database or DATABASE

    # Primeira tentativa: autenticação SQL
    engine_sql = _criar_engine_sql(database, **kwargs)

    try:
        with engine_sql.connect():
            pass

        print(
            f"[SQL Server] Conectado usando o login SQL '{USERNAME}'."
        )

        return engine_sql

    except Exception as erro_sql:
        engine_sql.dispose()

        print(
            "[SQL Server] Login SQL não funcionou. "
            "Tentando autenticação Windows..."
        )

        print(f"[SQL Server] Motivo inicial: {erro_sql}")

    # Segunda tentativa: garantir criação do login
    try:
        _garantir_login_e_usuario()

    except Exception as erro_windows:
        print(
            "[SQL Server] Não foi possível criar ou configurar "
            "o login utilizando autenticação Windows."
        )

        raise RuntimeError(
            "Falha ao conectar com o login SQL e também ao configurar "
            "automaticamente o login utilizando autenticação Windows. "
            "Verifique se o usuário do Windows possui permissões "
            "administrativas no SQL Server."
        ) from erro_windows

    # Terceira tentativa: autenticação SQL após criação
    engine_sql = _criar_engine_sql(database, **kwargs)

    try:
        with engine_sql.connect():
            pass

        print(
            f"[SQL Server] Conectado com sucesso usando "
            f"'{USERNAME}' após criação automática."
        )

        return engine_sql

    except Exception:
        engine_sql.dispose()
        raise