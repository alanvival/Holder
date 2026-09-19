import pytest


@pytest.mark.parametrize("rota", ["/api/sinais", "/api/acoes-recomendadas"])
def test_catalogo_exige_autenticacao(client, rota):
    assert client.get(rota).status_code == 401


def test_sinais_disponiveis_desde_o_startup(client, auth_headers):
    sinais = client.get("/api/sinais", headers=auth_headers).json()

    assert len(sinais) == 10
    reclamacoes = next(s for s in sinais if s["codigo"] == "RECLAMACOES")
    assert reclamacoes["metrica"] == "soma_3m"
    assert reclamacoes["peso"] == pytest.approx(0.1)
    assert reclamacoes["lift"] is None
    assert reclamacoes["ativo"] is True


def test_acoes_em_ordem_do_playbook(client, auth_headers):
    acoes = client.get("/api/acoes-recomendadas", headers=auth_headers).json()

    assert [a["codigo"] for a in acoes][:2] == ["COMITE_RETENCAO", "CONTATO_EXECUTIVO"]
    assert len(acoes) == 6
    assert set(acoes[0]) == {
        "codigo",
        "titulo",
        "descricao",
        "dimensao_gatilho",
        "responsavel_sugerido",
        "prazo_dias",
        "ordem",
    }
