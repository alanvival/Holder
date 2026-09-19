"""Exceções de domínio. Não dependem de FastAPI; os handlers HTTP ficam em handlers.py."""


class ErroDominio(Exception):
    status_code: int = 400
    mensagem_padrao: str = "Erro de domínio"

    def __init__(self, mensagem: str | None = None) -> None:
        self.mensagem = mensagem or self.mensagem_padrao
        super().__init__(self.mensagem)


class UsuarioJaExisteError(ErroDominio):
    status_code = 409
    mensagem_padrao = "Usuário já cadastrado"


class CredenciaisInvalidasError(ErroDominio):
    status_code = 401
    mensagem_padrao = "Usuário ou senha inválidos"


class UsuarioInativoError(ErroDominio):
    status_code = 403
    mensagem_padrao = "Usuário inativo"


class TokenInvalidoError(ErroDominio):
    status_code = 401
    mensagem_padrao = "Token inválido ou expirado"


class RecursoNaoEncontradoError(ErroDominio):
    status_code = 404
    mensagem_padrao = "Recurso não encontrado"


class ImportacaoInvalidaError(ErroDominio):
    status_code = 422
    mensagem_padrao = "Arquivo de importação inválido"


class ParametroInvalidoError(ErroDominio):
    status_code = 422
    mensagem_padrao = "Parâmetro inválido"
