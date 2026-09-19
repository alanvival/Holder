from app.core.database import agora_utc
from app.core.exceptions import (
    CredenciaisInvalidasError,
    TokenInvalidoError,
    UsuarioInativoError,
)
from app.core.security import GerenciadorToken, HasherSenha
from app.models import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.usuario import UsuarioResumo


class AuthService:
    """Login e validação de token.

    Regra: usuário inexistente e senha errada geram o mesmo erro, para não revelar
    quais usuários existem.
    """

    def __init__(
        self, repo: UsuarioRepository, hasher: HasherSenha, tokens: GerenciadorToken
    ) -> None:
        self._repo = repo
        self._hasher = hasher
        self._tokens = tokens

    def autenticar(self, dados: LoginRequest) -> TokenResponse:
        usuario = self._repo.obter_por_usuario(dados.usuario)
        if usuario is None:
            self._hasher.verificar_ficticio(dados.senha)
            raise CredenciaisInvalidasError()
        if not self._hasher.verificar(dados.senha, usuario.senha_hash):
            raise CredenciaisInvalidasError()
        if not usuario.ativo:
            raise UsuarioInativoError()
        usuario.ultimo_login_em = agora_utc()
        self._repo.salvar(usuario)
        token, expira_em = self._tokens.criar(usuario.id, usuario.usuario)
        return TokenResponse(
            access_token=token,
            expira_em=expira_em,
            usuario=UsuarioResumo.model_validate(usuario),
        )

    def usuario_do_token(self, token: str) -> Usuario:
        payload = self._tokens.decodificar(token)
        try:
            usuario_id = int(payload["sub"])
        except (KeyError, ValueError) as erro:
            raise TokenInvalidoError() from erro
        usuario = self._repo.obter_por_id(usuario_id)
        if usuario is None:
            raise TokenInvalidoError()
        if not usuario.ativo:
            raise UsuarioInativoError()
        return usuario
