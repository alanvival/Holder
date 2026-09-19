import pytest

from app.core.enums import Dimensao, FaixaRisco, SentidoPiora, TipoRegra
from app.services.risco.score import LimiaresFaixa, calcular_score, classificar_faixa
from app.services.risco.sinais import DefinicaoSinal, Disparo

LIMIARES = LimiaresFaixa(critico=0.55, atencao=0.30, monitorar=0.15)


def _disparo(codigo: str, dimensao: Dimensao, peso: float = 0.1, intensidade: float = 1.0):
    sinal = DefinicaoSinal(
        id=1,
        codigo=codigo,
        dimensao=dimensao,
        variavel="v",
        tipo_regra=TipoRegra.NIVEL,
        sentido_piora=SentidoPiora.AUMENTO,
        limiar=1.0,
        persistencia_min_meses=2,
        peso=peso,
        template_evidencia="",
    )
    return Disparo(sinal, 1.0, None, None, 0, intensidade, codigo)


@pytest.mark.parametrize(
    "score,esperada",
    [
        (0.55, FaixaRisco.CRITICO),
        (0.30, FaixaRisco.ATENCAO),
        (0.15, FaixaRisco.MONITORAR),
        (0.149, FaixaRisco.SAUDAVEL),
    ],
)
def test_faixas_por_limiar_com_duas_dimensoes(score, esperada):
    assert classificar_faixa(score, 2, LIMIARES) == esperada


def test_uma_dimensao_nunca_passa_de_monitorar():
    assert classificar_faixa(0.9, 1, LIMIARES) == FaixaRisco.MONITORAR
    assert classificar_faixa(0.1, 1, LIMIARES) == FaixaRisco.SAUDAVEL


def test_score_soma_contribuicoes_e_ordena_evidencias():
    resultado = calcular_score(
        [
            _disparo("A", Dimensao.ATENDIMENTO, peso=0.2, intensidade=0.5),
            _disparo("B", Dimensao.SLA, peso=0.3, intensidade=1.0),
        ],
        LIMIARES,
    )

    assert resultado.score == pytest.approx(0.4)
    assert resultado.qtd_dimensoes_afetadas == 2
    assert resultado.faixa == FaixaRisco.ATENCAO
    assert [e.disparo.sinal.codigo for e in resultado.evidencias] == ["B", "A"]
    assert resultado.evidencias[0].contribuicao == pytest.approx(0.3)


def test_score_limitado_a_um():
    disparos = [_disparo(f"S{i}", Dimensao.ATENDIMENTO, peso=0.3) for i in range(5)]
    disparos.append(_disparo("F", Dimensao.FINANCEIRO, peso=0.3))

    assert calcular_score(disparos, LIMIARES).score == 1.0


def test_sem_disparos_e_saudavel():
    resultado = calcular_score([], LIMIARES)

    assert (resultado.score, resultado.faixa, resultado.qtd_dimensoes_afetadas) == (
        0.0,
        FaixaRisco.SAUDAVEL,
        0,
    )
