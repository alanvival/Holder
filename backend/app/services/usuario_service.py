from app.core.exceptions import RecursoNaoEncontradoError, UsuarioJaExisteError
from app.core.security import HasherSenha
from app.models import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import CadastroRequest


class UsuarioService:
    """Cadastro de usuários: usuário único (minúsculas) e senha guardada só como hash."""

    def __init__(self, repo: UsuarioRepository, hasher: HasherSenha) -> None:
        self._repo = repo
        self._hasher = hasher

    def cadastrar(self, dados: CadastroRequest) -> Usuario:
        if self._repo.obter_por_usuario(dados.usuario) is not None:
            raise UsuarioJaExisteError()
        usuario = Usuario(
            nome_completo=dados.nome_completo,
            usuario=dados.usuario,
            senha_hash=self._hasher.gerar_hash(dados.senha),
            ativo=True,
        )
        return self._repo.adicionar(usuario)

    def obter_por_id(self, usuario_id: int) -> Usuario:
        usuario = self._repo.obter_por_id(usuario_id)
        if usuario is None:
            raise RecursoNaoEncontradoError("Usuário não encontrado")
        return usuario
