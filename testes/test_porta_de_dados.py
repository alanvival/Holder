"""
Protege a decisão registrada em `docs/adr/0002-porta-de-dados-com-dois-adaptadores.md`.

O ADR aceita um risco explícito: os dois adaptadores (SQL Server e planilha)
precisam devolver as mesmas quatro tabelas com os mesmos tipos, e
divergência entre eles **não aparece como erro — aparece como número
diferente**. Este arquivo é o que transforma essa divergência em falha.
"""
import pytest

from holder.infra.dados import conexao
from holder.infra.dados.porta import fonte

TABELAS = ("clientes", "atendimento_mensal", "situacao_clientes", "pesquisas_nps")

# Do enunciado do desafio (docs/desafio/): 80 clientes, 1.295 linhas de
# atendimento (uma por cliente por mês), 422 registros de pesquisa.
CONTAGENS_ESPERADAS = {
    "clientes": 80,
    "atendimento_mensal": 1295,
    "situacao_clientes": 80,
    "pesquisas_nps": 422,
}


def test_fonte_desconhecida_falha_alto():
    with pytest.raises(ValueError, match="Fonte de dados desconhecida"):
        fonte("firebase")


def test_a_string_odbc_evita_negociacao_de_tls():
    """`Encrypt=no` é a versão deliberada que venceu a unificação das três
    cópias da string. Se alguém removê-la, a conexão volta a tentar TLS
    antes de cair pra sem criptografia numa instância local."""
    assert "Encrypt%3Dno" in conexao.string_odbc()
    assert "ODBC+Driver+17+for+SQL+Server" in conexao.string_odbc()
    assert conexao.string_odbc("master") != conexao.string_odbc()


@pytest.mark.parametrize("tabela", TABELAS)
def test_adaptador_excel_tem_as_contagens_do_enunciado(tabela):
    df = getattr(fonte("excel"), tabela)()
    assert len(df) == CONTAGENS_ESPERADAS[tabela]


@pytest.mark.sqlserver
@pytest.mark.parametrize("tabela", TABELAS)
def test_os_dois_adaptadores_concordam(tabela):
    do_banco = getattr(fonte("sqlserver"), tabela)()
    da_planilha = getattr(fonte("excel"), tabela)()

    assert len(do_banco) == len(da_planilha), (
        f"'{tabela}': banco tem {len(do_banco)} linhas, planilha tem {len(da_planilha)} — "
        "a ingestão está defasada ou os adaptadores divergiram"
    )
    assert set(do_banco.columns) == set(da_planilha.columns), (
        f"'{tabela}': colunas diferentes entre banco e planilha — "
        f"só no banco: {set(do_banco.columns) - set(da_planilha.columns)}, "
        f"só na planilha: {set(da_planilha.columns) - set(do_banco.columns)}"
    )


@pytest.mark.sqlserver
def test_carregar_tudo_devolve_na_ordem_que_o_dashboard_espera():
    """A ordem (clientes, atendimento, situação, pesquisas) é a que o
    dashboard e o modelo de risco desempacotam."""
    clientes, atendimento, situacao, pesquisas = fonte().carregar_tudo()

    assert "valor_mensal" in clientes.columns
    assert "mes_ref" in atendimento.columns
    assert "situacao" in situacao.columns
    assert "nota_nps" in pesquisas.columns
