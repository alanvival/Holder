import pandas as pd
import pytest


@pytest.mark.parametrize("rota", ["/api/metricas/variaveis", "/api/metricas/mensal?variavel=x"])
def test_metricas_exige_autenticacao(client, rota):
    assert client.get(rota).status_code == 401


def test_variaveis_disponiveis(client, auth_headers):
    variaveis = client.get("/api/metricas/variaveis", headers=auth_headers).json()

    codigos = [v["codigo"] for v in variaveis]
    assert len(codigos) == 11
    assert "pct_sla_cumprido" in codigos
    assert all(v["rotulo"] for v in variaveis)


def test_media_mensal_ignora_nulos(client_com_base, auth_headers, caminho_xlsx):
    pontos = client_com_base.get(
        "/api/metricas/mensal",
        headers=auth_headers,
        params={"variavel": "pct_sla_cumprido", "agregacao": "media"},
    ).json()

    df = pd.read_excel(caminho_xlsx, sheet_name="atendimento_mensal")
    esperado = df.dropna(subset=["pct_sla_cumprido"]).groupby("mes_ref")["pct_sla_cumprido"].mean()

    assert len(pontos) == 18
    assert [p["mes_ref"] for p in pontos] == sorted(p["mes_ref"] for p in pontos)
    assert pontos[0]["mes_ref"] == "2025-01-01"
    assert pontos[0]["valor"] == pytest.approx(esperado["2025-01"], rel=1e-3)


def test_soma_mensal(client_com_base, auth_headers, caminho_xlsx):
    pontos = client_com_base.get(
        "/api/metricas/mensal",
        headers=auth_headers,
        params={"variavel": "chamados_abertos", "agregacao": "soma"},
    ).json()

    df = pd.read_excel(caminho_xlsx, sheet_name="atendimento_mensal")
    assert pontos[0]["valor"] == df[df["mes_ref"] == "2025-01"]["chamados_abertos"].sum()


def test_variavel_ou_agregacao_invalida_retorna_422(client, auth_headers):
    invalida = client.get(
        "/api/metricas/mensal", headers=auth_headers, params={"variavel": "senha_hash"}
    )
    assert invalida.status_code == 422
    assert "senha_hash" in invalida.json()["detail"]
    agregacao = client.get(
        "/api/metricas/mensal",
        headers=auth_headers,
        params={"variavel": "chamados_abertos", "agregacao": "mediana"},
    )
    assert agregacao.status_code == 422


def test_sem_base_retorna_lista_vazia(client, auth_headers):
    pontos = client.get(
        "/api/metricas/mensal", headers=auth_headers, params={"variavel": "chamados_abertos"}
    )
    assert pontos.status_code == 200 and pontos.json() == []
