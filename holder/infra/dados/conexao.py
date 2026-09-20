"""
Centraliza todas as conexões com o SQL Server.

Fluxo:

1. Conecta inicialmente usando autenticação Windows.
2. Cria o login SQL holder_jenkins caso ele não exista.
3. Cria o usuário holder_jenkins dentro do banco holder.
4. Concede as permissões necessárias.
5. Conecta utilizando o login SQL holder_jenkins.

A autenticação Windows precisa possuir permissões suficientes
para criar logins e usuários no SQL Server.
"""

from __future__ import annotations

import urllib.parse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


SERVER = "localhost"
DATABASE = "holder"

DRIVER = "ODBC Driver 17 for SQL Server"

USERNAME = "holder_jenkins"
PASSWORD = "Holder@123456"


def _string_odbc_base(database: str | None = None) -> str:
    """
    Parte comum da string ODBC.
    """

    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database or DATABASE};"
        f"Encrypt=no;"
    )


def string_odbc(database: str | None = None) -> str:
    """
    String de conexão usando autenticação SQL Server.
    """

    connection_string = (
        f"{_string_odbc_base(database)}"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
    )

    return urllib.parse.quote_plus(connection_string)


def _string_odbc_trusted(database: str | None = None) -> str:
    """
    String de conexão usando autenticação integrada do Windows.
    """

    connection_string = (
        f"{_string_odbc_base(database)}"
        f"Trusted_Connection=yes;"
    )

    return urllib.parse.quote_plus(connection_string)


def _criar_engine_sql(
    database: str | None = None,
    **kwargs,
) -> Engine:
    """
    Cria uma engine utilizando o login SQL holder_jenkins.
    """

    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={string_odbc(database)}",
        **kwargs,
    )


def _criar_engine_windows(
    database: str | None = None,
    **kwargs,
) -> Engine:
    """
    Cria uma engine utilizando autenticação Windows.
    """

    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={_string_odbc_trusted(database)}",
        **kwargs,
    )


def _garantir_login_sql(engine_windows: Engine) -> None:
    """
    Cria o login SQL holder_jenkins na instância do SQL Server,
    caso ele ainda não exista.
    """

    username_sql = USERNAME.replace("]", "]]")
    password_sql = PASSWORD.replace("'", "''")

    comando = text(
        f"""
        IF NOT EXISTS (
            SELECT 1
            FROM sys.server_principals
            WHERE name = :username
        )
        BEGIN
            CREATE LOGIN [{username_sql}]
            WITH PASSWORD = '{password_sql}',
                 CHECK_POLICY = OFF,
                 CHECK_EXPIRATION = OFF;
        END;
        """
    )

    with engine_windows.connect() as connection:
        connection.execute(
            comando,
            {"username": USERNAME},
        )
        connection.commit()

    print(
        f"[SQL Server] Login '{USERNAME}' criado ou já existente."
    )


def _garantir_usuario_banco(
    engine_windows: Engine,
    database: str,
) -> None:
    """
    Cria o usuário dentro do banco e concede permissões.
    """

    username_sql = USERNAME.replace("]", "]]")

    comando = text(
        f"""
        IF NOT EXISTS (
            SELECT 1
            FROM sys.database_principals
            WHERE name = :username
        )
        BEGIN
            CREATE USER [{username_sql}]
            FOR LOGIN [{username_sql}];
        END;

        IF NOT EXISTS (
            SELECT 1
            FROM sys.database_role_members drm
            INNER JOIN sys.database_principals role_principal
                ON drm.role_principal_id = role_principal.principal_id
            INNER JOIN sys.database_principals user_principal
                ON drm.member_principal_id = user_principal.principal_id
            WHERE role_principal.name = 'db_datareader'
              AND user_principal.name = :username
        )
        BEGIN
            ALTER ROLE db_datareader
            ADD MEMBER [{username_sql}];
        END;

        IF NOT EXISTS (
            SELECT 1
            FROM sys.database_role_members drm
            INNER JOIN sys.database_principals role_principal
                ON drm.role_principal_id = role_principal.principal_id
            INNER JOIN sys.database_principals user_principal
                ON drm.member_principal_id = user_principal.principal_id
            WHERE role_principal.name = 'db_datawriter'
              AND user_principal.name = :username
        )
        BEGIN
            ALTER ROLE db_datawriter
            ADD MEMBER [{username_sql}];
        END;

        IF NOT EXISTS (
            SELECT 1
            FROM sys.database_role_members drm
            INNER JOIN sys.database_principals role_principal
                ON drm.role_principal_id = role_principal.principal_id
            INNER JOIN sys.database_principals user_principal
                ON drm.member_principal_id = user_principal.principal_id
            WHERE role_principal.name = 'db_ddladmin'
              AND user_principal.name = :username
        )
        BEGIN
            ALTER ROLE db_ddladmin
            ADD MEMBER [{username_sql}];
        END;
        """
    )

    with engine_windows.connect() as connection:
        connection.execute(
            comando,
            {"username": USERNAME},
        )
        connection.commit()

    print(
        f"[SQL Server] Usuário '{USERNAME}' configurado "
        f"no banco '{database}'."
    )


def _preparar_login_jenkins(
    database: str,
    **kwargs,
) -> None:
    """
    Conecta primeiro via Windows e prepara o login SQL do Jenkins.
    """

    print(
        "[SQL Server] Conectando via autenticação Windows "
        "para preparar o login do Jenkins..."
    )

    engine_windows = _criar_engine_windows(
        database=database,
        **kwargs,
    )

    try:
        with engine_windows.connect():
            pass

        print(
            "[SQL Server] Autenticação Windows realizada com sucesso."
        )

        _garantir_login_sql(engine_windows)
        _garantir_usuario_banco(engine_windows, database)

    finally:
        engine_windows.dispose()


def criar_engine(
    database: str | None = None,
    **kwargs,
) -> Engine:
    """
    Cria uma engine SQLAlchemy.

    O login SQL do Jenkins é preparado primeiro por meio
    da autenticação Windows.

    Depois disso, a conexão final utiliza o login SQL.
    """

    database = database or DATABASE

    # Primeiro: autenticação Windows e criação do login
    _preparar_login_jenkins(
        database=database,
        **kwargs,
    )

    # Segundo: conexão final utilizando o login SQL
    print(
        f"[SQL Server] Tentando conexão com o login SQL '{USERNAME}'..."
    )

    engine_sql = _criar_engine_sql(
        database=database,
        **kwargs,
    )

    try:
        with engine_sql.connect():
            pass

        print(
            f"[SQL Server] Conectado com sucesso usando '{USERNAME}'."
        )

        return engine_sql

    except Exception:
        engine_sql.dispose()
        raise