import pytest
from pydantic import ValidationError

from app.schemas.auth import CadastroRequest, LoginRequest


def test_cadastro_normaliza_usuario_e_nome():
    dados = CadastroRequest(
        nome_completo="  Maria da Silva  ", usuario="  Maria.Silva ", senha="SenhaForte123"
    )

    assert dados.nome_completo == "Maria da Silva"
    assert dados.usuario == "maria.silva"


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("nome_completo", "Ma"),
        ("usuario", "ma"),
        ("usuario", "maria silva"),
        ("usuario", "maria@silva"),
        ("senha", "curta1"),
        ("senha", "somenteletras"),
        ("senha", "12345678"),
        ("senha", "a1" * 65),
    ],
)
def test_cadastro_rejeita_valores_invalidos(campo, valor):
    dados = {"nome_completo": "Maria da Silva", "usuario": "maria.silva", "senha": "SenhaForte123"}
    dados[campo] = valor

    with pytest.raises(ValidationError):
        CadastroRequest(**dados)


def test_login_normaliza_usuario():
    assert LoginRequest(usuario=" MARIA.Silva ", senha="x").usuario == "maria.silva"
