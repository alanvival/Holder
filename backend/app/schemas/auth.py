from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.usuario import UsuarioResumo

REGEX_USUARIO = r"^[a-zA-Z0-9._-]+$"


def _normalizar_usuario(valor: object) -> object:
    return valor.strip().lower() if isinstance(valor, str) else valor


class CadastroRequest(BaseModel):
    nome_completo: str = Field(min_length=3, max_length=150, examples=["Maria da Silva"])
    usuario: str = Field(
        min_length=3, max_length=50, pattern=REGEX_USUARIO, examples=["maria.silva"]
    )
    senha: str = Field(min_length=8, max_length=128, examples=["SenhaForte123"])

    @field_validator("nome_completo", mode="before")
    @classmethod
    def _strip_nome(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("usuario", mode="before")
    @classmethod
    def _normalizar(cls, valor: object) -> object:
        return _normalizar_usuario(valor)

    @field_validator("senha")
    @classmethod
    def _senha_forte(cls, valor: str) -> str:
        if not any(c.isalpha() for c in valor) or not any(c.isdigit() for c in valor):
            raise ValueError("A senha deve conter ao menos uma letra e um número")
        return valor


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=1, max_length=50, examples=["maria.silva"])
    senha: str = Field(min_length=1, max_length=128, examples=["SenhaForte123"])

    @field_validator("usuario", mode="before")
    @classmethod
    def _normalizar(cls, valor: object) -> object:
        return _normalizar_usuario(valor)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expira_em: datetime
    usuario: UsuarioResumo
