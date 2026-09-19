from app.core.enums import Dimensao, SentidoPiora, TipoRegra
from app.services.risco.recomendacao import recomendar
from app.services.risco.score import Evidencia
from app.services.risco.sinais import DefinicaoSinal, Disparo


def _ev(codigo: str, dimensao: Dimensao, contribuicao: float = 0.1) -> Evidencia:
    sinal = DefinicaoSinal(
        1, codigo, dimensao, "v", TipoRegra.NIVEL, SentidoPiora.AUMENTO, 1.0, 2, 0.1, ""
    )
    return Evidencia(Disparo(sinal, 1.0, None, None, 0, 1.0, ""), contribuicao)


def test_sem_evidencias_nao_recomenda():
    assert recomendar([]) is None


def test_tres_dimensoes_vira_comite():
    evidencias = [
        _ev("A", Dimensao.ATENDIMENTO),
        _ev("B", Dimensao.FINANCEIRO),
        _ev("C", Dimensao.SATISFACAO),
    ]
    assert recomendar(evidencias) == "COMITE_RETENCAO"


def test_reunioes_e_silencio_viram_contato_executivo():
    evidencias = [
        _ev("REUNIOES_CANCELADAS", Dimensao.ENGAJAMENTO),
        _ev("NPS_SILENCIO", Dimensao.SATISFACAO),
    ]
    assert recomendar(evidencias) == "CONTATO_EXECUTIVO"


def test_dimensao_dominante_define_a_acao():
    assert recomendar([_ev("A", Dimensao.SLA)]) == "REVISAO_TECNICA"
    assert recomendar([_ev("A", Dimensao.ATENDIMENTO)]) == "REVISAO_TECNICA"
    assert recomendar([_ev("A", Dimensao.ENGAJAMENTO)]) == "REUNIAO_VALOR"
    assert recomendar([_ev("A", Dimensao.SATISFACAO)]) == "PLANO_DE_RECUPERACAO"
    misto = [_ev("F", Dimensao.FINANCEIRO, 0.10), _ev("A", Dimensao.ATENDIMENTO, 0.05)]
    assert recomendar(misto) == "CONVERSA_FINANCEIRA"


def test_contribuicoes_da_mesma_dimensao_se_somam():
    evidencias = [
        _ev("A1", Dimensao.ATENDIMENTO, 0.06),
        _ev("A2", Dimensao.ATENDIMENTO, 0.06),
        _ev("F", Dimensao.FINANCEIRO, 0.10),
    ]
    assert recomendar(evidencias) == "REVISAO_TECNICA"
