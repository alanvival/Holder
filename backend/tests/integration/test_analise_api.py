def test_executar_exige_autenticacao(client):
    assert client.post("/api/analise/executar").status_code == 401


def test_executar_sem_base_retorna_404(client, auth_headers):
    resposta = client.post("/api/analise/executar", headers=auth_headers)

    assert resposta.status_code == 404
    assert "Importe" in resposta.json()["detail"]


def test_importacao_ja_roda_a_analise(client, auth_headers, caminho_xlsx):
    resposta = client.post(
        "/api/importacao",
        headers=auth_headers,
        files={"arquivo": ("base.xlsx", caminho_xlsx.read_bytes())},
    )

    execucao = resposta.json()["execucao"]
    assert execucao["qtd_clientes_avaliados"] == 58
    assert execucao["mes_referencia"] == "2026-06-01"
    assert execucao["qtd_na_fila"] >= 1


def test_executar_com_base(client_com_base, auth_headers):
    resposta = client_com_base.post("/api/analise/executar", headers=auth_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo"] == "PRODUCAO"
    assert corpo["versao_modelo"] == "mvp-regras-1"
    assert corpo["qtd_clientes_avaliados"] == 58
