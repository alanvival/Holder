from app.models import Usuario

CADASTRO = {"nome_completo": "Maria da Silva", "usuario": "maria.silva", "senha": "SenhaForte123"}


def _cadastrar(client, **extra):
    return client.post("/api/auth/cadastro", json={**CADASTRO, **extra})


def test_cadastro_sucesso_nao_expoe_hash(client):
    resposta = _cadastrar(client, usuario="Maria.Silva")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert set(corpo) == {"id", "nome_completo", "usuario", "criado_em"}
    assert corpo["usuario"] == "maria.silva"


def test_cadastro_duplicado_ignora_maiusculas(client):
    _cadastrar(client)
    resposta = _cadastrar(client, usuario="MARIA.SILVA")

    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Usuário já cadastrado"}


def test_cadastro_invalido_retorna_422(client):
    assert _cadastrar(client, senha="semnumero").status_code == 422


def test_login_sucesso_e_me(client):
    _cadastrar(client)
    resposta = client.post(
        "/api/auth/login", json={"usuario": "  Maria.Silva ", "senha": "SenhaForte123"}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    usuario_esperado = {
        "id": 1,
        "nome_completo": "Maria da Silva",
        "usuario": "maria.silva",
    }
    assert corpo["usuario"] == usuario_esperado
    assert corpo["expira_em"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {corpo['access_token']}"})
    assert me.status_code == 200
    assert me.json()["usuario"] == "maria.silva"
    assert "senha_hash" not in me.json()


def test_login_atualiza_ultimo_login(client, db_session):
    _cadastrar(client)
    client.post("/api/auth/login", json={"usuario": "maria.silva", "senha": "SenhaForte123"})

    assert db_session.query(Usuario).one().ultimo_login_em is not None


def test_senha_errada_e_usuario_inexistente_tem_mesma_resposta(client):
    _cadastrar(client)
    errada = client.post("/api/auth/login", json={"usuario": "maria.silva", "senha": "Errada123"})
    inexistente = client.post("/api/auth/login", json={"usuario": "joao", "senha": "Errada123"})

    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json() == {"detail": "Usuário ou senha inválidos"}


def test_usuario_inativo_recebe_403(client, db_session):
    _cadastrar(client)
    usuario = db_session.query(Usuario).one()
    usuario.ativo = False
    db_session.commit()

    resposta = client.post(
        "/api/auth/login", json={"usuario": "maria.silva", "senha": "SenhaForte123"}
    )
    assert resposta.status_code == 403


def test_me_sem_token_ou_token_invalido_retorna_401(client):
    assert client.get("/api/auth/me").status_code == 401
    invalido = client.get("/api/auth/me", headers={"Authorization": "Bearer lixo"})
    assert invalido.status_code == 401
    assert invalido.json() == {"detail": "Token inválido ou expirado"}


def test_fixture_auth_headers_autentica(client, auth_headers):
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 200
