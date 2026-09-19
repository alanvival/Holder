from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ErroDominio


def registrar_handlers(app: FastAPI) -> None:
    """Converte exceções de domínio em respostas HTTP {"detail": mensagem}."""

    @app.exception_handler(ErroDominio)
    async def tratar_erro_dominio(request: Request, exc: ErroDominio) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.mensagem}, headers=headers
        )
