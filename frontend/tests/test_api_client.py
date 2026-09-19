import json

import httpx
import pytest

from api_client import ApiClient, ApiErro, NaoAutenticado

TOKEN_RESPOSTA = {
    "access_token": "tok",
    "token_type": "bearer",
    "expira_em": "2026-09-20T02:00:00Z",
    "usuario": {"id": 1, "nome_completo": "Maria", "usuario": "maria"},
}


def test_login_envia_json_e_devolve_corpo(api_falsa):
    api_falsa.responder("POST", "/auth/login", 200, TOKEN_RESPOSTA)

    resposta = api_falsa.cliente().login("maria", "SenhaForte123")

    assert resposta["access_token"] == "tok"
    requisicao = api_falsa.requisicoes[0]
    assert str(requisicao.url) == "http://api.teste/api/auth/login"
    assert json.loads(requisicao.content) == {"usuario": "maria", "senha": "SenhaForte123"}


def test_token_vai_no_cabecalho(api_falsa):
    api_falsa.responder("GET", "/auth/me", 200, {"id": 1})

    api_falsa.cliente(token="abc").me()

    assert api_falsa.requisicoes[0].headers["authorization"] == "Bearer abc"


def test_401_vira_nao_autenticado_com_mensagem(api_falsa):
    api_falsa.responder("POST", "/auth/login", 401, {"detail": "Usuário ou senha inválidos"})

    with pytest.raises(NaoAutenticado) as erro:
        api_falsa.cliente().login("maria", "errada1")

    assert erro.value.detail == "Usuário ou senha inválidos"


def test_422_de_validacao_vira_mensagem_legivel(api_falsa):
    api_falsa.responder(
        "POST",
        "/auth/cadastro",
        422,
        {
            "detail": [
                {
                    "loc": ["body", "senha"],
                    "msg": "Value error, A senha deve conter ao menos uma letra e um número",
                }
            ]
        },
    )

    with pytest.raises(ApiErro) as erro:
        api_falsa.cliente().cadastrar("Maria", "maria", "semnumero")

    assert erro.value.status == 422
    assert erro.value.detail == "senha: A senha deve conter ao menos uma letra e um número"


def test_409_vira_api_erro(api_falsa):
    api_falsa.responder("POST", "/auth/cadastro", 409, {"detail": "Usuário já cadastrado"})

    with pytest.raises(ApiErro) as erro:
        api_falsa.cliente().cadastrar("Maria", "maria", "SenhaForte123")

    assert not isinstance(erro.value, NaoAutenticado)
    assert (erro.value.status, erro.value.detail) == (409, "Usuário já cadastrado")


def test_api_fora_do_ar_gera_mensagem_amigavel():
    def recusa(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusado", request=request)

    cliente = ApiClient(base_url="http://api.teste/api", transport=httpx.MockTransport(recusa))

    with pytest.raises(ApiErro) as erro:
        cliente.resumo_dashboard()

    assert erro.value.status == 0
    assert "Não foi possível conectar à API" in erro.value.detail


def test_listar_clientes_descarta_filtros_vazios(api_falsa):
    api_falsa.responder(
        "GET", "/clientes", 200, {"itens": [], "total": 0, "pagina": 1, "tamanho": 20}
    )

    api_falsa.cliente(token="t").listar_clientes(situacao=None, faixa="ATENCAO", busca="", pagina=2)

    assert dict(api_falsa.requisicoes[0].url.params) == {"faixa": "ATENCAO", "pagina": "2"}


def test_importar_envia_multipart(api_falsa):
    api_falsa.responder("POST", "/importacao", 200, {"contagens": {}, "avisos": []})

    api_falsa.cliente(token="t").importar("base.xlsx", b"conteudo")

    requisicao = api_falsa.requisicoes[0]
    assert requisicao.headers["content-type"].startswith("multipart/form-data")
    assert b'name="arquivo"; filename="base.xlsx"' in requisicao.content
