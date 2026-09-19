from collections.abc import Iterator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import TokenInvalidoError
from app.core.security import GerenciadorToken, HasherSenha
from app.models import Usuario
from app.repositories.health_repository import HealthRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.analise_service import AnaliseService
from app.services.auth_service import AuthService
from app.services.catalogo_service import CatalogoService
from app.services.fabrica import (
    criar_analise_service,
    criar_catalogo_service,
    criar_importacao_service,
)
from app.services.health_service import HealthService
from app.services.importacao_service import ImportacaoService
from app.services.usuario_service import UsuarioService


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_health_service(db: Session = Depends(get_db)) -> HealthService:
    return HealthService(HealthRepository(db))


_hasher = HasherSenha()
_bearer = HTTPBearer(auto_error=False)


def get_hasher() -> HasherSenha:
    return _hasher


def get_gerenciador_token(settings: Settings = Depends(get_settings_dep)) -> GerenciadorToken:
    return GerenciadorToken(settings.jwt_secret, settings.jwt_expira_minutos)


def get_usuario_service(
    db: Session = Depends(get_db), hasher: HasherSenha = Depends(get_hasher)
) -> UsuarioService:
    return UsuarioService(UsuarioRepository(db), hasher)


def get_auth_service(
    db: Session = Depends(get_db),
    hasher: HasherSenha = Depends(get_hasher),
    tokens: GerenciadorToken = Depends(get_gerenciador_token),
) -> AuthService:
    return AuthService(UsuarioRepository(db), hasher, tokens)


def get_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth: AuthService = Depends(get_auth_service),
) -> Usuario:
    """Protege a rota: exige 'Authorization: Bearer <jwt>' válido."""
    if credenciais is None:
        raise TokenInvalidoError("Não autenticado")
    return auth.usuario_do_token(credenciais.credentials)


def get_catalogo_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)
) -> CatalogoService:
    return criar_catalogo_service(db, settings)


def get_importacao_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)
) -> ImportacaoService:
    return criar_importacao_service(db, settings)


def get_analise_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)
) -> AnaliseService:
    return criar_analise_service(db, settings)
