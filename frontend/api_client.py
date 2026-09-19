"""Cliente HTTP da API Holder — único ponto do front que faz requisições."""

from __future__ import annotations

import os
from typing import Any

import httpx

URL_PADRAO = "http://localhost:8000/api"


class ApiErro(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class NaoAutenticado(ApiErro):
    """401: token ausente/inválido/expirado, ou credenciais erradas no login."""


def _mensagem(resposta: httpx.Response) -> str:
    try:
        corpo = resposta.json()
    except ValueError:
        return f"Erro {resposta.status_code} na API"
    detail = corpo.get("detail") if isinstance(corpo, dict) else None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        partes = []
        for erro in detail:
            campo = (erro.get("loc") or [""])[-1]
            texto = str(erro.get("msg", "")).removeprefix("Value error, ")
            partes.append(f"{campo}: {texto}" if campo else texto)
        return "; ".join(partes)
    return f"Erro {resposta.status_code} na API"


class ApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("API_URL") or URL_PADRAO).rstrip("/")
        cabecalhos = {"Authorization": f"Bearer {token}"} if token else {}
        self._http = httpx.Client(
            base_url=self.base_url, headers=cabecalhos, transport=transport, timeout=timeout
        )

    def _requisitar(self, metodo: str, caminho: str, **kwargs: Any) -> Any:
        try:
            resposta = self._http.request(metodo, caminho, **kwargs)
        except httpx.HTTPError as erro:
            raise ApiErro(
                0,
                f"Não foi possível conectar à API em {self.base_url}. "
                "Verifique se o backend está rodando.",
            ) from erro
        if resposta.status_code == 401:
            raise NaoAutenticado(401, _mensagem(resposta))
        if resposta.is_error:
            raise ApiErro(resposta.status_code, _mensagem(resposta))
        return resposta.json()

    # --- autenticação
    def cadastrar(self, nome_completo: str, usuario: str, senha: str) -> dict:
        corpo = {"nome_completo": nome_completo, "usuario": usuario, "senha": senha}
        return self._requisitar("POST", "/auth/cadastro", json=corpo)

    def login(self, usuario: str, senha: str) -> dict:
        return self._requisitar("POST", "/auth/login", json={"usuario": usuario, "senha": senha})

    def me(self) -> dict:
        return self._requisitar("GET", "/auth/me")

    # --- dashboard
    def resumo_dashboard(self) -> dict:
        return self._requisitar("GET", "/dashboard/resumo")

    def fila(self, limite: int = 10) -> list[dict]:
        return self._requisitar("GET", "/dashboard/fila", params={"limite": limite})

    # --- clientes
    def listar_clientes(self, **filtros: Any) -> dict:
        params = {chave: valor for chave, valor in filtros.items() if valor not in (None, "")}
        return self._requisitar("GET", "/clientes", params=params)

    def cliente(self, cliente_id: str) -> dict:
        return self._requisitar("GET", f"/clientes/{cliente_id}")

    def historico(self, cliente_id: str) -> dict:
        return self._requisitar("GET", f"/clientes/{cliente_id}/historico")

    # --- métricas
    def variaveis_metricas(self) -> list[dict]:
        return self._requisitar("GET", "/metricas/variaveis")

    def metrica_mensal(self, variavel: str, agregacao: str = "media") -> list[dict]:
        params = {"variavel": variavel, "agregacao": agregacao}
        return self._requisitar("GET", "/metricas/mensal", params=params)

    # --- catálogo e análise
    def sinais(self) -> list[dict]:
        return self._requisitar("GET", "/sinais")

    def acoes(self) -> list[dict]:
        return self._requisitar("GET", "/acoes-recomendadas")

    def executar_analise(self) -> dict:
        return self._requisitar("POST", "/analise/executar")

    def importar(self, nome_arquivo: str, conteudo: bytes) -> dict:
        tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        arquivos = {"arquivo": (nome_arquivo, conteudo, tipo)}
        return self._requisitar("POST", "/importacao", files=arquivos, timeout=120.0)
