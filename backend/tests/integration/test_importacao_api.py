def test_importacao_exige_autenticacao(client, caminho_xlsx):
    resposta = client.post(
        "/api/importacao", files={"arquivo": ("base.xlsx", caminho_xlsx.read_bytes())}
    )
    assert resposta.status_code == 401


def test_importacao_via_upload(client, auth_headers, caminho_xlsx):
    resposta = client.post(
        "/api/importacao",
        headers=auth_headers,
        files={"arquivo": ("base.xlsx", caminho_xlsx.read_bytes())},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["contagens"]["clientes"] == 80
    assert corpo["avisos"] == []


def test_importacao_de_arquivo_invalido_retorna_422(client, auth_headers):
    resposta = client.post(
        "/api/importacao", headers=auth_headers, files={"arquivo": ("x.xlsx", b"lixo")}
    )

    assert resposta.status_code == 422
    assert "xlsx" in resposta.json()["detail"]
