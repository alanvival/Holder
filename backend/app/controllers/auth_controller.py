from fastapi import APIRouter, Depends, status

from app.dependencies import get_auth_service, get_usuario_atual, get_usuario_service
from app.models import Usuario
from app.schemas.auth import CadastroRequest, LoginRequest, TokenResponse
from app.schemas.usuario import UsuarioResponse
from app.services.auth_service import AuthService
from app.services.usuario_service import UsuarioService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/cadastro", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def cadastrar(
    dados: CadastroRequest, service: UsuarioService = Depends(get_usuario_service)
) -> Usuario:
    return service.cadastrar(dados)


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    return service.autenticar(dados)


@router.get("/me", response_model=UsuarioResponse)
def me(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
    return usuario
