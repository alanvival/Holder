import math

import pytest

from app.core.enums import Dimensao, SentidoPiora, TipoRegra
from app.services.risco.sinais import DefinicaoSinal, avaliar_sinais, avaliar_sinal


def _sinal(**kw) -> DefinicaoSinal:
    padrao = dict(
        id=1,
        codigo="X",
        dimensao=Dimensao.ATENDIMENTO,
        variavel="chamados_reabertos",
        tipo_regra=TipoRegra.TENDENCIA,
        sentido_piora=SentidoPiora.AUMENTO,
        limiar=0.5,
        persistencia_min_meses=2,
        peso=0.1,
        template_evidencia="subiu {variacao_pct:.0%}",
        metrica="media_3m",
    )
    return DefinicaoSinal(**{**padrao, **kw})


def _ind(**kw) -> dict:
    padrao = dict(
        valor_mes=1.0,
        media_3m=1.0,
        soma_3m=3.0,
        linha_base_6m=1.0,
        variacao_pct=0.0,
        meses_consecutivos_piora=0,
    )
    return {**padrao, **kw}


def test_tendencia_dispara_com_persistencia_e_preenche_texto():
    disparo = avaliar_sinal(_sinal(), _ind(variacao_pct=1.0, meses_consecutivos_piora=2))

    assert disparo is not None
    assert disparo.intensidade == pytest.approx(1.0)
    assert disparo.texto == "subiu 100%"
    assert disparo.meses_persistencia == 2
    assert disparo.variacao_pct == pytest.approx(1.0)


def test_tendencia_sem_persistencia_nao_dispara():
    assert avaliar_sinal(_sinal(), _ind(variacao_pct=1.0, meses_consecutivos_piora=1)) is None


def test_tendencia_abaixo_do_limiar_nao_dispara():
    assert avaliar_sinal(_sinal(), _ind(variacao_pct=0.4, meses_consecutivos_piora=3)) is None


@pytest.mark.parametrize("variacao,esperado", [(0.5, 0.5), (0.75, 0.75), (1.0, 1.0), (5.0, 1.0)])
def test_intensidade_vai_de_meio_no_limiar_a_um_no_dobro(variacao, esperado):
    disparo = avaliar_sinal(_sinal(), _ind(variacao_pct=variacao, meses_consecutivos_piora=2))

    assert disparo.intensidade == pytest.approx(esperado)


def test_tendencia_de_queda_inverte_o_sinal():
    sinal = _sinal(
        sentido_piora=SentidoPiora.QUEDA,
        limiar=0.15,
        template_evidencia="caiu {queda_pct:.0%}",
    )

    disparo = avaliar_sinal(sinal, _ind(variacao_pct=-0.2, meses_consecutivos_piora=2))
    assert disparo is not None and disparo.texto == "caiu 20%"
    assert avaliar_sinal(sinal, _ind(variacao_pct=0.3, meses_consecutivos_piora=2)) is None


def test_nivel_de_queda_nao_exige_persistencia():
    sinal = _sinal(
        tipo_regra=TipoRegra.NIVEL,
        sentido_piora=SentidoPiora.QUEDA,
        limiar=65,
        variavel="pct_sla_cumprido",
        template_evidencia="SLA {media_3m:.0f}%",
    )

    disparo = avaliar_sinal(sinal, _ind(media_3m=50.0))
    assert disparo is not None
    assert disparo.texto == "SLA 50%"
    assert disparo.intensidade == pytest.approx(0.5 + 0.5 * 15 / 65)
    assert avaliar_sinal(sinal, _ind(media_3m=70.0)) is None


def test_nivel_usa_a_metrica_configurada():
    sinal = _sinal(
        tipo_regra=TipoRegra.NIVEL, limiar=2, metrica="soma_3m", template_evidencia="{soma_3m:.0f}"
    )

    assert avaliar_sinal(sinal, _ind(soma_3m=3.0, media_3m=1.0)).texto == "3"
    assert avaliar_sinal(sinal, _ind(soma_3m=1.0, media_3m=5.0)) is None


def test_evento_de_queda_do_nps():
    sinal = _sinal(
        tipo_regra=TipoRegra.EVENTO,
        sentido_piora=SentidoPiora.QUEDA,
        limiar=2,
        variavel="nps_variacao",
        template_evidencia="caiu {queda_abs:.0f} pontos",
    )

    assert avaliar_sinal(sinal, _ind(valor_mes=-3.0)).texto == "caiu 3 pontos"
    assert avaliar_sinal(sinal, _ind(valor_mes=-1.0)) is None


@pytest.mark.parametrize("nulo", [None, math.nan])
def test_metrica_nula_nunca_dispara(nulo):
    assert avaliar_sinal(_sinal(), _ind(variacao_pct=nulo, meses_consecutivos_piora=5)) is None
    nivel = _sinal(tipo_regra=TipoRegra.NIVEL, limiar=1)
    assert avaliar_sinal(nivel, _ind(media_3m=nulo)) is None


def test_avaliar_sinais_ignora_variavel_ausente_e_devolve_so_disparos():
    sinais = [_sinal(codigo="A"), _sinal(codigo="B", variavel="uso_plataforma_pct")]
    indicadores = {"chamados_reabertos": _ind(variacao_pct=1.0, meses_consecutivos_piora=2)}

    disparos = avaliar_sinais(sinais, indicadores)

    assert [d.sinal.codigo for d in disparos] == ["A"]
