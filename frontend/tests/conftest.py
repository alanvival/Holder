import httpx
import pytest

import auth
from api_client import ApiClient


class ApiFalsa:
    """API simulada: respostas por (método, caminho sem /api) e registro das requisições."""

    def __init__(self) -> None:
        self.rotas: dict[tuple[str, str], tuple[int, object]] = {}
        self.requisicoes: list[httpx.Request] = []

    def responder(self, metodo: str, caminho: str, status: int = 200, corpo: object = None) -> None:
        self.rotas[(metodo, caminho)] = (status, corpo)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requisicoes.append(request)
        chave = (request.method, request.url.path.removeprefix("/api"))
        if chave not in self.rotas:
            return httpx.Response(404, json={"detail": f"rota não simulada: {chave}"})
        status, corpo = self.rotas[chave]
        return httpx.Response(status, json=corpo)

    def cliente(self, token: str | None = None) -> ApiClient:
        return ApiClient(
            base_url="http://api.teste/api",
            token=token,
            transport=httpx.MockTransport(self.handler),
        )


@pytest.fixture
def api_falsa(monkeypatch: pytest.MonkeyPatch) -> ApiFalsa:
    falsa = ApiFalsa()
    monkeypatch.setattr(auth, "fabrica_cliente", falsa.cliente)
    return falsa
