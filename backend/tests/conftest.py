from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite://",
        jwt_secret="segredo-de-teste-com-mais-de-32-bytes-ok",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session(app: FastAPI) -> Iterator[Session]:
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def caminho_xlsx() -> Path:
    return Path(__file__).resolve().parents[2] / "INOVAAPPS_base_de_dados.xlsx"


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/auth/cadastro",
        json={"nome_completo": "Usuária Teste", "usuario": "teste", "senha": "SenhaForte123"},
    )
    resposta = client.post("/api/auth/login", json={"usuario": "teste", "senha": "SenhaForte123"})
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
def client_com_base(
    client: TestClient, auth_headers: dict[str, str], caminho_xlsx: Path
) -> TestClient:
    resposta = client.post(
        "/api/importacao",
        headers=auth_headers,
        files={"arquivo": ("base.xlsx", caminho_xlsx.read_bytes())},
    )
    assert resposta.status_code == 200, resposta.text
    return client
