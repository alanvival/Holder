from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

import auth
from api_client import ApiClient

HOME = str(Path(__file__).resolve().parents[1] / "Home.py")
TOKEN_RESPOSTA = {
    "access_token": "tok",
    "token_type": "bearer",
    "expira_em": "2026-09-20T02:00:00Z",
    "usuario": {"id": 1, "nome_completo": "Maria da Silva", "usuario": "maria.silva"},
}


def _app() -> AppTest:
    return AppTest.from_file(HOME, default_timeout=30).run()


def _entrar(at: AppTest, usuario: str, senha: str) -> AppTest:
    at.text_input(key="login_usuario").input(usuario)
    at.text_input(key="login_senha").input(senha)
    return at.button(key="botao_entrar").click().run()


def test_home_mostra_abas_de_login_e_cadastro(api_falsa):
    at = _app()

    assert not at.exception
    assert [aba.label for aba in at.tabs] == ["Entrar", "Criar conta"]


def test_login_com_sucesso_guarda_token_e_sauda(api_falsa):
    api_falsa.responder("POST", "/auth/login", 200, TOKEN_RESPOSTA)

    at = _entrar(_app(), "maria.silva", "SenhaForte123")

    assert not at.exception
    assert at.session_state["token"] == "tok"
    assert any("Maria da Silva" in m.value for m in at.sidebar.markdown)


def test_login_invalido_mostra_mensagem_da_api(api_falsa):
    api_falsa.responder("POST", "/auth/login", 401, {"detail": "Usuário ou senha inválidos"})

    at = _entrar(_app(), "maria.silva", "errada123")

    assert [e.value for e in at.error] == ["Usuário ou senha inválidos"]
    assert "token" not in at.session_state


def test_cadastro_faz_login_automatico(api_falsa):
    api_falsa.responder("POST", "/auth/cadastro", 201, {"id": 1})
    api_falsa.responder("POST", "/auth/login", 200, TOKEN_RESPOSTA)
    at = _app()

    at.text_input(key="cadastro_nome").input("Maria da Silva")
    at.text_input(key="cadastro_usuario").input("maria.silva")
    at.text_input(key="cadastro_senha").input("SenhaForte123")
    at.text_input(key="cadastro_confirmacao").input("SenhaForte123")
    at = at.button(key="botao_cadastrar").click().run()

    assert not at.exception
    assert at.session_state["token"] == "tok"


def test_cadastro_com_senhas_diferentes_nem_chama_a_api(api_falsa):
    at = _app()

    at.text_input(key="cadastro_nome").input("Maria da Silva")
    at.text_input(key="cadastro_usuario").input("maria.silva")
    at.text_input(key="cadastro_senha").input("SenhaForte123")
    at.text_input(key="cadastro_confirmacao").input("Outra123")
    at = at.button(key="botao_cadastrar").click().run()

    assert [e.value for e in at.error] == ["As senhas não conferem."]
    assert api_falsa.requisicoes == []


def test_api_fora_do_ar_mostra_mensagem_amigavel(monkeypatch):
    def recusa(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusado", request=request)

    monkeypatch.setattr(
        auth,
        "fabrica_cliente",
        lambda token=None: ApiClient(
            base_url="http://api.teste/api", token=token, transport=httpx.MockTransport(recusa)
        ),
    )

    at = _entrar(_app(), "maria.silva", "SenhaForte123")

    assert not at.exception
    assert "Não foi possível conectar à API" in at.error[0].value
