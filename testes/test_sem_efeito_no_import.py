"""
Prende o invariante conquistado na fase 3: **importar não é operação
observável**. Antes, importar o pacote lia a planilha inteira, criava a
pasta `logs/`, abria arquivo de log e, no caso de `ingestao`, conectava no
SQL Server e podia executar CREATE DATABASE.

Cada verificação roda num subprocesso limpo, porque o que está sob teste é
o que acontece *durante* o import — num processo onde outro teste já
importou o módulo, o efeito já teria acontecido e a checagem não valeria
nada.
"""
import subprocess
import sys
import textwrap

RAIZ = __import__("pathlib").Path(__file__).resolve().parent.parent


def _rodar(codigo: str):
    resultado = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(codigo)],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, (
        f"subprocesso falhou:\n--- stdout ---\n{resultado.stdout}\n--- stderr ---\n{resultado.stderr}"
    )


def test_importar_o_pacote_nao_le_a_planilha():
    """`tools` é o topo da cadeia: puxa dados, metricas, tools_genericas e
    previsao_risco. Nenhum deles deve ter tocado o Excel."""
    _rodar(
        """
        import holder.aplicacao.assistente.tools  # noqa: F401
        from holder.infra.dados import carteira as dados
        from holder.infra.dados import adaptador_excel

        assert dados.carregar.cache_info().misses == 0, (
            f"os índices por cliente foram montados durante o import: {dados.carregar.cache_info()}"
        )
        assert adaptador_excel._abas.cache_info().misses == 0, (
            f"a planilha foi lida durante o import: {adaptador_excel._abas.cache_info()}"
        )
        """
    )


def test_importar_o_pacote_nao_configura_log_em_disco():
    _rodar(
        """
        import holder.aplicacao.assistente.ia_fallback  # noqa: F401
        from holder.infra.ia import guardrails

        assert guardrails.logger.handlers == [], (
            f"o log foi configurado durante o import: {guardrails.logger.handlers}"
        )
        """
    )


def test_importar_ingestao_nao_conecta_no_banco():
    """O mais grave dos efeitos antigos: este import podia executar
    CREATE DATABASE. Se o módulo voltar a conectar no import, este teste
    falha mesmo com o SQL Server no ar — o que ele confere é que nenhum
    motor de conexão é criado, não se a conexão daria certo."""
    _rodar(
        """
        from unittest.mock import patch

        with patch("sqlalchemy.create_engine") as motor:
            from holder.infra.etl import ingestao  # noqa: F401

        assert not motor.called, "ingestao criou um motor de conexão durante o import"
        """
    )


def test_a_planilha_e_lida_uma_unica_vez_por_processo():
    """A carga preguiçosa não pode ter virado carga repetida: o cache
    mantém a garantia antiga de uma leitura por processo."""
    _rodar(
        """
        from holder.infra.dados import carteira as dados

        primeiro = dados.clientes
        segundo = dados.aba("clientes")
        terceiro = dados.carregar()["clientes"]

        assert primeiro is segundo is terceiro, "as tabelas deixaram de ser o mesmo objeto"
        assert dados.carregar.cache_info().misses == 1, (
            f"a planilha foi lida mais de uma vez: {dados.carregar.cache_info()}"
        )
        """
    )
