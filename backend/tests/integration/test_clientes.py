import pytest

CHAVES_RESUMO = {
    "cliente_id",
    "segmento",
    "porte",
    "plano",
    "valor_mensal",
    "sla_contratado_h",
    "inicio_contrato",
    "situacao",
    "mes_cancelamento",
    "score_risco",
    "faixa",
    "receita_em_risco",
    "posicao_fila",
}


def _listar(client, headers, **params):
    resposta = client.get("/api/clientes", headers=headers, params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


@pytest.mark.parametrize(
    "rota", ["/api/clientes", "/api/clientes/C001", "/api/clientes/C001/historico"]
)
def test_clientes_exige_autenticacao(client, rota):
    assert client.get(rota).status_code == 401


def test_listagem_padrao_paginada(client_com_base, auth_headers):
    pagina = _listar(client_com_base, auth_headers)

    assert (pagina["total"], pagina["pagina"], pagina["tamanho"]) == (80, 1, 20)
    assert len(pagina["itens"]) == 20
    assert pagina["itens"][0]["cliente_id"] == "C001"
    assert set(pagina["itens"][0]) == CHAVES_RESUMO


def test_paginas_seguintes(client_com_base, auth_headers):
    quarta = _listar(client_com_base, auth_headers, pagina=4)
    quinta = _listar(client_com_base, auth_headers, pagina=5)

    assert quarta["itens"][0]["cliente_id"] == "C061"
    assert quinta["itens"] == [] and quinta["total"] == 80


def test_filtros(client_com_base, auth_headers):
    cancelados = _listar(client_com_base, auth_headers, situacao="CANCELADO", tamanho=100)
    assert cancelados["total"] == 22
    assert all(
        c["situacao"] == "CANCELADO" and c["score_risco"] is None for c in cancelados["itens"]
    )

    assert _listar(client_com_base, auth_headers, plano="ENTERPRISE")["total"] == 19
    assert _listar(client_com_base, auth_headers, porte="PEQUENO")["total"] == 35
    assert _listar(client_com_base, auth_headers, segmento="saude")["total"] == 12
    busca = _listar(client_com_base, auth_headers, busca="c08")
    assert [c["cliente_id"] for c in busca["itens"]] == ["C080"]


def test_filtro_por_faixa_bate_com_o_resumo(client_com_base, auth_headers):
    resumo = client_com_base.get("/api/dashboard/resumo", headers=auth_headers).json()
    atencao = _listar(client_com_base, auth_headers, faixa="ATENCAO", tamanho=100)

    assert atencao["total"] == resumo["por_faixa"]["ATENCAO"]
    assert all(c["faixa"] == "ATENCAO" for c in atencao["itens"])


def test_ordenacao_por_receita_em_risco_deixa_nulos_no_fim(client_com_base, auth_headers):
    itens = _listar(client_com_base, auth_headers, ordenar="receita_em_risco", tamanho=100)["itens"]

    valores = [c["receita_em_risco"] for c in itens]
    preenchidos = [v for v in valores if v is not None]
    assert preenchidos == sorted(preenchidos, reverse=True)
    assert valores[: len(preenchidos)] == preenchidos
    assert all(v is None for v in valores[len(preenchidos) :])


@pytest.mark.parametrize(
    "params", [{"ordenar": "xpto"}, {"faixa": "PESSIMO"}, {"tamanho": 101}, {"pagina": 0}]
)
def test_parametros_invalidos_retornam_422(client_com_base, auth_headers, params):
    resposta = client_com_base.get("/api/clientes", headers=auth_headers, params=params)
    assert resposta.status_code == 422


def test_detalhe_de_cliente_na_fila(client_com_base, auth_headers):
    fila = client_com_base.get("/api/dashboard/fila", headers=auth_headers).json()
    primeiro = fila[0]["cliente_id"]

    detalhe = client_com_base.get(f"/api/clientes/{primeiro.lower()}", headers=auth_headers)

    assert detalhe.status_code == 200
    corpo = detalhe.json()
    assert corpo["cliente_id"] == primeiro
    avaliacao = corpo["avaliacao"]
    assert avaliacao["posicao_fila"] == 1
    assert avaliacao["evidencias"] and avaliacao["evidencias"][0]["texto"]
    assert avaliacao["acao_recomendada"]["descricao"]


def test_detalhe_de_cancelado_nao_tem_avaliacao(client_com_base, auth_headers):
    cancelado = _listar(client_com_base, auth_headers, situacao="CANCELADO")["itens"][0]

    corpo = client_com_base.get(
        f"/api/clientes/{cancelado['cliente_id']}", headers=auth_headers
    ).json()

    assert corpo["situacao"] == "CANCELADO"
    assert corpo["mes_cancelamento"] is not None
    assert corpo["avaliacao"] is None


def test_cliente_inexistente_retorna_404(client_com_base, auth_headers):
    resposta = client_com_base.get("/api/clientes/C999", headers=auth_headers)

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Cliente C999 não encontrado"}
    historico = client_com_base.get("/api/clientes/C999/historico", headers=auth_headers)
    assert historico.status_code == 404


def test_historico_pronto_para_grafico(client_com_base, auth_headers):
    corpo = client_com_base.get("/api/clientes/C001/historico", headers=auth_headers).json()

    assert corpo["cliente_id"] == "C001"
    meses = [linha["mes_ref"] for linha in corpo["atendimento"]]
    assert len(meses) == 18 and meses == sorted(meses)
    assert meses[0] == "2025-01-01"
    assert {"pct_sla_cumprido", "uso_plataforma_pct", "chamados_abertos"} <= set(
        corpo["atendimento"][0]
    )
    assert len(corpo["nps"]) == 6
    assert {"mes_ref", "respondeu", "nota_nps", "classificacao_nps"} == set(corpo["nps"][0])
