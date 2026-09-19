from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    CredenciaisInvalidasError,
    RecursoNaoEncontradoError,
    UsuarioJaExisteError,
)
from app.core.handlers import registrar_handlers


def _app_que_lanca(erro: Exception) -> TestClient:
    app = FastAPI()
    registrar_handlers(app)

    @app.get("/x")
    def lanca():
        raise erro

    return TestClient(app)


def test_erro_de_dominio_vira_status_e_detail():
    resposta = _app_que_lanca(UsuarioJaExisteError()).get("/x")

    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Usuário já cadastrado"}


def test_401_inclui_www_authenticate():
    resposta = _app_que_lanca(CredenciaisInvalidasError()).get("/x")

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Usuário ou senha inválidos"}
    assert resposta.headers["www-authenticate"] == "Bearer"


def test_mensagem_customizada():
    resposta = _app_que_lanca(RecursoNaoEncontradoError("Cliente C999 não encontrado")).get("/x")

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Cliente C999 não encontrado"}
