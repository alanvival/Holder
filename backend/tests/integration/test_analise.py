from datetime import date

import pytest

from app.core.enums import FaixaRisco
from app.core.exceptions import RecursoNaoEncontradoError
from app.services.fabrica import criar_analise_service, criar_importacao_service

ORDEM = {FaixaRisco.CRITICO: 0, FaixaRisco.ATENCAO: 1}


@pytest.fixture
def base_importada(db_session, settings, caminho_xlsx):
    criar_importacao_service(db_session, settings).importar(caminho_xlsx)


def test_avalia_todos_os_ativos_no_ultimo_mes(base_importada, db_session, settings):
    execucao = criar_analise_service(db_session, settings).executar()

    assert execucao.id is not None
    assert execucao.mes_referencia == date(2026, 6, 1)
    assert execucao.qtd_clientes_avaliados == 58
    assert len(execucao.avaliacoes) == 58


def test_fila_nao_vazia_ordenada_e_com_evidencias(base_importada, db_session, settings):
    execucao = criar_analise_service(db_session, settings).executar()

    fila = sorted(
        (a for a in execucao.avaliacoes if a.posicao_fila is not None),
        key=lambda a: a.posicao_fila,
    )
    assert 1 <= len(fila) <= settings.capacidade_fila
    assert [a.posicao_fila for a in fila] == list(range(1, len(fila) + 1))
    chaves = [(ORDEM[a.faixa], -float(a.receita_em_risco)) for a in fila]
    assert chaves == sorted(chaves)
    for avaliacao in fila:
        assert avaliacao.qtd_dimensoes_afetadas >= 2
        assert avaliacao.acao_recomendada_id is not None
        assert avaliacao.evidencias
        assert all(e.texto and "{" not in e.texto for e in avaliacao.evidencias)
        contribuicoes = [float(e.contribuicao) for e in avaliacao.evidencias]
        assert contribuicoes == sorted(contribuicoes, reverse=True)


def test_fora_da_fila_nao_tem_posicao(base_importada, db_session, settings):
    execucao = criar_analise_service(db_session, settings).executar()

    for avaliacao in execucao.avaliacoes:
        if avaliacao.faixa in (FaixaRisco.MONITORAR, FaixaRisco.SAUDAVEL):
            assert avaliacao.posicao_fila is None


def test_capacidade_da_fila_vem_das_settings(base_importada, db_session, settings):
    execucao = criar_analise_service(
        db_session, settings.model_copy(update={"capacidade_fila": 1})
    ).executar()

    assert execucao.qtd_na_fila == 1


def test_mes_de_referencia_explicito(base_importada, db_session, settings):
    execucao = criar_analise_service(db_session, settings).executar(date(2025, 12, 1))

    assert execucao.mes_referencia == date(2025, 12, 1)
    assert all(a.mes_referencia == date(2025, 12, 1) for a in execucao.avaliacoes)


def test_sem_dados_importados_gera_erro_claro(db_session, settings):
    with pytest.raises(RecursoNaoEncontradoError, match="Importe"):
        criar_analise_service(db_session, settings).executar()
