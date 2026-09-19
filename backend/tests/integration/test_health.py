def test_health_retorna_ok_com_banco(client):
    resposta = client.get("/api/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "banco": "ok"}


def test_cors_libera_origem_do_streamlit(client):
    resposta = client.get("/api/health", headers={"Origin": "http://localhost:8501"})

    assert resposta.headers["access-control-allow-origin"] == "http://localhost:8501"
