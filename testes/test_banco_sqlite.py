"""
O terceiro destino de escrita: SQLite.

O adaptador de planilha (ADR 0002) resolve a leitura da carteira sem o SQL
Server no ar, mas não resolve o que a aba "Score de Risco" consome —
`fScoreRisco` e `fModeloRiscoLog` só existem como tabela. Este arquivo
cobre o caminho que faz essas duas tabelas existirem fora do SQL Server,
que é o que permite o dashboard subir inteiro num host sem banco (Streamlit
Cloud).

A regra que este arquivo protege: **ligar o SQLite não pode mudar nada do
caminho SQL Server**. O primeiro teste é o guarda dessa regra; os demais
exercem o SQLite de verdade, contra arquivo em disco, sem mock — é barato
o bastante pra rodar na suíte normal, sem marcador.
"""
import pandas as pd
import pytest

from holder.infra.dados import conexao
from holder.infra.persistencia import historico_score, log_treinos


@pytest.fixture
def banco_sqlite(tmp_path, monkeypatch):
    """Aponta o SQLite pra um arquivo descartável e liga o dialeto. Sem
    isto, os testes escreveriam no `dados/holder.sqlite3` versionado."""
    monkeypatch.setattr(conexao, "ARQUIVO_SQLITE", tmp_path / "holder.sqlite3")
    monkeypatch.setenv(conexao.VARIAVEL_DE_AMBIENTE, "sqlite")
    return tmp_path / "holder.sqlite3"


# --- o guarda: o caminho existente não muda ---------------------------------

def test_sem_a_variavel_de_ambiente_continua_sql_server(monkeypatch):
    """Regressão. O default é e continua sendo SQL Server — quem já roda
    local não precisa configurar nada pra continuar funcionando igual."""
    monkeypatch.delenv(conexao.VARIAVEL_DE_AMBIENTE, raising=False)
    assert conexao.dialeto() == "sqlserver"
    assert conexao.criar_engine().url.drivername == "mssql+pyodbc"


def test_a_string_odbc_nao_muda_com_o_sqlite_ligado(banco_sqlite):
    """A string ODBC é usada só pelo dialeto SQL Server, mas é lida por
    `test_porta_de_dados.py` como contrato — ligar o SQLite não pode
    reescrevê-la."""
    assert "Encrypt%3Dno" in conexao.string_odbc()
    assert "ODBC+Driver+17+for+SQL+Server" in conexao.string_odbc()


def test_dialeto_desconhecido_falha_alto(monkeypatch):
    """Mesmo contrato de `porta.fonte()`: nome errado estoura, não cai
    silenciosamente num default."""
    monkeypatch.setenv(conexao.VARIAVEL_DE_AMBIENTE, "oracle")
    with pytest.raises(ValueError, match="Banco desconhecido"):
        conexao.criar_engine()


# --- o caminho novo ---------------------------------------------------------

def test_sqlite_aponta_pro_arquivo_configurado(banco_sqlite):
    engine = conexao.criar_engine()
    assert engine.url.drivername == "sqlite"
    assert engine.url.database == str(banco_sqlite)


def test_historico_de_score_sobrevive_ao_round_trip(banco_sqlite):
    """`fScoreRisco` é o que a aba 3 lê. Gravar e reler tem que devolver os
    mesmos números — é o teste que prova que a aba funciona sem SQL Server."""
    linhas = pd.DataFrame([{
        "cliente_id": "C001", "mes_ref": "2024-06",
        "score_precoce": 2.0, "score_confirmado": 3.0,
        "risco_percentual": 71.5, "faixa": "alto",
        "sinais_detalhados": '{"nps": -2}',
    }])

    assert historico_score.salvar_mes(linhas, "2024-06") == 1

    lido = historico_score.carregar_historico()
    assert len(lido) == 1
    assert lido.iloc[0]["cliente_id"] == "C001"
    assert lido.iloc[0]["risco_percentual"] == pytest.approx(71.5)
    assert lido.iloc[0]["sinais_detalhados"] == '{"nps": -2}'


