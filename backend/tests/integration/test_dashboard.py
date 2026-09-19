import pandas as pd
import pytest

CHAVES_ITEM_FILA = {
    "posicao",
    "cliente_id",
    "segmento",
    "plano",
    "porte",
    "valor_mensal",
    "score_risco",
    "faixa",
    "receita_em_risco",
    "qtd_dimensoes_afetadas",
    "principais_motivos",
    "acao_recomendada",
    "ultimo_contato",
}


@pytest.mark.parametrize("rota", ["/api/dashboard/resumo", "/api/dashboard/fila"])
def test_dashboard_exige_autenticacao(client, rota):
    assert client.get(rota).status_code == 401


def test_dashboard_sem_analise_responde_vazio(client, auth_headers):
    resumo = client.get("/api/dashboard/resumo", headers=auth_headers)
    fila = client.get("/api/dashboard/fila", headers=auth_headers)

    assert resumo.status_code == 200
    corpo = resumo.json()
    assert corpo["mes_referencia"] is None
    assert corpo["clientes_ativos"] == 0
    assert corpo["receita_em_risco"] == 0
    assert corpo["por_faixa"] == {"CRITICO": 0, "ATENCAO": 0, "MONITORAR": 0, "SAUDAVEL": 0}
    assert fila.status_code == 200 and fila.json() == []


def test_resumo_com_base(client_com_base, auth_headers, caminho_xlsx):
    corpo = client_com_base.get("/api/dashboard/resumo", headers=auth_headers).json()

    clientes = pd.read_excel(caminho_xlsx, sheet_name="clientes")
    situacao = pd.read_excel(caminho_xlsx, sheet_name="situacao_clientes")
    ativos = situacao.loc[situacao["situacao"] == "Ativo", "cliente_id"]
    receita_ativa = float(clientes[clientes["cliente_id"].isin(ativos)]["valor_mensal"].sum())

    assert corpo["mes_referencia"] == "2026-06-01"
    assert corpo["clientes_ativos"] == 58
    assert corpo["receita_ativa"] == pytest.approx(receita_ativa)
    assert 0 < corpo["receita_em_risco"] < corpo["receita_ativa"]
    assert sum(corpo["por_faixa"].values()) == 58
    assert set(corpo["por_dimensao"]) == {
        "ATENDIMENTO",
        "SLA",
        "ENGAJAMENTO",
        "FINANCEIRO",
        "SATISFACAO",
    }
    assert corpo["qtd_na_fila"] == (corpo["por_faixa"]["CRITICO"] + corpo["por_faixa"]["ATENCAO"])


def test_fila_no_formato_do_contrato(client_com_base, auth_headers):
    fila = client_com_base.get("/api/dashboard/fila", headers=auth_headers).json()

    assert fila
    assert [item["posicao"] for item in fila] == list(range(1, len(fila) + 1))
    for item in fila:
        assert set(item) == CHAVES_ITEM_FILA
        assert item["faixa"] in ("CRITICO", "ATENCAO")
        assert isinstance(item["valor_mensal"], float)
        assert 1 <= len(item["principais_motivos"]) <= 3
        assert set(item["acao_recomendada"]) == {"codigo", "titulo", "responsavel", "prazo_dias"}
        assert item["ultimo_contato"] is None


def test_fila_respeita_limite(client_com_base, auth_headers):
    resp_limit1 = client_com_base.get("/api/dashboard/fila?limite=1", headers=auth_headers).json()
    assert len(resp_limit1) == 1

    resp_limit0 = client_com_base.get("/api/dashboard/fila?limite=0", headers=auth_headers)
    assert resp_limit0.status_code == 422
