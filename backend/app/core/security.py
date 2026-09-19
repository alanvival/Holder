from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.exceptions import TokenInvalidoError


class HasherSenha:
    """Hash de senha com argon2 (pwdlib)."""

    def __init__(self) -> None:
        self._hash = PasswordHash((Argon2Hasher(),))
        self._hash_ficticio: str | None = None

    def gerar_hash(self, senha: str) -> str:
        return self._hash.hash(senha)

    def verificar(self, senha: str, senha_hash: str) -> bool:
        try:
            return self._hash.verify(senha, senha_hash)
        except Exception:
            return False

    def verificar_ficticio(self, senha: str) -> bool:
        """Gasta o mesmo tempo de uma verificação real (usuário inexistente) e retorna False."""
        if self._hash_ficticio is None:
            self._hash_ficticio = self._hash.hash("senha-ficticia-0")
        self.verificar(senha, self._hash_ficticio)
        return False


class GerenciadorToken:
    """Cria e valida JWT HS256 com sub (id do usuário), usuario, iat e exp."""

    ALGORITMO = "HS256"

    def __init__(self, segredo: str, expira_minutos: int) -> None:
        self._segredo = segredo
        self._expira_minutos = expira_minutos

    def criar(self, usuario_id: int, usuario: str) -> tuple[str, datetime]:
        agora = datetime.now(UTC)
        expira_em = agora + timedelta(minutes=self._expira_minutos)
        payload = {"sub": str(usuario_id), "usuario": usuario, "iat": agora, "exp": expira_em}
        return jwt.encode(payload, self._segredo, algorithm=self.ALGORITMO), expira_em

    def decodificar(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self._segredo,
                algorithms=[self.ALGORITMO],
                options={"require": ["sub", "exp", "iat"]},
            )
        except jwt.PyJWTError as erro:
            raise TokenInvalidoError() from erro