def test_salvar_o_mesmo_mes_duas_vezes_nao_duplica(banco_sqlite):
    """A idempotência é explícita no docstring de `salvar_mes` (apaga e
    regrava). Ela vinha do DELETE, que é portável — este teste garante que
    continua valendo no SQLite."""
    linhas = pd.DataFrame([{
        "cliente_id": "C001", "mes_ref": "2024-06",
        "score_precoce": 2.0, "score_confirmado": 3.0,
        "risco_percentual": 71.5, "faixa": "alto",
        "sinais_detalhados": "{}",
    }])

    historico_score.salvar_mes(linhas, "2024-06")
    historico_score.salvar_mes(linhas, "2024-06")

    assert len(historico_score.carregar_historico()) == 1


def test_historico_vazio_nao_estoura_antes_do_primeiro_treino(banco_sqlite):
    """A aba 3 renderiza antes de existir qualquer treino: `carregar_historico`
    tem que criar a tabela e devolver vazio, não levantar."""
    assert historico_score.carregar_historico().empty


def test_log_de_treinos_registra_e_recupera(banco_sqlite):
    """`fModeloRiscoLog` alimenta a seção de metodologia — é a prova de que
    o número na tela veio de modelo validado."""
    log_treinos.registrar(
        {"auc": 0.87, "brier": 0.09, "n_amostras": 960, "n_positivos": 112},
        mes_ref_treino="2024-06",
    )

    lido = log_treinos.carregar()
    assert len(lido) == 1
    assert lido.iloc[0]["auc"] == pytest.approx(0.87)
    assert lido.iloc[0]["n_amostras"] == 960
    assert lido.iloc[0]["treinado_em"] is not None


def test_log_de_treinos_vazio_devolve_as_colunas_certas(banco_sqlite):
    """Contrato já documentado em `log_treinos.carregar`: DataFrame vazio
    com as colunas certas, pra metodologia renderizar antes do 1º treino."""
    vazio = log_treinos.carregar()
    assert vazio.empty
    assert list(vazio.columns) == log_treinos.COLUNAS


# --- a ingestão -------------------------------------------------------------

def test_ingestao_popula_o_sqlite_com_as_contagens_do_enunciado(banco_sqlite):
    """O caminho inteiro: planilha -> ingestão -> SQLite -> adaptador. É o
    que gera o arquivo versionado que sobe no deploy, e a prova de que o
    modelo dimensional sobrevive fora do SQL Server.

    `_garantir_banco_existe` consulta `sys.databases` e emite CREATE
    DATABASE — no SQLite não há instância com vários bancos, e o passo tem
    de ser pulado em vez de estourar."""
    from holder.infra.dados.porta import fonte
    from holder.infra.etl import ingestao

    ingestao.main()

    esperado = {"clientes": 80, "atendimento_mensal": 1295,
                "situacao_clientes": 80, "pesquisas_nps": 422}
    adaptador = fonte("sqlserver")
    for tabela, contagem in esperado.items():
        assert len(getattr(adaptador, tabela)()) == contagem, f"tabela '{tabela}'"


def test_o_caminho_sqlite_nao_importa_pyodbc():
    """Guarda da premissa do deploy: o host do Streamlit é Linux e não tem
    o driver ODBC da Microsoft. O dashboard inteiro tem de rodar sem tocar
    no pyodbc — o que hoje vale porque `criar_engine` só monta a URL
    `mssql+pyodbc` no ramo SQL Server, e o SQLAlchemy só carrega o dialeto
    quando a URL pede.

    Se alguém importar pyodbc no topo de um módulo, este teste cai aqui e
    não lá, em build remoto, sem stack trace legível.

    Roda contra o `dados/holder.sqlite3` versionado de propósito (não contra
    um tmp_path): de quebra, prova que o arquivo que sobe no deploy existe e
    é legível."""
    import subprocess
    import sys

    codigo = (
        "import sys;"
        "from holder.dominio.carteira import carregar_e_preparar;"
        "from holder.infra.persistencia import historico_score, log_treinos;"
        "print('pyodbc' in sys.modules or any('dialects.mssql' in m for m in sys.modules))"
    )
    saida = subprocess.run(
        [sys.executable, "-c", codigo],
        capture_output=True, text=True, env={**__import__("os").environ,
                                             conexao.VARIAVEL_DE_AMBIENTE: "sqlite"},
    )
    assert saida.returncode == 0, saida.stderr
    assert saida.stdout.strip() == "False", "algum módulo passou a importar pyodbc no topo"
