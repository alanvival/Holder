from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.exceptions import TokenInvalidoError
from app.core.security import GerenciadorToken, HasherSenha

SEGREDO = "segredo-de-teste-com-mais-de-32-bytes-ok"


def test_hash_nao_e_a_senha_e_verifica():
    hasher = HasherSenha()
    senha_hash = hasher.gerar_hash("SenhaForte123")

    assert senha_hash != "SenhaForte123"
    assert senha_hash.startswith("$argon2")
    assert hasher.verificar("SenhaForte123", senha_hash)
    assert not hasher.verificar("outra123", senha_hash)


def test_verificar_com_hash_corrompido_retorna_false():
    assert HasherSenha().verificar("SenhaForte123", "isto-nao-e-um-hash") is False


def test_verificar_ficticio_sempre_falso():
    assert HasherSenha().verificar_ficticio("qualquer1") is False


def test_token_ida_e_volta():
    tokens = GerenciadorToken(SEGREDO, expira_minutos=60)
    token, expira_em = tokens.criar(7, "maria.silva")

    payload = tokens.decodificar(token)
    assert payload["sub"] == "7"
    assert payload["usuario"] == "maria.silva"
    assert "iat" in payload
    assert expira_em.tzinfo is not None
    assert timedelta(minutes=59) < expira_em - datetime.now(UTC) <= timedelta(minutes=60)


def test_token_expirado_e_invalido():
    tokens = GerenciadorToken(SEGREDO, expira_minutos=-1)
    token, _ = tokens.criar(1, "maria")

    with pytest.raises(TokenInvalidoError):
        tokens.decodificar(token)


def test_token_com_outro_segredo_e_invalido():
    token, _ = GerenciadorToken("outro-segredo-com-mais-de-32-bytes-xx", 60).criar(1, "maria")

    with pytest.raises(TokenInvalidoError):
        GerenciadorToken(SEGREDO, 60).decodificar(token)


def test_token_sem_sub_e_invalido():
    token = jwt.encode({"exp": datetime.now(UTC) + timedelta(minutes=5)}, SEGREDO, "HS256")

    with pytest.raises(TokenInvalidoError):
        GerenciadorToken(SEGREDO, 60).decodificar(token)
