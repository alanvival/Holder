# MVP Backend FastAPI + Streamlit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar um backend FastAPI em MVC (auth JWT, importação do xlsx, motor de risco simples por regras, endpoints de consulta) e um front Streamlit multipágina (login/cadastro, dashboard com fila priorizada, clientes, análise mensal) que consome apenas a API.

**Architecture:** `backend/` segue MVC adaptado para API: `models/` (SQLAlchemy), `repositories/` (única camada com queries), `services/` (regras; `services/risco/` são funções puras com pandas), `controllers/` (routers que só chamam services), `schemas/` (DTOs Pydantic = View). Banco SQLite via `DATABASE_URL` com tipos genéricos (troca futura para SQL Server só pela URL). `frontend/` é um app Streamlit multipágina com um `api_client.py` (httpx) como único ponto de HTTP.

**Tech Stack:** Python ≥3.12 (local: 3.14), FastAPI, SQLAlchemy 2.0, Pydantic v2 + pydantic-settings, pwdlib[argon2], PyJWT, pandas 3, openpyxl, pytest + httpx TestClient, ruff; Streamlit ≥1.50, Plotly.

**Spec:** `docs/superpowers/specs/2026-09-19-mvp-backend-streamlit-design.md`

## Global Constraints

- Todos os comandos rodam no **Git Bash** a partir da raiz do repo `C:\Git\Holder` (caminho `/c/Git/Holder`). Um único venv na raiz: `.venv` (Windows: `.venv/Scripts/python`).
- Rodar testes do backend: `cd backend && ../.venv/Scripts/python -m pytest <alvo> -v`. Testes do frontend: `cd frontend && ../.venv/Scripts/python -m pytest <alvo> -v`.
- Commits: o git desta máquina não tem identidade configurada. **Nunca** altere a config global. Commite sempre com
  `git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "<mensagem>" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"`
- Nomes de domínio em português; termos de framework em inglês. Type hints em tudo; docstrings curtas nos services explicando a regra de negócio.
- Controller chama **apenas** services. Service nunca importa `fastapi`. Repository recebe `Session` e só faz I/O. `pandas` só em `services/` e `scripts/`. Services recebem dependências pelo construtor.
- Só tipos genéricos do SQLAlchemy (`String`, `Unicode`, `UnicodeText`, `Numeric`, `Date`, `DateTime`, `Boolean`, `Integer`); enums com `native_enum=False` (VARCHAR com o nome do membro). Nada de `NULLS LAST` ou SQL específico de dialeto.
- Schemas de resposta usam `float` (não `Decimal`) para valores numéricos, para o JSON sair como número.
- Valores de negócio configuráveis ficam em `Settings` (`capacidade_fila`, `limiar_critico=0.55`, `limiar_atencao=0.30`, `limiar_monitorar=0.15`, `persistencia_min_meses=2`) ou em `configuracoes_sinal`; nunca fixos no código.
- Nunca retornar `senha_hash`. Login com usuário inexistente e senha errada devolvem **a mesma** mensagem `"Usuário ou senha inválidos"` (401).
- Corpo de erro da API: `{"detail": "<mensagem>"}`.
- `pct_sla_cumprido` vazio fica `NULL` (nunca 0/100). NPS `Sem resposta` é o valor `SEM_RESPOSTA`, não dado faltante. Meses `AAAA-MM` viram `date(ano, mes, 1)`.
- Indicadores do mês M usam somente dados ≤ M.
- `ruff check .` e `ruff format --check .` limpos em `backend/` e `frontend/` ao fim de cada tarefa (config em cada `pyproject.toml`).
- Não tocar em `app.py`, `ingestao.py`, `analise_sla.py`, `assistente-consultas/` nem no xlsx da raiz.

## Review Focus

- Usuário digitado com maiúsculas/espaços no login ou cadastro (`"  Maria.Silva "`) deve funcionar como `maria.silva` — teste na Task 4.
- Banco vazio (antes de qualquer importação): dashboard/fila/listagem devem responder vazio (200), e `POST /analise/executar` deve responder 404 com mensagem clara — testes nas Tasks 8 e 9.
- Upload de arquivo que não é xlsx, ou xlsx sem uma aba/coluna: 422 com mensagem clara **e os dados anteriores preservados** — teste na Task 5.
- Token expirado/inválido no Streamlit: o usuário volta para o login com aviso, sem traceback — testes nas Tasks 11 e 12.
- API fora do ar quando o Streamlit roda: mensagem amigável ("Não foi possível conectar à API..."), sem traceback — teste na Task 11.

---

## File Structure

```
.gitignore                                   (Task 1)
backend/
  pyproject.toml, .env.example               (Task 1)
  app/__init__.py, app/main.py               (Task 1; routers adicionados nas Tasks 4,5,8,9,10)
  app/dependencies.py                        (Task 1; ampliado 4,5,8,9,10)
  app/core/config.py, database.py            (Task 1)
  app/core/enums.py                          (Task 2)
  app/core/exceptions.py, handlers.py, security.py   (Task 3)
  app/models/*.py                            (Task 2)
  app/repositories/health_repository.py      (Task 1)
  app/services/health_service.py             (Task 1)
  app/controllers/health_controller.py       (Task 1)
  app/schemas/usuario.py, auth.py            (Task 4)
  app/repositories/usuario_repository.py     (Task 4)
  app/services/usuario_service.py, auth_service.py   (Task 4)
  app/controllers/auth_controller.py         (Task 4)
  app/services/catalogo_seed.py, catalogo_service.py (Task 5)
  app/repositories/origem_repository.py, sinal_repository.py, acao_repository.py (Task 5)
  app/services/importacao_service.py, fabrica.py     (Task 5)
  app/schemas/importacao.py                  (Task 5)
  app/controllers/importacao_controller.py   (Task 5)
  scripts/importar_base.py                   (Task 5; análise ligada na Task 8)
  app/services/risco/indicadores.py          (Task 6)
  app/services/risco/sinais.py, score.py, recomendacao.py, priorizacao.py (Task 7)
  app/repositories/cliente_repository.py, atendimento_repository.py, nps_repository.py, execucao_repository.py (Task 8)
  app/services/analise_service.py            (Task 8)
  app/schemas/analise.py                     (Task 8)
  app/controllers/analise_controller.py      (Task 8)
  scripts/rodar_analise.py                   (Task 8)
  app/repositories/avaliacao_repository.py   (Task 9)
  app/schemas/comum.py, risco.py, dashboard.py, catalogo.py (Task 9)
  app/services/mapeadores.py, dashboard_service.py   (Task 9)
  app/controllers/dashboard_controller.py, catalogo_controller.py (Task 9)
  app/schemas/cliente.py, metrica.py         (Task 10)
  app/services/cliente_service.py, metrica_service.py (Task 10)
  app/controllers/cliente_controller.py, metrica_controller.py (Task 10)
  tests/conftest.py, tests/unit/*, tests/integration/*
frontend/
  pyproject.toml, requirements.txt, .streamlit/config.toml  (Task 11)
  api_client.py, auth.py, formatacao.py, Home.py            (Task 11)
  pages/1_Dashboard.py, 2_Clientes.py, 3_Analise_Mensal.py  (Task 12)
  tests/conftest.py, tests/test_*.py
README.md (raiz), backend/README.md, .claude/launch.json    (Task 13)
```

---

### Task 1: Fundação do backend (config, banco, health, testes)

**Files:**
- Create: `.gitignore`, `backend/pyproject.toml`, `backend/.env.example`
- Create: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/core/database.py`
- Create: `backend/app/models/__init__.py` (vazio por enquanto), `backend/app/schemas/__init__.py`, `backend/app/repositories/__init__.py`, `backend/app/services/__init__.py`, `backend/app/controllers/__init__.py` (todos vazios)
- Create: `backend/app/repositories/health_repository.py`, `backend/app/services/health_service.py`, `backend/app/controllers/health_controller.py`
- Create: `backend/app/dependencies.py`, `backend/app/main.py`
- Test: `backend/tests/__init__.py` (vazio), `backend/tests/conftest.py`, `backend/tests/integration/__init__.py` (vazio), `backend/tests/unit/__init__.py` (vazio), `backend/tests/integration/test_health.py`

**Interfaces:**
- Produces: `Settings` (campos abaixo) e `get_settings()`; `Base`, `criar_engine(url) -> Engine`, `agora_utc() -> datetime` (naive UTC); `create_app(settings: Settings | None = None) -> FastAPI` que guarda `app.state.settings`, `app.state.engine`, `app.state.session_factory`; dependências `get_settings_dep(request) -> Settings` e `get_db(request) -> Iterator[Session]`; fixtures pytest `settings`, `app`, `client`, `db_session`.

- [ ] **Step 1: Criar venv e arquivos de projeto**

`.gitignore` (raiz):
```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
*.db
.env
*.egg-info/
build/
```

`backend/pyproject.toml`:
```toml
[project]
name = "holder-backend"
version = "0.1.0"
description = "API de risco de churn (INOVAAPPS 2026) — MVP"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "sqlalchemy>=2.0.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "pwdlib[argon2]>=0.2",
  "PyJWT>=2.8",
  "pandas>=2.2",
  "numpy>=1.26",
  "openpyxl>=3.1",
  "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27", "ruff>=0.5"]
sqlserver = ["pyodbc>=5"]

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*", "scripts*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["B008"]  # Depends(...) em default de parâmetro é o padrão do FastAPI
```

`backend/.env.example`:
```dotenv
# SQLite local (MVP). Para SQL Server (futuro):
# DATABASE_URL=mssql+pyodbc://sa:SenhaForte!123@localhost:1433/INOVAAPPS?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
DATABASE_URL=sqlite:///./holder.db
JWT_SECRET=trocar-em-producao-use-uma-chave-longa-e-aleatoria
JWT_EXPIRA_MINUTOS=480
CORS_ORIGENS=http://localhost:8501,http://localhost:5173
CAPACIDADE_FILA=10
LIMIAR_CRITICO=0.55
LIMIAR_ATENCAO=0.30
LIMIAR_MONITORAR=0.15
PERSISTENCIA_MIN_MESES=2
CAMINHO_XLSX=../INOVAAPPS_base_de_dados.xlsx
```

Run:
```bash
py -m venv .venv && .venv/Scripts/python -m pip install -q --upgrade pip && .venv/Scripts/python -m pip install -q -e "backend[dev]"
```
Expected: instala sem erro. (`py` é o launcher do Windows; o Python local é 3.14.)

Crie os `__init__.py` vazios listados em **Files**.

- [ ] **Step 2: Escrever o teste que falha**

`backend/tests/conftest.py`:
```python
from collections.abc import Iterator

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
```

`backend/tests/integration/test_health.py`:
```python
def test_health_retorna_ok_com_banco(client):
    resposta = client.get("/api/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "banco": "ok"}


def test_cors_libera_origem_do_streamlit(client):
    resposta = client.get("/api/health", headers={"Origin": "http://localhost:8501"})

    assert resposta.headers["access-control-allow-origin"] == "http://localhost:8501"
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/integration/test_health.py -v`
Expected: FAIL/ERROR com `ModuleNotFoundError: No module named 'app.core.config'` (ou `app.main`).

- [ ] **Step 4: Implementar**

`backend/app/core/config.py`:
```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da aplicação, lida de variáveis de ambiente / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./holder.db"
    jwt_secret: str = "trocar-em-producao-use-uma-chave-longa-e-aleatoria"
    jwt_expira_minutos: int = 480
    cors_origens: str = "http://localhost:8501,http://localhost:5173"
    capacidade_fila: int = 10
    limiar_critico: float = 0.55
    limiar_atencao: float = 0.30
    limiar_monitorar: float = 0.15
    persistencia_min_meses: int = 2
    caminho_xlsx: str = "../INOVAAPPS_base_de_dados.xlsx"

    @property
    def lista_cors(self) -> list[str]:
        return [origem.strip() for origem in self.cors_origens.split(",") if origem.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/app/core/database.py`:
```python
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def criar_engine(url: str) -> Engine:
    """Cria a engine conforme o banco: SQLite (MVP/testes) ou SQL Server (futuro)."""
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    if url.startswith("mssql"):
        return create_engine(url, fast_executemany=True)
    return create_engine(url)


def agora_utc() -> datetime:
    """Data/hora atual em UTC, sem tzinfo (DATETIME2 / SQLite)."""
    return datetime.now(UTC).replace(tzinfo=None)
```

`backend/app/repositories/health_repository.py`:
```python
from sqlalchemy import text
from sqlalchemy.orm import Session


class HealthRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ping(self) -> bool:
        try:
            self._session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
```

`backend/app/services/health_service.py`:
```python
from app.repositories.health_repository import HealthRepository


class HealthService:
    """Informa se a API está no ar e se o banco responde."""

    def __init__(self, repo: HealthRepository) -> None:
        self._repo = repo

    def status(self) -> dict[str, str]:
        return {"status": "ok", "banco": "ok" if self._repo.ping() else "erro"}
```

`backend/app/dependencies.py`:
```python
from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.health_repository import HealthRepository
from app.services.health_service import HealthService


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
```

`backend/app/controllers/health_controller.py`:
```python
from fastapi import APIRouter, Depends

from app.dependencies import get_health_service
from app.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health")
def health(service: HealthService = Depends(get_health_service)) -> dict[str, str]:
    return service.status()
```

`backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registra os models no metadata)
from app.controllers import health_controller
from app.core.config import Settings, get_settings
from app.core.database import Base, criar_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    """Fábrica da aplicação. Rode com: uvicorn app.main:create_app --factory"""
    settings = settings or get_settings()
    engine = criar_engine(settings.database_url)
    Base.metadata.create_all(engine)

    app = FastAPI(title="Holder — API de risco de churn", version="0.1.0")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.lista_cors,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_controller.router, prefix="/api")
    return app
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/integration/test_health.py -v`
Expected: 2 passed.

Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`
Expected: sem erros (se `format --check` acusar, rode `ruff format .` e repita).

- [ ] **Step 6: Commit**

```bash
git add .gitignore backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): fundação FastAPI com config, banco e /api/health" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Enums e models

**Files:**
- Create: `backend/app/core/enums.py`
- Create: `backend/app/models/_tipos.py`, `usuario.py`, `cliente.py`, `situacao_cliente.py`, `atendimento_mensal.py`, `pesquisa_nps.py`, `configuracao_sinal.py`, `acao_recomendada.py`, `execucao_analise.py`, `avaliacao_risco.py`, `evidencia_risco.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/unit/test_models.py`

**Interfaces:**
- Consumes: `Base`, `agora_utc` (Task 1).
- Produces: enums `Porte, Plano, SituacaoCliente, ClassificacaoNPS, Dimensao, TipoRegra, SentidoPiora, FaixaRisco, TipoExecucao, Responsavel` (StrEnum, valor == nome); models `Usuario, Cliente, Situacao, AtendimentoMensal, PesquisaNps, ConfiguracaoSinal, AcaoRecomendada, ExecucaoAnalise, AvaliacaoRisco, EvidenciaRisco`, todos importáveis de `app.models`. Relações: `Cliente.situacao` (1:1, `Situacao | None`), `ExecucaoAnalise.avaliacoes` (cascade), `ExecucaoAnalise.qtd_na_fila` (property int), `AvaliacaoRisco.cliente/.acao_recomendada/.evidencias` (evidências em ordem de `id`), `EvidenciaRisco.sinal`.

- [ ] **Step 1: Escrever o teste que falha**

`backend/tests/unit/test_models.py`:
```python
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.enums import FaixaRisco, Plano, Porte, SituacaoCliente, TipoExecucao
from app.models import (
    AtendimentoMensal,
    AvaliacaoRisco,
    Cliente,
    ExecucaoAnalise,
    Situacao,
)

TABELAS = {
    "usuarios",
    "clientes",
    "situacao_clientes",
    "atendimentos_mensais",
    "pesquisas_nps",
    "configuracoes_sinal",
    "acoes_recomendadas",
    "execucoes_analise",
    "avaliacoes_risco",
    "evidencias_risco",
}


def _cliente(cliente_id: str = "C001") -> Cliente:
    return Cliente(
        cliente_id=cliente_id,
        segmento="Saude",
        porte=Porte.MEDIO,
        plano=Plano.AVANCADO,
        valor_mensal=Decimal("10742.00"),
        sla_contratado_h=12,
        inicio_contrato=date(2020, 2, 1),
    )


def _atendimento(mes: date, pct_sla: Decimal | None = Decimal("64.3")) -> AtendimentoMensal:
    return AtendimentoMensal(
        cliente_id="C001",
        mes_ref=mes,
        chamados_abertos=14,
        chamados_criticos=3,
        chamados_reabertos=5,
        chamados_dentro_sla=9,
        pct_sla_cumprido=pct_sla,
        tempo_medio_resolucao_h=Decimal("22.4"),
        reclamacoes_formais=1,
        uso_plataforma_pct=Decimal("74.5"),
        dias_atraso_pagamento=13,
        reunioes_previstas=1,
        reunioes_realizadas=0,
    )


def test_create_all_cria_todas_as_tabelas_do_mvp(app):
    assert TABELAS <= set(inspect(app.state.engine).get_table_names())


def test_atendimento_unico_por_cliente_e_mes(db_session):
    db_session.add(_cliente())
    db_session.add(_atendimento(date(2025, 1, 1)))
    db_session.commit()

    db_session.add(_atendimento(date(2025, 1, 1)))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_pct_sla_nulo_e_enum_como_texto_sao_preservados(db_session):
    db_session.add(_cliente())
    db_session.add(Situacao(cliente_id="C001", situacao=SituacaoCliente.ATIVO))
    db_session.add(_atendimento(date(2025, 2, 1), pct_sla=None))
    db_session.commit()

    atendimento = db_session.query(AtendimentoMensal).one()
    assert atendimento.pct_sla_cumprido is None
    bruto = db_session.execute(text("SELECT porte, plano FROM clientes")).one()
    assert tuple(bruto) == ("MEDIO", "AVANCADO")
    assert db_session.get(Cliente, "C001").situacao.situacao == SituacaoCliente.ATIVO


def test_execucao_conta_clientes_na_fila(db_session):
    db_session.add(_cliente("C001"))
    db_session.add(_cliente("C002"))
    execucao = ExecucaoAnalise(
        tipo=TipoExecucao.PRODUCAO,
        mes_referencia=date(2026, 6, 1),
        versao_modelo="teste",
        parametros_json="{}",
        qtd_clientes_avaliados=2,
    )
    for posicao, cliente_id in ((1, "C001"), (None, "C002")):
        execucao.avaliacoes.append(
            AvaliacaoRisco(
                cliente_id=cliente_id,
                mes_referencia=date(2026, 6, 1),
                score_risco=Decimal("0.4"),
                faixa=FaixaRisco.ATENCAO,
                qtd_dimensoes_afetadas=2,
                receita_em_risco=Decimal("100.00"),
                posicao_fila=posicao,
            )
        )
    db_session.add(execucao)
    db_session.commit()

    assert execucao.qtd_na_fila == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/unit/test_models.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.core.enums'`.

- [ ] **Step 3: Implementar enums**

`backend/app/core/enums.py`:
```python
"""Enums de domínio. O valor é igual ao nome e é o que vai para o banco."""

from enum import StrEnum


class Porte(StrEnum):
    PEQUENO = "PEQUENO"
    MEDIO = "MEDIO"
    GRANDE = "GRANDE"


class Plano(StrEnum):
    ESSENCIAL = "ESSENCIAL"
    AVANCADO = "AVANCADO"
    ENTERPRISE = "ENTERPRISE"


class SituacaoCliente(StrEnum):
    ATIVO = "ATIVO"
    CANCELADO = "CANCELADO"


class ClassificacaoNPS(StrEnum):
    PROMOTOR = "PROMOTOR"
    NEUTRO = "NEUTRO"
    DETRATOR = "DETRATOR"
    SEM_RESPOSTA = "SEM_RESPOSTA"


class Dimensao(StrEnum):
    ATENDIMENTO = "ATENDIMENTO"
    SLA = "SLA"
    ENGAJAMENTO = "ENGAJAMENTO"
    FINANCEIRO = "FINANCEIRO"
    SATISFACAO = "SATISFACAO"


class TipoRegra(StrEnum):
    NIVEL = "NIVEL"
    TENDENCIA = "TENDENCIA"
    EVENTO = "EVENTO"


class SentidoPiora(StrEnum):
    AUMENTO = "AUMENTO"
    QUEDA = "QUEDA"


class FaixaRisco(StrEnum):
    CRITICO = "CRITICO"
    ATENCAO = "ATENCAO"
    MONITORAR = "MONITORAR"
    SAUDAVEL = "SAUDAVEL"


class TipoExecucao(StrEnum):
    PRODUCAO = "PRODUCAO"
    CALIBRACAO = "CALIBRACAO"
    BACKTEST = "BACKTEST"


class Responsavel(StrEnum):
    CS = "CS"
    TECNICO = "TECNICO"
    FINANCEIRO = "FINANCEIRO"
    EXECUTIVO = "EXECUTIVO"
```

- [ ] **Step 4: Implementar models**

`backend/app/models/_tipos.py`:
```python
from enum import Enum

from sqlalchemy import Enum as SAEnum


def coluna_enum(enum_cls: type[Enum]) -> SAEnum:
    """Enum guardado como VARCHAR(20) com o nome do membro (portável SQLite/SQL Server)."""
    return SAEnum(enum_cls, native_enum=False, length=20, validate_strings=True)
```

`backend/app/models/usuario.py`:
```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, agora_utc


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_completo: Mapped[str] = mapped_column(Unicode(150))
    usuario: Mapped[str] = mapped_column(Unicode(50), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(Unicode(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    ultimo_login_em: Mapped[datetime | None] = mapped_column(DateTime)
```

`backend/app/models/cliente.py`:
```python
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Numeric, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Plano, Porte
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.situacao_cliente import Situacao


class Cliente(Base):
    __tablename__ = "clientes"

    cliente_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    segmento: Mapped[str] = mapped_column(Unicode(50))
    porte: Mapped[Porte] = mapped_column(coluna_enum(Porte))
    plano: Mapped[Plano] = mapped_column(coluna_enum(Plano))
    valor_mensal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sla_contratado_h: Mapped[int]
    inicio_contrato: Mapped[date] = mapped_column(Date)

    situacao: Mapped["Situacao | None"] = relationship(back_populates="cliente", uselist=False)
```

`backend/app/models/situacao_cliente.py`:
```python
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import SituacaoCliente
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.cliente import Cliente


class Situacao(Base):
    __tablename__ = "situacao_clientes"

    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"), primary_key=True)
    situacao: Mapped[SituacaoCliente] = mapped_column(coluna_enum(SituacaoCliente))
    mes_cancelamento: Mapped[date | None] = mapped_column(Date)

    cliente: Mapped["Cliente"] = relationship(back_populates="situacao")
```

`backend/app/models/atendimento_mensal.py`:
```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AtendimentoMensal(Base):
    __tablename__ = "atendimentos_mensais"
    __table_args__ = (UniqueConstraint("cliente_id", "mes_ref", name="uq_atendimento_cliente_mes"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"), index=True)
    mes_ref: Mapped[date] = mapped_column(Date, index=True)
    chamados_abertos: Mapped[int]
    chamados_criticos: Mapped[int]
    chamados_reabertos: Mapped[int]
    chamados_dentro_sla: Mapped[int]
    pct_sla_cumprido: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    tempo_medio_resolucao_h: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    reclamacoes_formais: Mapped[int]
    uso_plataforma_pct: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    dias_atraso_pagamento: Mapped[int]
    reunioes_previstas: Mapped[int]
    reunioes_realizadas: Mapped[int]
```

`backend/app/models/pesquisa_nps.py`:
```python
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import ClassificacaoNPS
from app.models._tipos import coluna_enum


class PesquisaNps(Base):
    __tablename__ = "pesquisas_nps"
    __table_args__ = (UniqueConstraint("cliente_id", "mes_ref", name="uq_nps_cliente_mes"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"), index=True)
    mes_ref: Mapped[date] = mapped_column(Date)
    respondeu: Mapped[bool] = mapped_column(Boolean)
    nota_nps: Mapped[int | None]
    classificacao_nps: Mapped[ClassificacaoNPS] = mapped_column(coluna_enum(ClassificacaoNPS))
```

`backend/app/models/configuracao_sinal.py`:
```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, agora_utc
from app.core.enums import Dimensao, SentidoPiora, TipoRegra
from app.models._tipos import coluna_enum


class ConfiguracaoSinal(Base):
    """Catálogo de sinais de risco com limiar e peso."""

    __tablename__ = "configuracoes_sinal"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    dimensao: Mapped[Dimensao] = mapped_column(coluna_enum(Dimensao))
    variavel: Mapped[str] = mapped_column(String(50))
    tipo_regra: Mapped[TipoRegra] = mapped_column(coluna_enum(TipoRegra))
    sentido_piora: Mapped[SentidoPiora] = mapped_column(coluna_enum(SentidoPiora))
    limiar: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    metrica: Mapped[str] = mapped_column(String(20), default="media_3m")
    persistencia_min_meses: Mapped[int] = mapped_column(default=2)
    peso: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    lift: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    cobertura_cancelados: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    taxa_falso_alarme: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    antecedencia_media_meses: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    template_evidencia: Mapped[str] = mapped_column(Unicode(300))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, onupdate=agora_utc)
```

`backend/app/models/acao_recomendada.py`:
```python
from sqlalchemy import String, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import Dimensao, Responsavel
from app.models._tipos import coluna_enum


class AcaoRecomendada(Base):
    """Playbook: o que fazer para cada padrão de risco."""

    __tablename__ = "acoes_recomendadas"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    titulo: Mapped[str] = mapped_column(Unicode(150))
    descricao: Mapped[str] = mapped_column(UnicodeText)
    dimensao_gatilho: Mapped[Dimensao | None] = mapped_column(coluna_enum(Dimensao))
    responsavel_sugerido: Mapped[Responsavel] = mapped_column(coluna_enum(Responsavel))
    prazo_dias: Mapped[int]
    ordem: Mapped[int]
```

`backend/app/models/execucao_analise.py`:
```python
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, agora_utc
from app.core.enums import TipoExecucao
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.avaliacao_risco import AvaliacaoRisco


class ExecucaoAnalise(Base):
    __tablename__ = "execucoes_analise"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoExecucao] = mapped_column(coluna_enum(TipoExecucao))
    mes_referencia: Mapped[date] = mapped_column(Date)
    versao_modelo: Mapped[str] = mapped_column(String(20))
    parametros_json: Mapped[str] = mapped_column(UnicodeText)
    executado_por_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    executado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    qtd_clientes_avaliados: Mapped[int]

    avaliacoes: Mapped[list["AvaliacaoRisco"]] = relationship(
        back_populates="execucao", cascade="all, delete-orphan"
    )

    @property
    def qtd_na_fila(self) -> int:
        return sum(1 for avaliacao in self.avaliacoes if avaliacao.posicao_fila is not None)
```

`backend/app/models/avaliacao_risco.py`:
```python
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import FaixaRisco
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.acao_recomendada import AcaoRecomendada
    from app.models.cliente import Cliente
    from app.models.evidencia_risco import EvidenciaRisco
    from app.models.execucao_analise import ExecucaoAnalise


class AvaliacaoRisco(Base):
    __tablename__ = "avaliacoes_risco"
    __table_args__ = (
        UniqueConstraint("execucao_id", "cliente_id", name="uq_avaliacao_execucao_cliente"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    execucao_id: Mapped[int] = mapped_column(ForeignKey("execucoes_analise.id"), index=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"))
    mes_referencia: Mapped[date] = mapped_column(Date)
    score_risco: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    faixa: Mapped[FaixaRisco] = mapped_column(coluna_enum(FaixaRisco))
    qtd_dimensoes_afetadas: Mapped[int]
    receita_em_risco: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    posicao_fila: Mapped[int | None]
    acao_recomendada_id: Mapped[int | None] = mapped_column(ForeignKey("acoes_recomendadas.id"))

    execucao: Mapped["ExecucaoAnalise"] = relationship(back_populates="avaliacoes")
    cliente: Mapped["Cliente"] = relationship()
    acao_recomendada: Mapped["AcaoRecomendada | None"] = relationship()
    evidencias: Mapped[list["EvidenciaRisco"]] = relationship(
        back_populates="avaliacao", cascade="all, delete-orphan", order_by="EvidenciaRisco.id"
    )
```

`backend/app/models/evidencia_risco.py`:
```python
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Dimensao
from app.models._tipos import coluna_enum

if TYPE_CHECKING:
    from app.models.avaliacao_risco import AvaliacaoRisco
    from app.models.configuracao_sinal import ConfiguracaoSinal


class EvidenciaRisco(Base):
    """O porquê de cada alerta: um sinal disparado para uma avaliação."""

    __tablename__ = "evidencias_risco"

    id: Mapped[int] = mapped_column(primary_key=True)
    avaliacao_id: Mapped[int] = mapped_column(ForeignKey("avaliacoes_risco.id"), index=True)
    configuracao_sinal_id: Mapped[int] = mapped_column(ForeignKey("configuracoes_sinal.id"))
    dimensao: Mapped[Dimensao] = mapped_column(coluna_enum(Dimensao))
    valor_observado: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    linha_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    variacao_pct: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    meses_persistencia: Mapped[int]
    contribuicao: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    texto: Mapped[str] = mapped_column(Unicode(300))

    avaliacao: Mapped["AvaliacaoRisco"] = relationship(back_populates="evidencias")
    sinal: Mapped["ConfiguracaoSinal"] = relationship()
```

`backend/app/models/__init__.py`:
```python
from app.models.acao_recomendada import AcaoRecomendada
from app.models.atendimento_mensal import AtendimentoMensal
from app.models.avaliacao_risco import AvaliacaoRisco
from app.models.cliente import Cliente
from app.models.configuracao_sinal import ConfiguracaoSinal
from app.models.evidencia_risco import EvidenciaRisco
from app.models.execucao_analise import ExecucaoAnalise
from app.models.pesquisa_nps import PesquisaNps
from app.models.situacao_cliente import Situacao
from app.models.usuario import Usuario

__all__ = [
    "AcaoRecomendada",
    "AtendimentoMensal",
    "AvaliacaoRisco",
    "Cliente",
    "ConfiguracaoSinal",
    "EvidenciaRisco",
    "ExecucaoAnalise",
    "PesquisaNps",
    "Situacao",
    "Usuario",
]
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam (4 novos + 2 da Task 1). Um `SAWarning` sobre Decimal no SQLite é esperado e inofensivo.

Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 6: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): enums de domínio e models SQLAlchemy do MVP" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Segurança (hash, JWT) e exceções de domínio

**Files:**
- Create: `backend/app/core/exceptions.py`, `backend/app/core/handlers.py`, `backend/app/core/security.py`
- Modify: `backend/app/main.py` (registrar handlers)
- Test: `backend/tests/unit/test_security.py`, `backend/tests/integration/test_handlers.py`

**Interfaces:**
- Produces: `ErroDominio(mensagem: str | None = None)` com `.status_code` e `.mensagem`; subclasses `UsuarioJaExisteError` (409), `CredenciaisInvalidasError` (401), `UsuarioInativoError` (403), `TokenInvalidoError` (401), `RecursoNaoEncontradoError` (404), `ImportacaoInvalidaError` (422), `ParametroInvalidoError` (422). `registrar_handlers(app)`. `HasherSenha().gerar_hash(senha) -> str`, `.verificar(senha, senha_hash) -> bool`, `.verificar_ficticio(senha) -> bool` (sempre False, gasta o mesmo tempo). `GerenciadorToken(segredo, expira_minutos).criar(usuario_id, usuario) -> tuple[str, datetime]` (datetime aware UTC) e `.decodificar(token) -> dict` (lança `TokenInvalidoError`).

- [ ] **Step 1: Escrever os testes que falham**

`backend/tests/unit/test_security.py`:
```python
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.exceptions import TokenInvalidoError
from app.core.security import GerenciadorToken, HasherSenha

SEGREDO = "segredo-de-teste-com-mais-de-32-bytes-ok"


def test_hash_nao_e_a_senha_e_verifica():
    hasher = HasherSenha()
    senha_hash = hasher.gerar_hash("SenhaForte123")

    assert senha_hash != "SenhaForte123"
    assert senha_hash.startswith("$argon2")
    assert hasher.verificar("SenhaForte123", senha_hash)
    assert not hasher.verificar("outra123", senha_hash)


def test_verificar_com_hash_corrompido_retorna_false():
    assert HasherSenha().verificar("SenhaForte123", "isto-nao-e-um-hash") is False


def test_verificar_ficticio_sempre_falso():
    assert HasherSenha().verificar_ficticio("qualquer1") is False


def test_token_ida_e_volta():
    tokens = GerenciadorToken(SEGREDO, expira_minutos=60)
    token, expira_em = tokens.criar(7, "maria.silva")

    payload = tokens.decodificar(token)
    assert payload["sub"] == "7"
    assert payload["usuario"] == "maria.silva"
    assert "iat" in payload
    assert expira_em.tzinfo is not None
    assert timedelta(minutes=59) < expira_em - datetime.now(UTC) <= timedelta(minutes=60)


def test_token_expirado_e_invalido():
    tokens = GerenciadorToken(SEGREDO, expira_minutos=-1)
    token, _ = tokens.criar(1, "maria")

    with pytest.raises(TokenInvalidoError):
        tokens.decodificar(token)


def test_token_com_outro_segredo_e_invalido():
    token, _ = GerenciadorToken("outro-segredo-com-mais-de-32-bytes-xx", 60).criar(1, "maria")

    with pytest.raises(TokenInvalidoError):
        GerenciadorToken(SEGREDO, 60).decodificar(token)


def test_token_sem_sub_e_invalido():
    token = jwt.encode({"exp": datetime.now(UTC) + timedelta(minutes=5)}, SEGREDO, "HS256")

    with pytest.raises(TokenInvalidoError):
        GerenciadorToken(SEGREDO, 60).decodificar(token)
```

`backend/tests/integration/test_handlers.py`:
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    CredenciaisInvalidasError,
    RecursoNaoEncontradoError,
    UsuarioJaExisteError,
)
from app.core.handlers import registrar_handlers


def _app_que_lanca(erro: Exception) -> TestClient:
    app = FastAPI()
    registrar_handlers(app)

    @app.get("/x")
    def lanca():
        raise erro

    return TestClient(app)


def test_erro_de_dominio_vira_status_e_detail():
    resposta = _app_que_lanca(UsuarioJaExisteError()).get("/x")

    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Usuário já cadastrado"}


def test_401_inclui_www_authenticate():
    resposta = _app_que_lanca(CredenciaisInvalidasError()).get("/x")

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Usuário ou senha inválidos"}
    assert resposta.headers["www-authenticate"] == "Bearer"


def test_mensagem_customizada():
    resposta = _app_que_lanca(RecursoNaoEncontradoError("Cliente C999 não encontrado")).get("/x")

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Cliente C999 não encontrado"}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/unit/test_security.py tests/integration/test_handlers.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'app.core.exceptions'`.

- [ ] **Step 3: Implementar**

`backend/app/core/exceptions.py`:
```python
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
```

`backend/app/core/handlers.py`:
```python
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
```

`backend/app/core/security.py`:
```python
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
```

Em `backend/app/main.py`, importe `from app.core.handlers import registrar_handlers` e chame `registrar_handlers(app)` logo após `app.add_middleware(...)`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam.
Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 5: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): hash argon2, JWT e exceções de domínio com handlers HTTP" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Autenticação (cadastro, login, /me, proteção de rotas)

**Files:**
- Create: `backend/app/schemas/usuario.py`, `backend/app/schemas/auth.py`
- Create: `backend/app/repositories/usuario_repository.py`
- Create: `backend/app/services/usuario_service.py`, `backend/app/services/auth_service.py`
- Create: `backend/app/controllers/auth_controller.py`
- Modify: `backend/app/dependencies.py`, `backend/app/main.py`, `backend/tests/conftest.py`
- Test: `backend/tests/unit/test_schemas_auth.py`, `backend/tests/integration/test_auth.py`

**Interfaces:**
- Consumes: `Usuario` (Task 2), `HasherSenha`, `GerenciadorToken`, exceções (Task 3), `get_db`, `get_settings_dep` (Task 1).
- Produces: schemas `CadastroRequest`, `LoginRequest`, `TokenResponse(access_token, token_type, expira_em, usuario: UsuarioResumo)`, `UsuarioResponse(id, nome_completo, usuario, criado_em)`, `UsuarioResumo(id, nome_completo, usuario)`; `UsuarioRepository(session)` com `obter_por_id`, `obter_por_usuario`, `adicionar`, `salvar`; `UsuarioService(repo, hasher).cadastrar(dados) -> Usuario`, `.obter_por_id(id) -> Usuario`; `AuthService(repo, hasher, tokens).autenticar(dados) -> TokenResponse`, `.usuario_do_token(token) -> Usuario`; dependência **`get_usuario_atual`** (usada por todas as rotas protegidas nas tasks seguintes); fixture pytest **`auth_headers`** (dict com `Authorization: Bearer ...`).

- [ ] **Step 1: Escrever os testes que falham**

`backend/tests/unit/test_schemas_auth.py`:
```python
import pytest
from pydantic import ValidationError

from app.schemas.auth import CadastroRequest, LoginRequest


def test_cadastro_normaliza_usuario_e_nome():
    dados = CadastroRequest(
        nome_completo="  Maria da Silva  ", usuario="  Maria.Silva ", senha="SenhaForte123"
    )

    assert dados.nome_completo == "Maria da Silva"
    assert dados.usuario == "maria.silva"


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("nome_completo", "Ma"),
        ("usuario", "ma"),
        ("usuario", "maria silva"),
        ("usuario", "maria@silva"),
        ("senha", "curta1"),
        ("senha", "somenteletras"),
        ("senha", "12345678"),
        ("senha", "a1" * 65),
    ],
)
def test_cadastro_rejeita_valores_invalidos(campo, valor):
    dados = {"nome_completo": "Maria da Silva", "usuario": "maria.silva", "senha": "SenhaForte123"}
    dados[campo] = valor

    with pytest.raises(ValidationError):
        CadastroRequest(**dados)


def test_login_normaliza_usuario():
    assert LoginRequest(usuario=" MARIA.Silva ", senha="x").usuario == "maria.silva"
```

`backend/tests/integration/test_auth.py`:
```python
from app.models import Usuario

CADASTRO = {"nome_completo": "Maria da Silva", "usuario": "maria.silva", "senha": "SenhaForte123"}


def _cadastrar(client, **extra):
    return client.post("/api/auth/cadastro", json={**CADASTRO, **extra})


def test_cadastro_sucesso_nao_expoe_hash(client):
    resposta = _cadastrar(client, usuario="Maria.Silva")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert set(corpo) == {"id", "nome_completo", "usuario", "criado_em"}
    assert corpo["usuario"] == "maria.silva"


def test_cadastro_duplicado_ignora_maiusculas(client):
    _cadastrar(client)
    resposta = _cadastrar(client, usuario="MARIA.SILVA")

    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Usuário já cadastrado"}


def test_cadastro_invalido_retorna_422(client):
    assert _cadastrar(client, senha="semnumero").status_code == 422


def test_login_sucesso_e_me(client):
    _cadastrar(client)
    resposta = client.post(
        "/api/auth/login", json={"usuario": "  Maria.Silva ", "senha": "SenhaForte123"}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["usuario"] == {"id": 1, "nome_completo": "Maria da Silva", "usuario": "maria.silva"}
    assert corpo["expira_em"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {corpo['access_token']}"})
    assert me.status_code == 200
    assert me.json()["usuario"] == "maria.silva"
    assert "senha_hash" not in me.json()


def test_login_atualiza_ultimo_login(client, db_session):
    _cadastrar(client)
    client.post("/api/auth/login", json={"usuario": "maria.silva", "senha": "SenhaForte123"})

    assert db_session.query(Usuario).one().ultimo_login_em is not None


def test_senha_errada_e_usuario_inexistente_tem_mesma_resposta(client):
    _cadastrar(client)
    errada = client.post("/api/auth/login", json={"usuario": "maria.silva", "senha": "Errada123"})
    inexistente = client.post("/api/auth/login", json={"usuario": "joao", "senha": "Errada123"})

    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json() == {"detail": "Usuário ou senha inválidos"}


def test_usuario_inativo_recebe_403(client, db_session):
    _cadastrar(client)
    usuario = db_session.query(Usuario).one()
    usuario.ativo = False
    db_session.commit()

    resposta = client.post(
        "/api/auth/login", json={"usuario": "maria.silva", "senha": "SenhaForte123"}
    )
    assert resposta.status_code == 403


def test_me_sem_token_ou_token_invalido_retorna_401(client):
    assert client.get("/api/auth/me").status_code == 401
    invalido = client.get("/api/auth/me", headers={"Authorization": "Bearer lixo"})
    assert invalido.status_code == 401
    assert invalido.json() == {"detail": "Token inválido ou expirado"}


def test_fixture_auth_headers_autentica(client, auth_headers):
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 200
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/unit/test_schemas_auth.py tests/integration/test_auth.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'app.schemas.auth'`.

- [ ] **Step 3: Implementar schemas**

`backend/app/schemas/usuario.py`:
```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UsuarioResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_completo: str
    usuario: str


class UsuarioResponse(UsuarioResumo):
    criado_em: datetime
```

`backend/app/schemas/auth.py`:
```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.usuario import UsuarioResumo

REGEX_USUARIO = r"^[a-zA-Z0-9._-]+$"


def _normalizar_usuario(valor: object) -> object:
    return valor.strip().lower() if isinstance(valor, str) else valor


class CadastroRequest(BaseModel):
    nome_completo: str = Field(min_length=3, max_length=150, examples=["Maria da Silva"])
    usuario: str = Field(
        min_length=3, max_length=50, pattern=REGEX_USUARIO, examples=["maria.silva"]
    )
    senha: str = Field(min_length=8, max_length=128, examples=["SenhaForte123"])

    @field_validator("nome_completo", mode="before")
    @classmethod
    def _strip_nome(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("usuario", mode="before")
    @classmethod
    def _normalizar(cls, valor: object) -> object:
        return _normalizar_usuario(valor)

    @field_validator("senha")
    @classmethod
    def _senha_forte(cls, valor: str) -> str:
        if not any(c.isalpha() for c in valor) or not any(c.isdigit() for c in valor):
            raise ValueError("A senha deve conter ao menos uma letra e um número")
        return valor


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=1, max_length=50, examples=["maria.silva"])
    senha: str = Field(min_length=1, max_length=128, examples=["SenhaForte123"])

    @field_validator("usuario", mode="before")
    @classmethod
    def _normalizar(cls, valor: object) -> object:
        return _normalizar_usuario(valor)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expira_em: datetime
    usuario: UsuarioResumo
```

- [ ] **Step 4: Implementar repository e services**

`backend/app/repositories/usuario_repository.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Usuario


class UsuarioRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def obter_por_id(self, usuario_id: int) -> Usuario | None:
        return self._session.get(Usuario, usuario_id)

    def obter_por_usuario(self, usuario: str) -> Usuario | None:
        return self._session.scalar(select(Usuario).where(Usuario.usuario == usuario))

    def adicionar(self, usuario: Usuario) -> Usuario:
        self._session.add(usuario)
        self._session.commit()
        self._session.refresh(usuario)
        return usuario

    def salvar(self, usuario: Usuario) -> Usuario:
        self._session.commit()
        return usuario
```

`backend/app/services/usuario_service.py`:
```python
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
```

`backend/app/services/auth_service.py`:
```python
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
```

- [ ] **Step 5: Implementar dependências, controller e registrar router**

Acrescente em `backend/app/dependencies.py` (mantendo o que já existe; ajuste os imports no topo):
```python
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import TokenInvalidoError
from app.core.security import GerenciadorToken, HasherSenha
from app.models import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.services.auth_service import AuthService
from app.services.usuario_service import UsuarioService

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
```

Observação: com `HTTPBearer(auto_error=False)`, requisição sem header chega como `None` e cai no `TokenInvalidoError("Não autenticado")` → 401.

`backend/app/controllers/auth_controller.py`:
```python
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
```

Em `backend/app/main.py`: `from app.controllers import auth_controller, health_controller` e `app.include_router(auth_controller.router, prefix="/api")`.

Acrescente ao `backend/tests/conftest.py`:
```python
@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/auth/cadastro",
        json={"nome_completo": "Usuária Teste", "usuario": "teste", "senha": "SenhaForte123"},
    )
    resposta = client.post("/api/auth/login", json={"usuario": "teste", "senha": "SenhaForte123"})
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}
```

- [ ] **Step 6: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam.
Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 7: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): cadastro, login JWT, /auth/me e proteção de rotas" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Catálogo seed e importação do xlsx

**Files:**
- Create: `backend/app/services/catalogo_seed.py`, `backend/app/services/catalogo_service.py`
- Create: `backend/app/repositories/sinal_repository.py`, `backend/app/repositories/acao_repository.py`, `backend/app/repositories/origem_repository.py`
- Create: `backend/app/services/importacao_service.py`, `backend/app/services/fabrica.py`
- Create: `backend/app/schemas/importacao.py`, `backend/app/controllers/importacao_controller.py`
- Create: `backend/scripts/__init__.py` (vazio), `backend/scripts/importar_base.py`
- Modify: `backend/app/dependencies.py`, `backend/app/main.py`, `backend/tests/conftest.py`
- Test: `backend/tests/integration/test_importacao.py`, `backend/tests/integration/test_importacao_api.py`, `backend/tests/integration/test_scripts.py`

**Interfaces:**
- Consumes: models e enums (Task 2), `ImportacaoInvalidaError` (Task 3), `get_usuario_atual` e fixture `auth_headers` (Task 4).
- Produces: `SINAIS_SEED`, `ACOES_SEED`, `PESO_INICIAL`; `SinalRepository(session)` com `listar()`, `listar_ativos()`, `listar_codigos() -> set[str]`, `adicionar_todos(list)`; `AcaoRepository(session)` com `listar()`, `listar_codigos()`, `adicionar_todos(list)`, `mapa_por_codigo() -> dict[str, AcaoRecomendada]`; `OrigemRepository(session).substituir_tudo(clientes, situacoes, atendimentos, pesquisas) -> None`; `CatalogoService(sinais, acoes, persistencia_padrao).garantir_seeds()`, `.listar_sinais()`, `.listar_acoes()`; `RelatorioImportacao(contagens: dict[str, int], avisos: list[str])`; `ImportacaoService(repo, catalogo).importar(origem: str | Path | bytes) -> RelatorioImportacao`; `fabrica.criar_catalogo_service(session, settings)`, `fabrica.criar_importacao_service(session, settings)`; dependências `get_catalogo_service`, `get_importacao_service`; `POST /api/importacao`; `scripts.importar_base.main(argv) -> int`; fixture pytest **`caminho_xlsx`** (Path do xlsx real na raiz do repo).

- [ ] **Step 1: Escrever os testes que falham**

Acrescente ao `backend/tests/conftest.py` (e `from pathlib import Path` no topo):
```python
@pytest.fixture
def caminho_xlsx() -> Path:
    return Path(__file__).resolve().parents[2] / "INOVAAPPS_base_de_dados.xlsx"
```

`backend/tests/integration/test_importacao.py`:
```python
import io
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import func, select

from app.core.enums import ClassificacaoNPS, Plano, Porte, SituacaoCliente
from app.core.exceptions import ImportacaoInvalidaError
from app.models import (
    AcaoRecomendada,
    AtendimentoMensal,
    Cliente,
    ConfiguracaoSinal,
    PesquisaNps,
    Situacao,
)
from app.services.fabrica import criar_importacao_service


def _contar(sessao, modelo) -> int:
    return sessao.scalar(select(func.count()).select_from(modelo))


def _xlsx(abas: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        for nome, df in abas.items():
            df.to_excel(escritor, sheet_name=nome, index=False)
    return buffer.getvalue()


def _abas_reais(caminho_xlsx) -> dict[str, pd.DataFrame]:
    abas = pd.read_excel(caminho_xlsx, sheet_name=None)
    return {nome: abas[nome] for nome in ("clientes", "atendimento_mensal", "pesquisas_nps", "situacao_clientes")}


@pytest.fixture
def service(db_session, settings):
    return criar_importacao_service(db_session, settings)


def test_importa_base_real_com_contagens_esperadas(service, db_session, caminho_xlsx):
    relatorio = service.importar(caminho_xlsx)

    assert relatorio.contagens == {
        "clientes": 80,
        "situacao_clientes": 80,
        "atendimentos_mensais": 1295,
        "pesquisas_nps": 422,
    }
    assert relatorio.avisos == []
    assert _contar(db_session, Cliente) == 80
    assert _contar(db_session, AtendimentoMensal) == 1295
    cancelados = db_session.scalar(
        select(func.count()).where(Situacao.situacao == SituacaoCliente.CANCELADO)
    )
    assert cancelados == 22


def test_reimportar_nao_duplica(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    service.importar(caminho_xlsx.read_bytes())

    assert _contar(db_session, Cliente) == 80
    assert _contar(db_session, AtendimentoMensal) == 1295
    assert _contar(db_session, PesquisaNps) == 422


def test_preserva_nulos_e_normaliza_enums_e_meses(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)

    sla_nulos = db_session.scalar(
        select(func.count()).where(AtendimentoMensal.pct_sla_cumprido.is_(None))
    )
    assert sla_nulos == 23
    c002 = db_session.get(Cliente, "C002")
    assert (c002.porte, c002.plano) == (Porte.MEDIO, Plano.AVANCADO)
    assert c002.inicio_contrato == date(2020, 2, 1)
    sem_resposta = db_session.scalars(
        select(PesquisaNps).where(PesquisaNps.classificacao_nps == ClassificacaoNPS.SEM_RESPOSTA)
    ).all()
    assert len(sem_resposta) == 84
    assert all(p.nota_nps is None and p.respondeu is False for p in sem_resposta)
    meses = db_session.scalars(select(AtendimentoMensal.mes_ref).distinct()).all()
    assert all(m.day == 1 for m in meses)
    assert max(meses) == date(2026, 6, 1)
    cancelado = db_session.scalar(
        select(Situacao).where(Situacao.situacao == SituacaoCliente.CANCELADO).limit(1)
    )
    assert cancelado.mes_cancelamento is not None and cancelado.mes_cancelamento.day == 1


def test_importacao_cria_catalogo_seed_uma_vez(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    service.importar(caminho_xlsx)

    assert _contar(db_session, ConfiguracaoSinal) == 10
    assert _contar(db_session, AcaoRecomendada) == 6
    reclamacoes = db_session.scalar(
        select(ConfiguracaoSinal).where(ConfiguracaoSinal.codigo == "RECLAMACOES")
    )
    assert reclamacoes.metrica == "soma_3m"
    assert float(reclamacoes.peso) == pytest.approx(0.10)
    assert reclamacoes.persistencia_min_meses == 2


def test_arquivo_invalido_nao_apaga_dados(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)

    with pytest.raises(ImportacaoInvalidaError, match="xlsx"):
        service.importar(b"isto nao e um xlsx")

    assert _contar(db_session, Cliente) == 80


def test_coluna_faltando_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    abas["clientes"] = abas["clientes"].drop(columns=["plano"])

    with pytest.raises(ImportacaoInvalidaError, match="plano"):
        service.importar(_xlsx(abas))


def test_aba_faltando_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    del abas["pesquisas_nps"]

    with pytest.raises(ImportacaoInvalidaError, match="pesquisas_nps"):
        service.importar(_xlsx(abas))


def test_enum_invalido_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    abas["clientes"].loc[0, "porte"] = "Gigante"

    with pytest.raises(ImportacaoInvalidaError, match="Gigante"):
        service.importar(_xlsx(abas))


def test_linha_duplicada_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    abas["atendimento_mensal"] = pd.concat(
        [abas["atendimento_mensal"], abas["atendimento_mensal"].head(1)]
    )

    with pytest.raises(ImportacaoInvalidaError, match="duplicad"):
        service.importar(_xlsx(abas))


def test_contagens_diferentes_geram_avisos(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    primeiros = set(abas["clientes"]["cliente_id"].head(10))
    abas = {nome: df[df["cliente_id"].isin(primeiros)] for nome, df in abas.items()}

    relatorio = service.importar(_xlsx(abas))

    assert relatorio.contagens["clientes"] == 10
    assert any("clientes" in aviso for aviso in relatorio.avisos)
```

`backend/tests/integration/test_importacao_api.py`:
```python
def test_importacao_exige_autenticacao(client, caminho_xlsx):
    resposta = client.post(
        "/api/importacao", files={"arquivo": ("base.xlsx", caminho_xlsx.read_bytes())}
    )
    assert resposta.status_code == 401


def test_importacao_via_upload(client, auth_headers, caminho_xlsx):
    resposta = client.post(
        "/api/importacao",
        headers=auth_headers,
        files={"arquivo": ("base.xlsx", caminho_xlsx.read_bytes())},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["contagens"]["clientes"] == 80
    assert corpo["avisos"] == []


def test_importacao_de_arquivo_invalido_retorna_422(client, auth_headers):
    resposta = client.post(
        "/api/importacao", headers=auth_headers, files={"arquivo": ("x.xlsx", b"lixo")}
    )

    assert resposta.status_code == 422
    assert "xlsx" in resposta.json()["detail"]
```

`backend/tests/integration/test_scripts.py`:
```python
import pytest
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from scripts import importar_base


@pytest.fixture
def banco_arquivo(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'script.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    yield url
    get_settings.cache_clear()


def test_script_importar_base(banco_arquivo, caminho_xlsx, capsys):
    assert importar_base.main([str(caminho_xlsx)]) == 0

    engine = create_engine(banco_arquivo)
    with engine.connect() as conexao:
        assert conexao.execute(text("SELECT COUNT(*) FROM clientes")).scalar() == 80
    engine.dispose()
    assert "clientes: 80" in capsys.readouterr().out
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/integration/test_importacao.py tests/integration/test_importacao_api.py tests/integration/test_scripts.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'app.services.fabrica'`.

- [ ] **Step 3: Implementar catálogo seed, repositories e CatalogoService**

`backend/app/services/catalogo_seed.py`:
```python
"""Catálogo inicial (seed) de sinais de risco e do playbook de ações.

Os limiares vêm do planejamento (§6.2). Enquanto não há calibração, todos os
sinais têm o mesmo peso (0,10 — soma 1). `metrica` diz qual indicador a regra
NIVEL compara (média ou soma dos últimos 3 meses).
"""

from app.core.enums import Dimensao, Responsavel, SentidoPiora, TipoRegra

PESO_INICIAL = 0.10

SINAIS_SEED: list[dict] = [
    {
        "codigo": "REABERTOS_TENDENCIA",
        "dimensao": Dimensao.ATENDIMENTO,
        "variavel": "chamados_reabertos",
        "tipo_regra": TipoRegra.TENDENCIA,
        "sentido_piora": SentidoPiora.AUMENTO,
        "limiar": 0.50,
        "metrica": "media_3m",
        "template_evidencia": "Chamados reabertos subiram {variacao_pct:.0%} nos últimos 3 meses em relação à média anterior",
    },
    {
        "codigo": "CRITICOS_TENDENCIA",
        "dimensao": Dimensao.ATENDIMENTO,
        "variavel": "chamados_criticos",
        "tipo_regra": TipoRegra.TENDENCIA,
        "sentido_piora": SentidoPiora.AUMENTO,
        "limiar": 0.50,
        "metrica": "media_3m",
        "template_evidencia": "Chamados críticos subiram {variacao_pct:.0%} nos últimos 3 meses em relação à média anterior",
    },
    {
        "codigo": "RESOLUCAO_LENTA",
        "dimensao": Dimensao.SLA,
        "variavel": "tempo_resolucao_vs_sla",
        "tipo_regra": TipoRegra.TENDENCIA,
        "sentido_piora": SentidoPiora.AUMENTO,
        "limiar": 0.25,
        "metrica": "media_3m",
        "template_evidencia": "Tempo de resolução em relação ao SLA piorou {variacao_pct:.0%} nos últimos 3 meses",
    },
    {
        "codigo": "SLA_BAIXO",
        "dimensao": Dimensao.SLA,
        "variavel": "pct_sla_cumprido",
        "tipo_regra": TipoRegra.NIVEL,
        "sentido_piora": SentidoPiora.QUEDA,
        "limiar": 65,
        "metrica": "media_3m",
        "template_evidencia": "SLA cumprido em {media_3m:.0f}% na média dos últimos 3 meses (limite: 65%)",
    },
    {
        "codigo": "USO_EM_QUEDA",
        "dimensao": Dimensao.ENGAJAMENTO,
        "variavel": "uso_plataforma_pct",
        "tipo_regra": TipoRegra.TENDENCIA,
        "sentido_piora": SentidoPiora.QUEDA,
        "limiar": 0.15,
        "metrica": "media_3m",
        "template_evidencia": "Uso da plataforma caiu {queda_pct:.0%} em relação à média anterior",
    },
    {
        "codigo": "REUNIOES_CANCELADAS",
        "dimensao": Dimensao.ENGAJAMENTO,
        "variavel": "pct_reunioes_realizadas",
        "tipo_regra": TipoRegra.NIVEL,
        "sentido_piora": SentidoPiora.QUEDA,
        "limiar": 0.5,
        "metrica": "media_3m",
        "template_evidencia": "Apenas {media_3m:.0%} das reuniões previstas aconteceram nos últimos 3 meses",
    },
    {
        "codigo": "ATRASO_PAGAMENTO",
        "dimensao": Dimensao.FINANCEIRO,
        "variavel": "dias_atraso_pagamento",
        "tipo_regra": TipoRegra.NIVEL,
        "sentido_piora": SentidoPiora.AUMENTO,
        "limiar": 6,
        "metrica": "media_3m",
        "template_evidencia": "Atraso médio de pagamento de {media_3m:.1f} dias nos últimos 3 meses",
    },
    {
        "codigo": "RECLAMACOES",
        "dimensao": Dimensao.SATISFACAO,
        "variavel": "reclamacoes_formais",
        "tipo_regra": TipoRegra.NIVEL,
        "sentido_piora": SentidoPiora.AUMENTO,
        "limiar": 2,
        "metrica": "soma_3m",
        "template_evidencia": "{soma_3m:.0f} reclamações formais nos últimos 3 meses",
    },
    {
        "codigo": "NPS_EM_QUEDA",
        "dimensao": Dimensao.SATISFACAO,
        "variavel": "nps_variacao",
        "tipo_regra": TipoRegra.EVENTO,
        "sentido_piora": SentidoPiora.QUEDA,
        "limiar": 2,
        "metrica": "media_3m",
        "template_evidencia": "Nota de NPS caiu {queda_abs:.0f} pontos na última pesquisa respondida",
    },
    {
        "codigo": "NPS_SILENCIO",
        "dimensao": Dimensao.SATISFACAO,
        "variavel": "nps_sem_resposta_consecutivas",
        "tipo_regra": TipoRegra.EVENTO,
        "sentido_piora": SentidoPiora.AUMENTO,
        "limiar": 1,
        "metrica": "media_3m",
        "template_evidencia": "Não respondeu às {valor_mes:.0f} últimas pesquisas de NPS",
    },
]

ACOES_SEED: list[dict] = [
    {
        "codigo": "COMITE_RETENCAO",
        "titulo": "Ação coordenada de retenção",
        "descricao": "O risco afeta várias dimensões ao mesmo tempo: montar um comitê com CS, técnico e executivo e definir um plano único para o cliente.",
        "dimensao_gatilho": None,
        "responsavel_sugerido": Responsavel.EXECUTIVO,
        "prazo_dias": 7,
        "ordem": 1,
    },
    {
        "codigo": "CONTATO_EXECUTIVO",
        "titulo": "Contato executivo",
        "descricao": "O cliente sumiu das reuniões e parou de responder ao NPS: um executivo deve procurar o patrocinador do contrato.",
        "dimensao_gatilho": Dimensao.ENGAJAMENTO,
        "responsavel_sugerido": Responsavel.EXECUTIVO,
        "prazo_dias": 7,
        "ordem": 2,
    },
    {
        "codigo": "REVISAO_TECNICA",
        "titulo": "Revisão técnica dos chamados",
        "descricao": "Revisar chamados reabertos, críticos e fora do SLA, escalar internamente e apresentar um plano de correção.",
        "dimensao_gatilho": Dimensao.ATENDIMENTO,
        "responsavel_sugerido": Responsavel.TECNICO,
        "prazo_dias": 15,
        "ordem": 3,
    },
    {
        "codigo": "REUNIAO_VALOR",
        "titulo": "Reunião de valor e reonboarding",
        "descricao": "Agendar uma reunião para mostrar o valor entregue e reengajar o uso da plataforma.",
        "dimensao_gatilho": Dimensao.ENGAJAMENTO,
        "responsavel_sugerido": Responsavel.CS,
        "prazo_dias": 15,
        "ordem": 4,
    },
    {
        "codigo": "CONVERSA_FINANCEIRA",
        "titulo": "Conversa financeira",
        "descricao": "Entender o motivo dos atrasos de pagamento e negociar condições.",
        "dimensao_gatilho": Dimensao.FINANCEIRO,
        "responsavel_sugerido": Responsavel.FINANCEIRO,
        "prazo_dias": 15,
        "ordem": 5,
    },
    {
        "codigo": "PLANO_DE_RECUPERACAO",
        "titulo": "Plano de recuperação da satisfação",
        "descricao": "Tratar as reclamações e a queda de NPS com um plano de ação acompanhado pelo CS.",
        "dimensao_gatilho": Dimensao.SATISFACAO,
        "responsavel_sugerido": Responsavel.CS,
        "prazo_dias": 15,
        "ordem": 6,
    },
]
```
(Se o `ruff` reclamar de linha longa nos templates/descrições, acrescente `# noqa: E501` ao fim dessas linhas ou `per-file-ignores = {"app/services/catalogo_seed.py" = ["E501"]}` em `[tool.ruff.lint]`; prefira o per-file-ignores.)

`backend/app/repositories/sinal_repository.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConfiguracaoSinal


class SinalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar(self) -> list[ConfiguracaoSinal]:
        return list(self._session.scalars(select(ConfiguracaoSinal).order_by(ConfiguracaoSinal.id)))

    def listar_ativos(self) -> list[ConfiguracaoSinal]:
        consulta = (
            select(ConfiguracaoSinal)
            .where(ConfiguracaoSinal.ativo.is_(True))
            .order_by(ConfiguracaoSinal.id)
        )
        return list(self._session.scalars(consulta))

    def listar_codigos(self) -> set[str]:
        return set(self._session.scalars(select(ConfiguracaoSinal.codigo)))

    def adicionar_todos(self, sinais: list[ConfiguracaoSinal]) -> None:
        if sinais:
            self._session.add_all(sinais)
            self._session.commit()
```

`backend/app/repositories/acao_repository.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AcaoRecomendada


class AcaoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar(self) -> list[AcaoRecomendada]:
        return list(self._session.scalars(select(AcaoRecomendada).order_by(AcaoRecomendada.ordem)))

    def listar_codigos(self) -> set[str]:
        return set(self._session.scalars(select(AcaoRecomendada.codigo)))

    def mapa_por_codigo(self) -> dict[str, AcaoRecomendada]:
        return {acao.codigo: acao for acao in self.listar()}

    def adicionar_todos(self, acoes: list[AcaoRecomendada]) -> None:
        if acoes:
            self._session.add_all(acoes)
            self._session.commit()
```

`backend/app/repositories/origem_repository.py`:
```python
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import (
    AtendimentoMensal,
    AvaliacaoRisco,
    Cliente,
    EvidenciaRisco,
    ExecucaoAnalise,
    PesquisaNps,
    Situacao,
)


class OrigemRepository:
    """Grava os dados de origem (planilha). Substitui tudo em uma única transação."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def substituir_tudo(
        self,
        clientes: list[Cliente],
        situacoes: list[Situacao],
        atendimentos: list[AtendimentoMensal],
        pesquisas: list[PesquisaNps],
    ) -> None:
        try:
            for modelo in (
                EvidenciaRisco,
                AvaliacaoRisco,
                ExecucaoAnalise,
                AtendimentoMensal,
                PesquisaNps,
                Situacao,
                Cliente,
            ):
                self._session.execute(delete(modelo))
            self._session.add_all(clientes)
            self._session.flush()
            self._session.add_all([*situacoes, *atendimentos, *pesquisas])
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        finally:
            self._session.expunge_all()
```
(`expunge_all` evita que objetos antigos fiquem presos na sessão entre reimportações.)

`backend/app/services/catalogo_service.py`:
```python
from decimal import Decimal

from app.models import AcaoRecomendada, ConfiguracaoSinal
from app.repositories.acao_repository import AcaoRepository
from app.repositories.sinal_repository import SinalRepository
from app.services.catalogo_seed import ACOES_SEED, PESO_INICIAL, SINAIS_SEED


class CatalogoService:
    """Catálogo de sinais e playbook de ações. Garante o seed sem duplicar."""

    def __init__(
        self, sinais: SinalRepository, acoes: AcaoRepository, persistencia_padrao: int
    ) -> None:
        self._sinais = sinais
        self._acoes = acoes
        self._persistencia_padrao = persistencia_padrao

    def garantir_seeds(self) -> None:
        existentes = self._sinais.listar_codigos()
        self._sinais.adicionar_todos(
            [
                ConfiguracaoSinal(
                    **{**seed, "limiar": Decimal(str(seed["limiar"]))},
                    peso=Decimal(str(PESO_INICIAL)),
                    persistencia_min_meses=self._persistencia_padrao,
                    ativo=True,
                )
                for seed in SINAIS_SEED
                if seed["codigo"] not in existentes
            ]
        )
        acoes_existentes = self._acoes.listar_codigos()
        self._acoes.adicionar_todos(
            [AcaoRecomendada(**seed) for seed in ACOES_SEED if seed["codigo"] not in acoes_existentes]
        )

    def listar_sinais(self) -> list[ConfiguracaoSinal]:
        return self._sinais.listar()

    def listar_acoes(self) -> list[AcaoRecomendada]:
        return self._acoes.listar()
```

- [ ] **Step 4: Implementar ImportacaoService e fábrica**

`backend/app/services/importacao_service.py`:
```python
"""Importação da planilha INOVAAPPS para as tabelas de origem.

Regras: valida abas/colunas/enums antes de gravar (arquivo ruim não apaga nada),
converte meses 'AAAA-MM' para date(ano, mes, 1), mantém nulos que são informação
(pct_sla_cumprido sem chamado, NPS sem resposta) e é idempotente (substitui tudo).
"""

import io
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.enums import ClassificacaoNPS, Plano, Porte, SituacaoCliente
from app.core.exceptions import ImportacaoInvalidaError
from app.models import AtendimentoMensal, Cliente, PesquisaNps, Situacao
from app.repositories.origem_repository import OrigemRepository
from app.services.catalogo_service import CatalogoService

ABAS_COLUNAS: dict[str, list[str]] = {
    "clientes": [
        "cliente_id",
        "segmento",
        "porte",
        "plano",
        "valor_mensal",
        "sla_contratado_h",
        "inicio_contrato",
    ],
    "atendimento_mensal": [
        "cliente_id",
        "mes_ref",
        "chamados_abertos",
        "chamados_criticos",
        "chamados_reabertos",
        "chamados_dentro_sla",
        "pct_sla_cumprido",
        "tempo_medio_resolucao_h",
        "reclamacoes_formais",
        "uso_plataforma_pct",
        "dias_atraso_pagamento",
        "reunioes_previstas",
        "reunioes_realizadas",
    ],
    "pesquisas_nps": ["cliente_id", "mes_ref", "respondeu", "nota_nps", "classificacao_nps"],
    "situacao_clientes": ["cliente_id", "situacao", "mes_cancelamento"],
}

CONTAGENS_ESPERADAS = {
    "clientes": 80,
    "situacao_clientes": 80,
    "atendimentos_mensais": 1295,
    "pesquisas_nps": 422,
}
CANCELADOS_ESPERADOS = 22


@dataclass
class RelatorioImportacao:
    contagens: dict[str, int]
    avisos: list[str] = field(default_factory=list)


def _nulo(valor: Any) -> bool:
    return valor is None or (not isinstance(valor, str) and bool(pd.isna(valor)))


def _enum(valor: Any, enum_cls: type[Enum], campo: str) -> Any:
    chave = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    chave = chave.strip().upper().replace(" ", "_")
    try:
        return enum_cls(chave)
    except ValueError as erro:
        raise ImportacaoInvalidaError(f"Valor inválido '{valor}' em {campo}") from erro


def _mes(valor: Any, campo: str) -> date | None:
    if _nulo(valor):
        return None
    if isinstance(valor, datetime):
        return date(valor.year, valor.month, 1)
    try:
        ano, mes = str(valor).strip().split("-")[:2]
        return date(int(ano), int(mes), 1)
    except (ValueError, TypeError) as erro:
        raise ImportacaoInvalidaError(f"Mês inválido '{valor}' em {campo}") from erro


def _data(valor: Any, campo: str) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    try:
        return date.fromisoformat(str(valor).strip()[:10])
    except ValueError as erro:
        raise ImportacaoInvalidaError(f"Data inválida '{valor}' em {campo}") from erro


def _decimal(valor: Any) -> Decimal | None:
    return None if _nulo(valor) else Decimal(str(valor))


def _inteiro(valor: Any, campo: str) -> int:
    if _nulo(valor):
        raise ImportacaoInvalidaError(f"Valor vazio em {campo}")
    return int(valor)


class ImportacaoService:
    def __init__(self, repo: OrigemRepository, catalogo: CatalogoService) -> None:
        self._repo = repo
        self._catalogo = catalogo

    def importar(self, origem: str | Path | bytes) -> RelatorioImportacao:
        abas = self._ler(origem)
        clientes = [self._cliente(linha) for linha in abas["clientes"].to_dict("records")]
        situacoes = [
            self._situacao(linha) for linha in abas["situacao_clientes"].to_dict("records")
        ]
        atendimentos = [
            self._atendimento(linha) for linha in abas["atendimento_mensal"].to_dict("records")
        ]
        pesquisas = [self._pesquisa(linha) for linha in abas["pesquisas_nps"].to_dict("records")]
        self._validar_chaves(clientes, situacoes, atendimentos, pesquisas)

        self._repo.substituir_tudo(clientes, situacoes, atendimentos, pesquisas)
        self._catalogo.garantir_seeds()

        contagens = {
            "clientes": len(clientes),
            "situacao_clientes": len(situacoes),
            "atendimentos_mensais": len(atendimentos),
            "pesquisas_nps": len(pesquisas),
        }
        cancelados = sum(1 for s in situacoes if s.situacao == SituacaoCliente.CANCELADO)
        return RelatorioImportacao(contagens, self._avisos(contagens, cancelados))

    def _ler(self, origem: str | Path | bytes) -> dict[str, pd.DataFrame]:
        fonte = io.BytesIO(origem) if isinstance(origem, bytes) else origem
        try:
            abas = pd.read_excel(fonte, sheet_name=None)
        except Exception as erro:
            raise ImportacaoInvalidaError(
                "Não foi possível ler o arquivo: envie uma planilha .xlsx válida"
            ) from erro
        for aba, colunas in ABAS_COLUNAS.items():
            if aba not in abas:
                raise ImportacaoInvalidaError(f"Aba '{aba}' não encontrada no arquivo")
            faltando = [coluna for coluna in colunas if coluna not in abas[aba].columns]
            if faltando:
                raise ImportacaoInvalidaError(
                    f"Aba '{aba}' sem as colunas: {', '.join(faltando)}"
                )
        return abas

    @staticmethod
    def _cliente(linha: dict[str, Any]) -> Cliente:
        return Cliente(
            cliente_id=str(linha["cliente_id"]).strip(),
            segmento=str(linha["segmento"]).strip(),
            porte=_enum(linha["porte"], Porte, "clientes.porte"),
            plano=_enum(linha["plano"], Plano, "clientes.plano"),
            valor_mensal=_decimal(linha["valor_mensal"]),
            sla_contratado_h=_inteiro(linha["sla_contratado_h"], "clientes.sla_contratado_h"),
            inicio_contrato=_data(linha["inicio_contrato"], "clientes.inicio_contrato"),
        )

    @staticmethod
    def _situacao(linha: dict[str, Any]) -> Situacao:
        return Situacao(
            cliente_id=str(linha["cliente_id"]).strip(),
            situacao=_enum(linha["situacao"], SituacaoCliente, "situacao_clientes.situacao"),
            mes_cancelamento=_mes(linha["mes_cancelamento"], "situacao_clientes.mes_cancelamento"),
        )

    @staticmethod
    def _atendimento(linha: dict[str, Any]) -> AtendimentoMensal:
        inteiros = {
            coluna: _inteiro(linha[coluna], f"atendimento_mensal.{coluna}")
            for coluna in (
                "chamados_abertos",
                "chamados_criticos",
                "chamados_reabertos",
                "chamados_dentro_sla",
                "reclamacoes_formais",
                "dias_atraso_pagamento",
                "reunioes_previstas",
                "reunioes_realizadas",
            )
        }
        return AtendimentoMensal(
            cliente_id=str(linha["cliente_id"]).strip(),
            mes_ref=_mes(linha["mes_ref"], "atendimento_mensal.mes_ref"),
            pct_sla_cumprido=_decimal(linha["pct_sla_cumprido"]),
            tempo_medio_resolucao_h=_decimal(linha["tempo_medio_resolucao_h"]),
            uso_plataforma_pct=_decimal(linha["uso_plataforma_pct"]),
            **inteiros,
        )

    @staticmethod
    def _pesquisa(linha: dict[str, Any]) -> PesquisaNps:
        return PesquisaNps(
            cliente_id=str(linha["cliente_id"]).strip(),
            mes_ref=_mes(linha["mes_ref"], "pesquisas_nps.mes_ref"),
            respondeu=bool(_inteiro(linha["respondeu"], "pesquisas_nps.respondeu")),
            nota_nps=None if _nulo(linha["nota_nps"]) else int(linha["nota_nps"]),
            classificacao_nps=_enum(
                linha["classificacao_nps"], ClassificacaoNPS, "pesquisas_nps.classificacao_nps"
            ),
        )

    @staticmethod
    def _validar_chaves(
        clientes: list[Cliente],
        situacoes: list[Situacao],
        atendimentos: list[AtendimentoMensal],
        pesquisas: list[PesquisaNps],
    ) -> None:
        ids = [c.cliente_id for c in clientes]
        if len(ids) != len(set(ids)):
            raise ImportacaoInvalidaError("Aba 'clientes' tem cliente_id duplicado")
        conhecidos = set(ids)
        for aba, chaves in (
            ("situacao_clientes", [(s.cliente_id,) for s in situacoes]),
            ("atendimento_mensal", [(a.cliente_id, a.mes_ref) for a in atendimentos]),
            ("pesquisas_nps", [(p.cliente_id, p.mes_ref) for p in pesquisas]),
        ):
            if len(chaves) != len(set(chaves)):
                raise ImportacaoInvalidaError(f"Aba '{aba}' tem linhas duplicadas")
            desconhecidos = {chave[0] for chave in chaves} - conhecidos
            if desconhecidos:
                raise ImportacaoInvalidaError(
                    f"Aba '{aba}' cita clientes inexistentes: {', '.join(sorted(desconhecidos))}"
                )

    @staticmethod
    def _avisos(contagens: dict[str, int], cancelados: int) -> list[str]:
        avisos = [
            f"{tabela}: esperado {esperado}, importado {contagens[tabela]}"
            for tabela, esperado in CONTAGENS_ESPERADAS.items()
            if contagens[tabela] != esperado
        ]
        if cancelados != CANCELADOS_ESPERADOS:
            avisos.append(f"cancelados: esperado {CANCELADOS_ESPERADOS}, importado {cancelados}")
        return avisos
```

`backend/app/services/fabrica.py`:
```python
"""Monta services com seus repositories (usado pela API e pelos scripts)."""

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.acao_repository import AcaoRepository
from app.repositories.origem_repository import OrigemRepository
from app.repositories.sinal_repository import SinalRepository
from app.services.catalogo_service import CatalogoService
from app.services.importacao_service import ImportacaoService


def criar_catalogo_service(session: Session, settings: Settings) -> CatalogoService:
    return CatalogoService(
        SinalRepository(session), AcaoRepository(session), settings.persistencia_min_meses
    )


def criar_importacao_service(session: Session, settings: Settings) -> ImportacaoService:
    return ImportacaoService(OrigemRepository(session), criar_catalogo_service(session, settings))
```

- [ ] **Step 5: Implementar schema, controller, dependências e script**

`backend/app/schemas/importacao.py`:
```python
from pydantic import BaseModel, ConfigDict


class RelatorioImportacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contagens: dict[str, int]
    avisos: list[str]
```

Acrescente em `backend/app/dependencies.py`:
```python
from app.services.catalogo_service import CatalogoService
from app.services.fabrica import criar_catalogo_service, criar_importacao_service
from app.services.importacao_service import ImportacaoService


def get_catalogo_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)
) -> CatalogoService:
    return criar_catalogo_service(db, settings)


def get_importacao_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)
) -> ImportacaoService:
    return criar_importacao_service(db, settings)
```

`backend/app/controllers/importacao_controller.py`:
```python
from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_importacao_service, get_usuario_atual
from app.models import Usuario
from app.schemas.importacao import RelatorioImportacaoResponse
from app.services.importacao_service import ImportacaoService, RelatorioImportacao

router = APIRouter(tags=["importacao"])


@router.post("/importacao", response_model=RelatorioImportacaoResponse)
def importar(
    arquivo: UploadFile = File(..., description="Planilha INOVAAPPS (.xlsx)"),
    usuario: Usuario = Depends(get_usuario_atual),
    importacao: ImportacaoService = Depends(get_importacao_service),
) -> RelatorioImportacao:
    return importacao.importar(arquivo.file.read())
```

Em `backend/app/main.py`, inclua `importacao_controller.router` com `prefix="/api"`.

`backend/scripts/importar_base.py`:
```python
"""Importa a planilha para o banco.

Uso (a partir de backend/):  python -m scripts.importar_base [caminho.xlsx]
"""

import sys

from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, criar_engine
from app.services.fabrica import criar_importacao_service


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    settings = get_settings()
    caminho = argv[0] if argv else settings.caminho_xlsx
    engine = criar_engine(settings.database_url)
    Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False) as session:
            relatorio = criar_importacao_service(session, settings).importar(caminho)
            print("Importação concluída:")
            for tabela, quantidade in relatorio.contagens.items():
                print(f"  {tabela}: {quantidade}")
            for aviso in relatorio.avisos:
                print(f"  AVISO: {aviso}")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam.
Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 7: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): importação idempotente do xlsx, catálogo seed e POST /api/importacao" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Indicadores mensais (função pura)

**Files:**
- Create: `backend/app/services/risco/__init__.py` (vazio), `backend/app/services/risco/indicadores.py`
- Test: `backend/tests/unit/test_indicadores.py`

**Interfaces:**
- Consumes: `SentidoPiora` (Task 2).
- Produces: `calcular_indicadores(atendimentos: pd.DataFrame, pesquisas: pd.DataFrame, clientes: pd.DataFrame, mes_referencia: date) -> pd.DataFrame` com colunas `COLUNAS_SAIDA = [cliente_id, variavel, valor_mes, media_3m, soma_3m, linha_base_6m, variacao_pct, meses_consecutivos_piora]`; `SENTIDO_PIORA: dict[str, SentidoPiora]` (13 variáveis); `somar_meses(mes: date, n: int) -> date`; `DENOMINADOR_MINIMO = 0.5`. Entradas: `atendimentos` com `cliente_id`, `mes_ref` (date) e as colunas numéricas da aba (podem conter `Decimal`/`None`); `pesquisas` com `cliente_id`, `mes_ref`, `respondeu`, `nota_nps`; `clientes` com `cliente_id`, `sla_contratado_h`.

- [ ] **Step 1: Escrever os testes que falham**

`backend/tests/unit/test_indicadores.py`:
```python
import math
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from app.services.risco.indicadores import (
    COLUNAS_SAIDA,
    SENTIDO_PIORA,
    calcular_indicadores,
    somar_meses,
)

JAN25 = date(2025, 1, 1)
PADRAO = {
    "chamados_abertos": 5,
    "chamados_criticos": 1,
    "chamados_reabertos": 1,
    "pct_sla_cumprido": 80.0,
    "tempo_medio_resolucao_h": 12.0,
    "reclamacoes_formais": 0,
    "uso_plataforma_pct": 80.0,
    "dias_atraso_pagamento": 0,
    "reunioes_previstas": 1,
    "reunioes_realizadas": 1,
}
CLIENTES = pd.DataFrame(
    [{"cliente_id": "C001", "sla_contratado_h": 12}, {"cliente_id": "C002", "sla_contratado_h": 24}]
)
SEM_NPS = pd.DataFrame(columns=["cliente_id", "mes_ref", "respondeu", "nota_nps"])


def _atendimentos(n: int = 12, cliente_id: str = "C001", inicio: date = JAN25, **series):
    """n meses a partir de `inicio`; cada kwarg é a lista de n valores de uma coluna."""
    linhas = []
    for i in range(n):
        linha = {"cliente_id": cliente_id, "mes_ref": somar_meses(inicio, i)}
        for coluna, padrao in PADRAO.items():
            linha[coluna] = series[coluna][i] if coluna in series else padrao
        linhas.append(linha)
    return pd.DataFrame(linhas)


def _valor(df: pd.DataFrame, variavel: str, coluna: str, cliente_id: str = "C001"):
    linha = df[(df["cliente_id"] == cliente_id) & (df["variavel"] == variavel)]
    assert len(linha) == 1
    return linha.iloc[0][coluna]


def test_somar_meses_vira_o_ano():
    assert somar_meses(date(2025, 11, 1), 3) == date(2026, 2, 1)
    assert somar_meses(date(2025, 3, 1), -3) == date(2024, 12, 1)


def test_saida_tem_uma_linha_por_variavel():
    resultado = calcular_indicadores(_atendimentos(), SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert list(resultado.columns) == COLUNAS_SAIDA
    assert set(resultado["variavel"]) == set(SENTIDO_PIORA)
    assert len(resultado) == len(SENTIDO_PIORA)


def test_media_3m_linha_base_6m_e_variacao():
    at = _atendimentos(chamados_reabertos=list(range(1, 13)))
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert _valor(resultado, "chamados_reabertos", "valor_mes") == 12
    assert _valor(resultado, "chamados_reabertos", "media_3m") == pytest.approx(11.0)
    assert _valor(resultado, "chamados_reabertos", "soma_3m") == pytest.approx(33.0)
    assert _valor(resultado, "chamados_reabertos", "linha_base_6m") == pytest.approx(6.5)
    assert _valor(resultado, "chamados_reabertos", "variacao_pct") == pytest.approx(4.5 / 6.5)


def test_variacao_usa_denominador_minimo_quando_base_e_zero():
    at = _atendimentos(chamados_reabertos=[0] * 9 + [1, 1, 1])
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert _valor(resultado, "chamados_reabertos", "variacao_pct") == pytest.approx(2.0)


def test_media_ignora_nulos_de_sla():
    at = _atendimentos(pct_sla_cumprido=[80.0] * 9 + [80.0, None, 60.0])
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert _valor(resultado, "pct_sla_cumprido", "media_3m") == pytest.approx(70.0)


def test_aceita_decimal_e_none_vindos_do_banco():
    valores = [Decimal("80.0")] * 11 + [None]
    at = _atendimentos(pct_sla_cumprido=valores)
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert math.isnan(_valor(resultado, "pct_sla_cumprido", "valor_mes"))
    assert _valor(resultado, "pct_sla_cumprido", "media_3m") == pytest.approx(80.0)


def test_mes_futuro_nao_vaza_para_o_calculo():
    doze = _atendimentos(12, chamados_reabertos=list(range(1, 13)))
    treze = _atendimentos(13, chamados_reabertos=list(range(1, 13)) + [99])
    mes = somar_meses(JAN25, 11)

    pd.testing.assert_frame_equal(
        calcular_indicadores(doze, SEM_NPS, CLIENTES, mes),
        calcular_indicadores(treze, SEM_NPS, CLIENTES, mes),
    )


def test_meses_consecutivos_de_piora_respeitam_o_sentido():
    at = _atendimentos(
        chamados_reabertos=[1] * 9 + [5, 5, 5],
        uso_plataforma_pct=[80.0] * 10 + [60.0, 60.0],
    )
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert _valor(resultado, "chamados_reabertos", "meses_consecutivos_piora") == 3
    assert _valor(resultado, "uso_plataforma_pct", "meses_consecutivos_piora") == 2
    assert _valor(resultado, "dias_atraso_pagamento", "meses_consecutivos_piora") == 0


def test_derivados_ficam_nulos_sem_chamado_ou_sem_reuniao_prevista():
    at = _atendimentos(chamados_abertos=[5] * 11 + [0], reunioes_previstas=[1] * 11 + [0])
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert math.isnan(_valor(resultado, "taxa_reabertura", "valor_mes"))
    assert math.isnan(_valor(resultado, "tempo_resolucao_vs_sla", "valor_mes"))
    assert math.isnan(_valor(resultado, "pct_reunioes_realizadas", "valor_mes"))
    # tempo 12h / SLA 12h = 1,0 nos meses anteriores
    assert _valor(resultado, "tempo_resolucao_vs_sla", "media_3m") == pytest.approx(1.0)


def test_nps_nota_variacao_e_silencio():
    pesquisas = pd.DataFrame(
        [
            {"cliente_id": "C001", "mes_ref": date(2025, 3, 1), "respondeu": 1, "nota_nps": 9},
            {"cliente_id": "C001", "mes_ref": date(2025, 6, 1), "respondeu": 1, "nota_nps": 6},
            {"cliente_id": "C001", "mes_ref": date(2025, 9, 1), "respondeu": 0, "nota_nps": None},
            {"cliente_id": "C001", "mes_ref": date(2025, 12, 1), "respondeu": 0, "nota_nps": None},
        ]
    )
    resultado = calcular_indicadores(_atendimentos(), pesquisas, CLIENTES, date(2025, 12, 1))

    assert _valor(resultado, "nps_nota", "valor_mes") == 6
    assert _valor(resultado, "nps_variacao", "valor_mes") == -3
    assert _valor(resultado, "nps_sem_resposta_consecutivas", "valor_mes") == 2


def test_silencio_so_conta_se_ja_respondeu_antes():
    pesquisas = pd.DataFrame(
        [{"cliente_id": "C001", "mes_ref": date(2025, 3, 1), "respondeu": 0, "nota_nps": None}]
    )
    resultado = calcular_indicadores(_atendimentos(), pesquisas, CLIENTES, date(2025, 12, 1))

    assert _valor(resultado, "nps_sem_resposta_consecutivas", "valor_mes") == 0
    assert math.isnan(_valor(resultado, "nps_nota", "valor_mes"))


def test_historico_curto_deixa_base_e_variacao_nulas():
    resultado = calcular_indicadores(_atendimentos(3), SEM_NPS, CLIENTES, date(2025, 3, 1))

    assert math.isnan(_valor(resultado, "chamados_reabertos", "linha_base_6m"))
    assert math.isnan(_valor(resultado, "chamados_reabertos", "variacao_pct"))
    assert _valor(resultado, "chamados_reabertos", "meses_consecutivos_piora") == 0


def test_cliente_sem_dados_ate_o_mes_fica_de_fora():
    at = pd.concat(
        [_atendimentos(12), _atendimentos(3, cliente_id="C002", inicio=date(2026, 1, 1))]
    )
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, date(2025, 12, 1))

    assert set(resultado["cliente_id"]) == {"C001"}
    assert calcular_indicadores(at, SEM_NPS, CLIENTES, date(2024, 12, 1)).empty
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/unit/test_indicadores.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'app.services.risco'`.

- [ ] **Step 3: Implementar**

`backend/app/services/risco/indicadores.py`:
```python
"""Indicadores mensais por cliente — função pura, sem acesso ao banco.

Regra de negócio: cada indicador do mês M usa somente dados até M
(sem vazamento do futuro). Para cada variável calculamos o nível recente
(média/soma dos últimos 3 meses), a linha de base (média dos 6 meses
anteriores a essa janela), a variação relativa e há quantos meses seguidos
o valor está pior que a base.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from app.core.enums import SentidoPiora

# Denominador mínimo da variação relativa: evita percentuais explosivos
# quando a linha de base é ~0 (ex.: nenhum chamado reaberto no passado).
DENOMINADOR_MINIMO = 0.5

SENTIDO_PIORA: dict[str, SentidoPiora] = {
    "chamados_abertos": SentidoPiora.AUMENTO,
    "chamados_criticos": SentidoPiora.AUMENTO,
    "chamados_reabertos": SentidoPiora.AUMENTO,
    "taxa_reabertura": SentidoPiora.AUMENTO,
    "pct_sla_cumprido": SentidoPiora.QUEDA,
    "tempo_resolucao_vs_sla": SentidoPiora.AUMENTO,
    "reclamacoes_formais": SentidoPiora.AUMENTO,
    "uso_plataforma_pct": SentidoPiora.QUEDA,
    "dias_atraso_pagamento": SentidoPiora.AUMENTO,
    "pct_reunioes_realizadas": SentidoPiora.QUEDA,
    "nps_nota": SentidoPiora.QUEDA,
    "nps_variacao": SentidoPiora.QUEDA,
    "nps_sem_resposta_consecutivas": SentidoPiora.AUMENTO,
}

COLUNAS_SAIDA = [
    "cliente_id",
    "variavel",
    "valor_mes",
    "media_3m",
    "soma_3m",
    "linha_base_6m",
    "variacao_pct",
    "meses_consecutivos_piora",
]


def somar_meses(mes: date, n: int) -> date:
    """Soma n meses (pode ser negativo) a uma data de dia 1."""
    ano, indice = divmod(mes.year * 12 + mes.month - 1 + n, 12)
    return date(ano, indice + 1, 1)


def _meses_entre(inicio: date, fim: date) -> list[date]:
    meses = []
    atual = inicio
    while atual <= fim:
        meses.append(atual)
        atual = somar_meses(atual, 1)
    return meses


def _numerico(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce").astype(float)


def _derivar_atendimento(atendimentos: pd.DataFrame, sla_por_cliente: pd.Series) -> pd.DataFrame:
    at = atendimentos.copy()
    abertos = _numerico(at["chamados_abertos"])
    tem_chamado = abertos > 0
    sla = _numerico(at["cliente_id"].map(sla_por_cliente))
    at["taxa_reabertura"] = (_numerico(at["chamados_reabertos"]) / abertos).where(tem_chamado)
    # Sem chamado no mês não há tempo de resolução a medir: fica nulo.
    at["tempo_resolucao_vs_sla"] = (_numerico(at["tempo_medio_resolucao_h"]) / sla).where(
        tem_chamado
    )
    previstas = _numerico(at["reunioes_previstas"])
    at["pct_reunioes_realizadas"] = (_numerico(at["reunioes_realizadas"]) / previstas).where(
        previstas > 0
    )
    return at


def _estado_nps(pesquisas_cliente: pd.DataFrame, meses: list[date]) -> pd.DataFrame:
    """Estado do NPS em cada mês, olhando só as pesquisas até aquele mês."""
    pesquisas = pesquisas_cliente.sort_values("mes_ref")
    linhas = []
    for mes in meses:
        ate_mes = pesquisas[pesquisas["mes_ref"] <= mes]
        respondeu = ate_mes["respondeu"].astype(bool)
        notas = _numerico(ate_mes["nota_nps"][respondeu]).dropna().tolist()
        silencio = 0
        if notas:  # o silêncio só é sinal se o cliente já respondeu antes
            for resposta in reversed(respondeu.tolist()):
                if resposta:
                    break
                silencio += 1
        linhas.append(
            {
                "nps_nota": notas[-1] if notas else np.nan,
                "nps_variacao": notas[-1] - notas[-2] if len(notas) >= 2 else np.nan,
                "nps_sem_resposta_consecutivas": float(silencio),
            }
        )
    return pd.DataFrame(linhas, index=meses)


def _resumir_serie(serie: pd.Series, sentido: SentidoPiora) -> dict[str, float | int]:
    serie = serie.astype(float)
    media_3m = serie.rolling(3, min_periods=1).mean()
    soma_3m = serie.rolling(3, min_periods=1).sum()
    linha_base = serie.shift(3).rolling(6, min_periods=1).mean()
    pior = serie > linha_base if sentido == SentidoPiora.AUMENTO else serie < linha_base
    pior = pior & serie.notna() & linha_base.notna()
    consecutivos = 0
    for mes_pior in reversed(pior.tolist()):
        if not mes_pior:
            break
        consecutivos += 1
    media, base = media_3m.iloc[-1], linha_base.iloc[-1]
    variacao = (
        (media - base) / max(abs(base), DENOMINADOR_MINIMO)
        if pd.notna(media) and pd.notna(base)
        else np.nan
    )
    return {
        "valor_mes": serie.iloc[-1],
        "media_3m": media,
        "soma_3m": soma_3m.iloc[-1],
        "linha_base_6m": base,
        "variacao_pct": variacao,
        "meses_consecutivos_piora": consecutivos,
    }


def calcular_indicadores(
    atendimentos: pd.DataFrame,
    pesquisas: pd.DataFrame,
    clientes: pd.DataFrame,
    mes_referencia: date,
) -> pd.DataFrame:
    """Indicadores de cada cliente × variável no mês de referência.

    Clientes sem nenhum atendimento até o mês de referência ficam de fora.
    """
    at = atendimentos[atendimentos["mes_ref"] <= mes_referencia]
    if at.empty:
        return pd.DataFrame(columns=COLUNAS_SAIDA)
    pq = pesquisas[pesquisas["mes_ref"] <= mes_referencia]
    sla = clientes.set_index("cliente_id")["sla_contratado_h"]
    at = _derivar_atendimento(at, sla)

    linhas = []
    for cliente_id, grupo in at.groupby("cliente_id", sort=True):
        meses = _meses_entre(min(grupo["mes_ref"]), mes_referencia)
        painel = grupo.set_index("mes_ref").reindex(meses)
        painel = painel.join(_estado_nps(pq[pq["cliente_id"] == cliente_id], meses))
        for variavel, sentido in SENTIDO_PIORA.items():
            linhas.append(
                {
                    "cliente_id": cliente_id,
                    "variavel": variavel,
                    **_resumir_serie(painel[variavel], sentido),
                }
            )
    return pd.DataFrame(linhas, columns=COLUNAS_SAIDA)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/unit/test_indicadores.py -v`
Expected: todos passam. Se algum falhar, não mude o teste — investigue o cálculo (ex.: `rolling` com `NaN`).
Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 5: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): cálculo puro de indicadores mensais sem vazamento" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Sinais, score, recomendação e priorização (funções puras)

**Files:**
- Create: `backend/app/services/risco/sinais.py`, `score.py`, `recomendacao.py`, `priorizacao.py`
- Test: `backend/tests/unit/test_sinais.py`, `test_score.py`, `test_recomendacao.py`, `test_priorizacao.py`

**Interfaces:**
- Consumes: enums (Task 2). Indicador = mapeamento com as chaves de `COLUNAS_SAIDA` da Task 6 (sem `cliente_id`/`variavel`).
- Produces:
  - `DefinicaoSinal(id, codigo, dimensao, variavel, tipo_regra, sentido_piora, limiar: float, persistencia_min_meses: int, peso: float, template_evidencia: str, metrica: str = "media_3m")` (frozen dataclass)
  - `Disparo(sinal, valor_observado, linha_base, variacao_pct, meses_persistencia, intensidade, texto)`
  - `avaliar_sinal(sinal, indicador) -> Disparo | None`, `avaliar_sinais(sinais, indicadores_cliente: Mapping[str, indicador]) -> list[Disparo]`, `preencher_template(template, indicador) -> str`
  - `LimiaresFaixa(critico, atencao, monitorar)`, `Evidencia(disparo, contribuicao)`, `ResultadoScore(score, faixa, qtd_dimensoes_afetadas, evidencias)`, `classificar_faixa(score, qtd_dimensoes, limiares) -> FaixaRisco`, `calcular_score(disparos, limiares) -> ResultadoScore`
  - `recomendar(evidencias: list[Evidencia]) -> str | None` (código da ação)
  - `ItemAvaliado(cliente_id, valor_mensal, score, faixa, receita_em_risco=0.0, posicao_fila=None)`, `priorizar(itens, capacidade) -> list[ItemAvaliado]`

- [ ] **Step 1: Escrever os testes que falham**

`backend/tests/unit/test_sinais.py`:
```python
import math

import pytest

from app.core.enums import Dimensao, SentidoPiora, TipoRegra
from app.services.risco.sinais import DefinicaoSinal, avaliar_sinal, avaliar_sinais


def _sinal(**kw) -> DefinicaoSinal:
    padrao = dict(
        id=1,
        codigo="X",
        dimensao=Dimensao.ATENDIMENTO,
        variavel="chamados_reabertos",
        tipo_regra=TipoRegra.TENDENCIA,
        sentido_piora=SentidoPiora.AUMENTO,
        limiar=0.5,
        persistencia_min_meses=2,
        peso=0.1,
        template_evidencia="subiu {variacao_pct:.0%}",
        metrica="media_3m",
    )
    return DefinicaoSinal(**{**padrao, **kw})


def _ind(**kw) -> dict:
    padrao = dict(
        valor_mes=1.0,
        media_3m=1.0,
        soma_3m=3.0,
        linha_base_6m=1.0,
        variacao_pct=0.0,
        meses_consecutivos_piora=0,
    )
    return {**padrao, **kw}


def test_tendencia_dispara_com_persistencia_e_preenche_texto():
    disparo = avaliar_sinal(_sinal(), _ind(variacao_pct=1.0, meses_consecutivos_piora=2))

    assert disparo is not None
    assert disparo.intensidade == pytest.approx(1.0)
    assert disparo.texto == "subiu 100%"
    assert disparo.meses_persistencia == 2
    assert disparo.variacao_pct == pytest.approx(1.0)


def test_tendencia_sem_persistencia_nao_dispara():
    assert avaliar_sinal(_sinal(), _ind(variacao_pct=1.0, meses_consecutivos_piora=1)) is None


def test_tendencia_abaixo_do_limiar_nao_dispara():
    assert avaliar_sinal(_sinal(), _ind(variacao_pct=0.4, meses_consecutivos_piora=3)) is None


@pytest.mark.parametrize("variacao,esperado", [(0.5, 0.5), (0.75, 0.75), (1.0, 1.0), (5.0, 1.0)])
def test_intensidade_vai_de_meio_no_limiar_a_um_no_dobro(variacao, esperado):
    disparo = avaliar_sinal(_sinal(), _ind(variacao_pct=variacao, meses_consecutivos_piora=2))

    assert disparo.intensidade == pytest.approx(esperado)


def test_tendencia_de_queda_inverte_o_sinal():
    sinal = _sinal(
        sentido_piora=SentidoPiora.QUEDA,
        limiar=0.15,
        template_evidencia="caiu {queda_pct:.0%}",
    )

    disparo = avaliar_sinal(sinal, _ind(variacao_pct=-0.2, meses_consecutivos_piora=2))
    assert disparo is not None and disparo.texto == "caiu 20%"
    assert avaliar_sinal(sinal, _ind(variacao_pct=0.3, meses_consecutivos_piora=2)) is None


def test_nivel_de_queda_nao_exige_persistencia():
    sinal = _sinal(
        tipo_regra=TipoRegra.NIVEL,
        sentido_piora=SentidoPiora.QUEDA,
        limiar=65,
        variavel="pct_sla_cumprido",
        template_evidencia="SLA {media_3m:.0f}%",
    )

    disparo = avaliar_sinal(sinal, _ind(media_3m=50.0))
    assert disparo is not None
    assert disparo.texto == "SLA 50%"
    assert disparo.intensidade == pytest.approx(0.5 + 0.5 * 15 / 65)
    assert avaliar_sinal(sinal, _ind(media_3m=70.0)) is None


def test_nivel_usa_a_metrica_configurada():
    sinal = _sinal(
        tipo_regra=TipoRegra.NIVEL, limiar=2, metrica="soma_3m", template_evidencia="{soma_3m:.0f}"
    )

    assert avaliar_sinal(sinal, _ind(soma_3m=3.0, media_3m=1.0)).texto == "3"
    assert avaliar_sinal(sinal, _ind(soma_3m=1.0, media_3m=5.0)) is None


def test_evento_de_queda_do_nps():
    sinal = _sinal(
        tipo_regra=TipoRegra.EVENTO,
        sentido_piora=SentidoPiora.QUEDA,
        limiar=2,
        variavel="nps_variacao",
        template_evidencia="caiu {queda_abs:.0f} pontos",
    )

    assert avaliar_sinal(sinal, _ind(valor_mes=-3.0)).texto == "caiu 3 pontos"
    assert avaliar_sinal(sinal, _ind(valor_mes=-1.0)) is None


@pytest.mark.parametrize("nulo", [None, math.nan])
def test_metrica_nula_nunca_dispara(nulo):
    assert avaliar_sinal(_sinal(), _ind(variacao_pct=nulo, meses_consecutivos_piora=5)) is None
    nivel = _sinal(tipo_regra=TipoRegra.NIVEL, limiar=1)
    assert avaliar_sinal(nivel, _ind(media_3m=nulo)) is None


def test_avaliar_sinais_ignora_variavel_ausente_e_devolve_so_disparos():
    sinais = [_sinal(codigo="A"), _sinal(codigo="B", variavel="uso_plataforma_pct")]
    indicadores = {"chamados_reabertos": _ind(variacao_pct=1.0, meses_consecutivos_piora=2)}

    disparos = avaliar_sinais(sinais, indicadores)

    assert [d.sinal.codigo for d in disparos] == ["A"]
```

`backend/tests/unit/test_score.py`:
```python
import pytest

from app.core.enums import Dimensao, FaixaRisco, SentidoPiora, TipoRegra
from app.services.risco.score import LimiaresFaixa, calcular_score, classificar_faixa
from app.services.risco.sinais import DefinicaoSinal, Disparo

LIMIARES = LimiaresFaixa(critico=0.55, atencao=0.30, monitorar=0.15)


def _disparo(codigo: str, dimensao: Dimensao, peso: float = 0.1, intensidade: float = 1.0):
    sinal = DefinicaoSinal(
        id=1,
        codigo=codigo,
        dimensao=dimensao,
        variavel="v",
        tipo_regra=TipoRegra.NIVEL,
        sentido_piora=SentidoPiora.AUMENTO,
        limiar=1.0,
        persistencia_min_meses=2,
        peso=peso,
        template_evidencia="",
    )
    return Disparo(sinal, 1.0, None, None, 0, intensidade, codigo)


@pytest.mark.parametrize(
    "score,esperada",
    [
        (0.55, FaixaRisco.CRITICO),
        (0.30, FaixaRisco.ATENCAO),
        (0.15, FaixaRisco.MONITORAR),
        (0.149, FaixaRisco.SAUDAVEL),
    ],
)
def test_faixas_por_limiar_com_duas_dimensoes(score, esperada):
    assert classificar_faixa(score, 2, LIMIARES) == esperada


def test_uma_dimensao_nunca_passa_de_monitorar():
    assert classificar_faixa(0.9, 1, LIMIARES) == FaixaRisco.MONITORAR
    assert classificar_faixa(0.1, 1, LIMIARES) == FaixaRisco.SAUDAVEL


def test_score_soma_contribuicoes_e_ordena_evidencias():
    resultado = calcular_score(
        [
            _disparo("A", Dimensao.ATENDIMENTO, peso=0.2, intensidade=0.5),
            _disparo("B", Dimensao.SLA, peso=0.3, intensidade=1.0),
        ],
        LIMIARES,
    )

    assert resultado.score == pytest.approx(0.4)
    assert resultado.qtd_dimensoes_afetadas == 2
    assert resultado.faixa == FaixaRisco.ATENCAO
    assert [e.disparo.sinal.codigo for e in resultado.evidencias] == ["B", "A"]
    assert resultado.evidencias[0].contribuicao == pytest.approx(0.3)


def test_score_limitado_a_um():
    disparos = [_disparo(f"S{i}", Dimensao.ATENDIMENTO, peso=0.3) for i in range(5)]
    disparos.append(_disparo("F", Dimensao.FINANCEIRO, peso=0.3))

    assert calcular_score(disparos, LIMIARES).score == 1.0


def test_sem_disparos_e_saudavel():
    resultado = calcular_score([], LIMIARES)

    assert (resultado.score, resultado.faixa, resultado.qtd_dimensoes_afetadas) == (
        0.0,
        FaixaRisco.SAUDAVEL,
        0,
    )
```

`backend/tests/unit/test_recomendacao.py`:
```python
from app.core.enums import Dimensao, SentidoPiora, TipoRegra
from app.services.risco.recomendacao import recomendar
from app.services.risco.score import Evidencia
from app.services.risco.sinais import DefinicaoSinal, Disparo


def _ev(codigo: str, dimensao: Dimensao, contribuicao: float = 0.1) -> Evidencia:
    sinal = DefinicaoSinal(
        1, codigo, dimensao, "v", TipoRegra.NIVEL, SentidoPiora.AUMENTO, 1.0, 2, 0.1, ""
    )
    return Evidencia(Disparo(sinal, 1.0, None, None, 0, 1.0, ""), contribuicao)


def test_sem_evidencias_nao_recomenda():
    assert recomendar([]) is None


def test_tres_dimensoes_vira_comite():
    evidencias = [
        _ev("A", Dimensao.ATENDIMENTO),
        _ev("B", Dimensao.FINANCEIRO),
        _ev("C", Dimensao.SATISFACAO),
    ]
    assert recomendar(evidencias) == "COMITE_RETENCAO"


def test_reunioes_e_silencio_viram_contato_executivo():
    evidencias = [
        _ev("REUNIOES_CANCELADAS", Dimensao.ENGAJAMENTO),
        _ev("NPS_SILENCIO", Dimensao.SATISFACAO),
    ]
    assert recomendar(evidencias) == "CONTATO_EXECUTIVO"


def test_dimensao_dominante_define_a_acao():
    assert recomendar([_ev("A", Dimensao.SLA)]) == "REVISAO_TECNICA"
    assert recomendar([_ev("A", Dimensao.ATENDIMENTO)]) == "REVISAO_TECNICA"
    assert recomendar([_ev("A", Dimensao.ENGAJAMENTO)]) == "REUNIAO_VALOR"
    assert recomendar([_ev("A", Dimensao.SATISFACAO)]) == "PLANO_DE_RECUPERACAO"
    misto = [_ev("F", Dimensao.FINANCEIRO, 0.10), _ev("A", Dimensao.ATENDIMENTO, 0.05)]
    assert recomendar(misto) == "CONVERSA_FINANCEIRA"


def test_contribuicoes_da_mesma_dimensao_se_somam():
    evidencias = [
        _ev("A1", Dimensao.ATENDIMENTO, 0.06),
        _ev("A2", Dimensao.ATENDIMENTO, 0.06),
        _ev("F", Dimensao.FINANCEIRO, 0.10),
    ]
    assert recomendar(evidencias) == "REVISAO_TECNICA"
```

`backend/tests/unit/test_priorizacao.py`:
```python
from app.core.enums import FaixaRisco
from app.services.risco.priorizacao import ItemAvaliado, priorizar


def _item(cliente_id: str, valor: float, score: float, faixa: FaixaRisco) -> ItemAvaliado:
    return ItemAvaliado(cliente_id=cliente_id, valor_mensal=valor, score=score, faixa=faixa)


def test_receita_em_risco_e_score_vezes_valor():
    [item] = priorizar([_item("C1", 10000.0, 0.4, FaixaRisco.ATENCAO)], capacidade=10)

    assert item.receita_em_risco == 4000.0


def test_ordena_por_faixa_e_depois_por_receita():
    itens = [
        _item("ATENCAO_GRANDE", 30000.0, 0.4, FaixaRisco.ATENCAO),
        _item("CRITICO_PEQUENO", 3000.0, 0.6, FaixaRisco.CRITICO),
        _item("ATENCAO_MEDIO", 10000.0, 0.4, FaixaRisco.ATENCAO),
        _item("SAUDAVEL", 50000.0, 0.0, FaixaRisco.SAUDAVEL),
    ]

    resultado = priorizar(itens, capacidade=10)

    assert [i.cliente_id for i in resultado] == [
        "CRITICO_PEQUENO",
        "ATENCAO_GRANDE",
        "ATENCAO_MEDIO",
        "SAUDAVEL",
    ]
    assert [i.posicao_fila for i in resultado] == [1, 2, 3, None]


def test_capacidade_limita_a_fila_e_monitorar_fica_de_fora():
    itens = [_item(f"C{i}", 1000.0 * (i + 1), 0.4, FaixaRisco.ATENCAO) for i in range(5)]
    itens.append(_item("M", 99999.0, 0.2, FaixaRisco.MONITORAR))

    resultado = priorizar(itens, capacidade=3)

    na_fila = [i for i in resultado if i.posicao_fila is not None]
    assert [i.posicao_fila for i in na_fila] == [1, 2, 3]
    assert [i.cliente_id for i in na_fila] == ["C4", "C3", "C2"]
    assert next(i for i in resultado if i.cliente_id == "M").posicao_fila is None


def test_nao_altera_a_lista_de_entrada():
    original = _item("C1", 1000.0, 0.4, FaixaRisco.ATENCAO)

    priorizar([original], capacidade=10)

    assert original.posicao_fila is None
    assert original.receita_em_risco == 0.0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/unit/test_sinais.py tests/unit/test_score.py tests/unit/test_recomendacao.py tests/unit/test_priorizacao.py -v`
Expected: ERROR `ModuleNotFoundError` (`app.services.risco.sinais` etc.).

- [ ] **Step 3: Implementar**

`backend/app/services/risco/sinais.py`:
```python
"""Avaliação de sinais de risco sobre os indicadores — funções puras.

Regras de disparo:
- TENDENCIA: variação relativa (invertida se o sentido de piora é QUEDA) ≥ limiar
  e piora persistente por `persistencia_min_meses` meses seguidos.
- NIVEL: `metrica` (media_3m ou soma_3m) acima (AUMENTO) ou abaixo (QUEDA) do limiar;
  a janela de 3 meses já expressa persistência.
- EVENTO: valor do mês (invertido se QUEDA) ≥ limiar.
Métrica nula nunca dispara. A intensidade vai de 0,5 (no limiar) a 1,0 (2× o limiar).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.core.enums import Dimensao, SentidoPiora, TipoRegra

Indicador = Mapping[str, Any]


@dataclass(frozen=True)
class DefinicaoSinal:
    id: int | None
    codigo: str
    dimensao: Dimensao
    variavel: str
    tipo_regra: TipoRegra
    sentido_piora: SentidoPiora
    limiar: float
    persistencia_min_meses: int
    peso: float
    template_evidencia: str
    metrica: str = "media_3m"


@dataclass(frozen=True)
class Disparo:
    sinal: DefinicaoSinal
    valor_observado: float
    linha_base: float | None
    variacao_pct: float | None
    meses_persistencia: int
    intensidade: float
    texto: str


def _nulo(valor: Any) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def _opcional(valor: Any) -> float | None:
    return None if _nulo(valor) else float(valor)


def preencher_template(template: str, indicador: Indicador) -> str:
    """Preenche o texto da evidência; campos nulos viram 0."""
    ctx = {
        chave: 0.0 if _nulo(indicador.get(chave)) else float(indicador[chave])
        for chave in ("valor_mes", "media_3m", "soma_3m", "linha_base_6m", "variacao_pct")
    }
    ctx["linha_base"] = ctx["linha_base_6m"]
    ctx["queda_pct"] = -ctx["variacao_pct"]
    ctx["queda_abs"] = -ctx["valor_mes"]
    return template.format(**ctx)


def avaliar_sinal(sinal: DefinicaoSinal, indicador: Indicador) -> Disparo | None:
    """Retorna o disparo do sinal para um indicador (cliente × variável) ou None."""
    persistencia = int(indicador.get("meses_consecutivos_piora") or 0)
    limiar = sinal.limiar
    if sinal.tipo_regra == TipoRegra.NIVEL:
        bruto = indicador.get(sinal.metrica)
        if _nulo(bruto):
            return None
        bruto = float(bruto)
        if sinal.sentido_piora == SentidoPiora.AUMENTO:
            dispara, excesso = bruto >= limiar, (bruto - limiar) / abs(limiar)
        else:
            dispara, excesso = bruto <= limiar, (limiar - bruto) / abs(limiar)
    else:
        campo = "variacao_pct" if sinal.tipo_regra == TipoRegra.TENDENCIA else "valor_mes"
        bruto = indicador.get(campo)
        if _nulo(bruto):
            return None
        bruto = float(bruto)
        orientado = -bruto if sinal.sentido_piora == SentidoPiora.QUEDA else bruto
        dispara, excesso = orientado >= limiar, (orientado - limiar) / abs(limiar)
        if sinal.tipo_regra == TipoRegra.TENDENCIA and persistencia < sinal.persistencia_min_meses:
            dispara = False
    if not dispara:
        return None
    return Disparo(
        sinal=sinal,
        valor_observado=bruto,
        linha_base=_opcional(indicador.get("linha_base_6m")),
        variacao_pct=_opcional(indicador.get("variacao_pct")),
        meses_persistencia=persistencia,
        intensidade=0.5 + 0.5 * min(1.0, max(0.0, excesso)),
        texto=preencher_template(sinal.template_evidencia, indicador),
    )


def avaliar_sinais(
    sinais: list[DefinicaoSinal], indicadores_cliente: Mapping[str, Indicador]
) -> list[Disparo]:
    """Avalia todos os sinais de um cliente. `indicadores_cliente` é variavel -> indicador."""
    disparos = []
    for sinal in sinais:
        indicador = indicadores_cliente.get(sinal.variavel)
        if indicador is None:
            continue
        disparo = avaliar_sinal(sinal, indicador)
        if disparo is not None:
            disparos.append(disparo)
    return disparos
```

`backend/app/services/risco/score.py`:
```python
"""Score de risco — função pura.

Regra de negócio: score = soma(peso × intensidade) dos sinais disparados,
limitado a [0, 1]. Para evitar alarme falso, um cliente com menos de 2
dimensões afetadas nunca passa de MONITORAR.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import FaixaRisco
from app.services.risco.sinais import Disparo


@dataclass(frozen=True)
class LimiaresFaixa:
    critico: float
    atencao: float
    monitorar: float


@dataclass(frozen=True)
class Evidencia:
    disparo: Disparo
    contribuicao: float


@dataclass(frozen=True)
class ResultadoScore:
    score: float
    faixa: FaixaRisco
    qtd_dimensoes_afetadas: int
    evidencias: list[Evidencia]


def classificar_faixa(score: float, qtd_dimensoes: int, limiares: LimiaresFaixa) -> FaixaRisco:
    if score >= limiares.critico:
        faixa = FaixaRisco.CRITICO
    elif score >= limiares.atencao:
        faixa = FaixaRisco.ATENCAO
    elif score >= limiares.monitorar:
        faixa = FaixaRisco.MONITORAR
    else:
        faixa = FaixaRisco.SAUDAVEL
    if qtd_dimensoes < 2 and faixa in (FaixaRisco.CRITICO, FaixaRisco.ATENCAO):
        faixa = FaixaRisco.MONITORAR
    return faixa


def calcular_score(disparos: list[Disparo], limiares: LimiaresFaixa) -> ResultadoScore:
    evidencias = sorted(
        (Evidencia(d, round(d.sinal.peso * d.intensidade, 4)) for d in disparos),
        key=lambda e: (-e.contribuicao, e.disparo.sinal.codigo),
    )
    score = round(min(1.0, sum(e.contribuicao for e in evidencias)), 4)
    qtd_dimensoes = len({e.disparo.sinal.dimensao for e in evidencias})
    return ResultadoScore(
        score=score,
        faixa=classificar_faixa(score, qtd_dimensoes, limiares),
        qtd_dimensoes_afetadas=qtd_dimensoes,
        evidencias=evidencias,
    )
```

`backend/app/services/risco/recomendacao.py`:
```python
"""Recomendação de ação a partir das evidências — função pura.

Regras (em ordem): 3+ dimensões → COMITE_RETENCAO; reuniões canceladas +
silêncio no NPS → CONTATO_EXECUTIVO; senão, a dimensão com maior
contribuição somada define a ação.
"""

from __future__ import annotations

from collections import defaultdict

from app.core.enums import Dimensao
from app.services.risco.score import Evidencia

ACAO_POR_DIMENSAO: dict[Dimensao, str] = {
    Dimensao.ATENDIMENTO: "REVISAO_TECNICA",
    Dimensao.SLA: "REVISAO_TECNICA",
    Dimensao.ENGAJAMENTO: "REUNIAO_VALOR",
    Dimensao.FINANCEIRO: "CONVERSA_FINANCEIRA",
    Dimensao.SATISFACAO: "PLANO_DE_RECUPERACAO",
}
ORDEM_DIMENSAO = list(Dimensao)


def recomendar(evidencias: list[Evidencia]) -> str | None:
    if not evidencias:
        return None
    dimensoes = {e.disparo.sinal.dimensao for e in evidencias}
    if len(dimensoes) >= 3:
        return "COMITE_RETENCAO"
    codigos = {e.disparo.sinal.codigo for e in evidencias}
    if {"REUNIOES_CANCELADAS", "NPS_SILENCIO"} <= codigos:
        return "CONTATO_EXECUTIVO"
    por_dimensao: dict[Dimensao, float] = defaultdict(float)
    for evidencia in evidencias:
        por_dimensao[evidencia.disparo.sinal.dimensao] += evidencia.contribuicao
    dominante = min(por_dimensao, key=lambda d: (-por_dimensao[d], ORDEM_DIMENSAO.index(d)))
    return ACAO_POR_DIMENSAO[dominante]
```

`backend/app/services/risco/priorizacao.py`:
```python
"""Fila de atendimento priorizada — função pura.

Regra: receita em risco = score × valor mensal. Entram na fila só CRITICO e
ATENCAO, ordenados por faixa e depois por receita em risco (maior primeiro),
até a capacidade da fila. Os demais continuam avaliados, mas sem posição.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.core.enums import FaixaRisco

ORDEM_FAIXA = {
    FaixaRisco.CRITICO: 0,
    FaixaRisco.ATENCAO: 1,
    FaixaRisco.MONITORAR: 2,
    FaixaRisco.SAUDAVEL: 3,
}
FAIXAS_DA_FILA = {FaixaRisco.CRITICO, FaixaRisco.ATENCAO}


@dataclass
class ItemAvaliado:
    cliente_id: str
    valor_mensal: float
    score: float
    faixa: FaixaRisco
    receita_em_risco: float = 0.0
    posicao_fila: int | None = None


def priorizar(itens: list[ItemAvaliado], capacidade: int) -> list[ItemAvaliado]:
    calculados = [
        replace(item, receita_em_risco=round(item.score * item.valor_mensal, 2), posicao_fila=None)
        for item in itens
    ]
    ordenados = sorted(
        calculados,
        key=lambda i: (ORDEM_FAIXA[i.faixa], -i.receita_em_risco, i.cliente_id),
    )
    posicao = 0
    for item in ordenados:
        if item.faixa in FAIXAS_DA_FILA and posicao < capacidade:
            posicao += 1
            item.posicao_fila = posicao
    return ordenados
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam.
Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 5: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): sinais, score com regra de 2 dimensões, recomendação e priorização" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Orquestração da análise (AnaliseService) e POST /api/analise/executar

**Files:**
- Create: `backend/app/repositories/cliente_repository.py`, `atendimento_repository.py`, `nps_repository.py`, `execucao_repository.py`
- Create: `backend/app/services/analise_service.py`, `backend/app/schemas/analise.py`, `backend/app/controllers/analise_controller.py`, `backend/scripts/rodar_analise.py`
- Modify: `backend/app/services/fabrica.py`, `backend/app/dependencies.py`, `backend/app/main.py`, `backend/app/schemas/importacao.py`, `backend/app/controllers/importacao_controller.py`, `backend/scripts/importar_base.py`, `backend/tests/conftest.py`
- Test: `backend/tests/integration/test_analise.py`, `backend/tests/integration/test_analise_api.py`, modify `backend/tests/integration/test_scripts.py`

**Interfaces:**
- Consumes: `calcular_indicadores` (Task 6); `DefinicaoSinal`, `avaliar_sinais`, `LimiaresFaixa`, `calcular_score`, `ResultadoScore`, `recomendar`, `ItemAvaliado`, `priorizar` (Task 7); `SinalRepository`, `AcaoRepository`, `criar_importacao_service` (Task 5); `RecursoNaoEncontradoError` (Task 3).
- Produces: `ClienteRepository(session)` com `listar_todos() -> list[Cliente]` (situação carregada) e `obter(cliente_id) -> Cliente | None`; `AtendimentoRepository(session)` com `listar_todos()`, `listar_por_cliente(cliente_id)`, `ultimo_mes() -> date | None`; `NpsRepository(session)` com `listar_todos()`, `listar_por_cliente(cliente_id)`; `ExecucaoRepository(session)` com `gravar(execucao) -> ExecucaoAnalise` e `ultima_producao() -> ExecucaoAnalise | None`; `AnaliseService.executar(mes_referencia: date | None = None, usuario_id: int | None = None) -> ExecucaoAnalise`; `ExecucaoResponse(id, tipo, mes_referencia, versao_modelo, executado_em, qtd_clientes_avaliados, qtd_na_fila)`; `RelatorioImportacaoResponse.execucao: ExecucaoResponse | None`; `fabrica.criar_analise_service(session, settings)`; dependência `get_analise_service`; `POST /api/analise/executar`; fixture pytest **`client_com_base`** (TestClient já com a base real importada e analisada).

- [ ] **Step 1: Escrever os testes que falham**

Acrescente ao `backend/tests/conftest.py`:
```python
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
```

`backend/tests/integration/test_analise.py`:
```python
from datetime import date

import pytest

from app.core.enums import FaixaRisco
from app.core.exceptions import RecursoNaoEncontradoError
from app.services.fabrica import criar_analise_service, criar_importacao_service

ORDEM = {FaixaRisco.CRITICO: 0, FaixaRisco.ATENCAO: 1}


@pytest.fixture
def base_importada(db_session, settings, caminho_xlsx):
    criar_importacao_service(db_session, settings).importar(caminho_xlsx)


def test_avalia_todos_os_ativos_no_ultimo_mes(base_importada, db_session, settings):
    execucao = criar_analise_service(db_session, settings).executar()

    assert execucao.id is not None
    assert execucao.mes_referencia == date(2026, 6, 1)
    assert execucao.qtd_clientes_avaliados == 58
    assert len(execucao.avaliacoes) == 58


def test_fila_nao_vazia_ordenada_e_com_evidencias(base_importada, db_session, settings):
    execucao = criar_analise_service(db_session, settings).executar()

    fila = sorted(
        (a for a in execucao.avaliacoes if a.posicao_fila is not None),
        key=lambda a: a.posicao_fila,
    )
    assert 1 <= len(fila) <= settings.capacidade_fila
    assert [a.posicao_fila for a in fila] == list(range(1, len(fila) + 1))
    chaves = [(ORDEM[a.faixa], -float(a.receita_em_risco)) for a in fila]
    assert chaves == sorted(chaves)
    for avaliacao in fila:
        assert avaliacao.qtd_dimensoes_afetadas >= 2
        assert avaliacao.acao_recomendada_id is not None
        assert avaliacao.evidencias
        assert all(e.texto and "{" not in e.texto for e in avaliacao.evidencias)
        contribuicoes = [float(e.contribuicao) for e in avaliacao.evidencias]
        assert contribuicoes == sorted(contribuicoes, reverse=True)


def test_fora_da_fila_nao_tem_posicao(base_importada, db_session, settings):
    execucao = criar_analise_service(db_session, settings).executar()

    for avaliacao in execucao.avaliacoes:
        if avaliacao.faixa in (FaixaRisco.MONITORAR, FaixaRisco.SAUDAVEL):
            assert avaliacao.posicao_fila is None


def test_capacidade_da_fila_vem_das_settings(base_importada, db_session, settings):
    execucao = criar_analise_service(
        db_session, settings.model_copy(update={"capacidade_fila": 1})
    ).executar()

    assert execucao.qtd_na_fila == 1


def test_mes_de_referencia_explicito(base_importada, db_session, settings):
    execucao = criar_analise_service(db_session, settings).executar(date(2025, 12, 1))

    assert execucao.mes_referencia == date(2025, 12, 1)
    assert all(a.mes_referencia == date(2025, 12, 1) for a in execucao.avaliacoes)


def test_sem_dados_importados_gera_erro_claro(db_session, settings):
    with pytest.raises(RecursoNaoEncontradoError, match="Importe"):
        criar_analise_service(db_session, settings).executar()
```

`backend/tests/integration/test_analise_api.py`:
```python
def test_executar_exige_autenticacao(client):
    assert client.post("/api/analise/executar").status_code == 401


def test_executar_sem_base_retorna_404(client, auth_headers):
    resposta = client.post("/api/analise/executar", headers=auth_headers)

    assert resposta.status_code == 404
    assert "Importe" in resposta.json()["detail"]


def test_importacao_ja_roda_a_analise(client, auth_headers, caminho_xlsx):
    resposta = client.post(
        "/api/importacao",
        headers=auth_headers,
        files={"arquivo": ("base.xlsx", caminho_xlsx.read_bytes())},
    )

    execucao = resposta.json()["execucao"]
    assert execucao["qtd_clientes_avaliados"] == 58
    assert execucao["mes_referencia"] == "2026-06-01"
    assert execucao["qtd_na_fila"] >= 1


def test_executar_com_base(client_com_base, auth_headers):
    resposta = client_com_base.post("/api/analise/executar", headers=auth_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo"] == "PRODUCAO"
    assert corpo["versao_modelo"] == "mvp-regras-1"
    assert corpo["qtd_clientes_avaliados"] == 58
```

Em `backend/tests/integration/test_scripts.py`, acrescente o import `from scripts import rodar_analise` e o teste:
```python
def test_scripts_importar_e_rodar_analise(banco_arquivo, caminho_xlsx, capsys):
    assert importar_base.main([str(caminho_xlsx)]) == 0
    assert rodar_analise.main([]) == 0

    engine = create_engine(banco_arquivo)
    with engine.connect() as conexao:
        execucoes = conexao.execute(text("SELECT COUNT(*) FROM execucoes_analise")).scalar()
    engine.dispose()
    assert execucoes == 2
    saida = capsys.readouterr().out
    assert "Análise concluída" in saida
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/integration/test_analise.py tests/integration/test_analise_api.py tests/integration/test_scripts.py -v`
Expected: FAIL/ERROR (`ImportError: cannot import name 'criar_analise_service'`).

- [ ] **Step 3: Implementar repositories**

`backend/app/repositories/cliente_repository.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Cliente


class ClienteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_todos(self) -> list[Cliente]:
        consulta = (
            select(Cliente).options(selectinload(Cliente.situacao)).order_by(Cliente.cliente_id)
        )
        return list(self._session.scalars(consulta))

    def obter(self, cliente_id: str) -> Cliente | None:
        consulta = (
            select(Cliente)
            .options(selectinload(Cliente.situacao))
            .where(Cliente.cliente_id == cliente_id)
        )
        return self._session.scalar(consulta)
```

`backend/app/repositories/atendimento_repository.py`:
```python
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AtendimentoMensal


class AtendimentoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_todos(self) -> list[AtendimentoMensal]:
        consulta = select(AtendimentoMensal).order_by(
            AtendimentoMensal.cliente_id, AtendimentoMensal.mes_ref
        )
        return list(self._session.scalars(consulta))

    def listar_por_cliente(self, cliente_id: str) -> list[AtendimentoMensal]:
        consulta = (
            select(AtendimentoMensal)
            .where(AtendimentoMensal.cliente_id == cliente_id)
            .order_by(AtendimentoMensal.mes_ref)
        )
        return list(self._session.scalars(consulta))

    def ultimo_mes(self) -> date | None:
        return self._session.scalar(select(func.max(AtendimentoMensal.mes_ref)))
```

`backend/app/repositories/nps_repository.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PesquisaNps


class NpsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_todos(self) -> list[PesquisaNps]:
        consulta = select(PesquisaNps).order_by(PesquisaNps.cliente_id, PesquisaNps.mes_ref)
        return list(self._session.scalars(consulta))

    def listar_por_cliente(self, cliente_id: str) -> list[PesquisaNps]:
        consulta = (
            select(PesquisaNps)
            .where(PesquisaNps.cliente_id == cliente_id)
            .order_by(PesquisaNps.mes_ref)
        )
        return list(self._session.scalars(consulta))
```

`backend/app/repositories/execucao_repository.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import TipoExecucao
from app.models import ExecucaoAnalise


class ExecucaoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def gravar(self, execucao: ExecucaoAnalise) -> ExecucaoAnalise:
        """Grava a execução com avaliações e evidências em uma única transação."""
        try:
            self._session.add(execucao)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return execucao

    def ultima_producao(self) -> ExecucaoAnalise | None:
        consulta = (
            select(ExecucaoAnalise)
            .where(ExecucaoAnalise.tipo == TipoExecucao.PRODUCAO)
            .order_by(ExecucaoAnalise.executado_em.desc(), ExecucaoAnalise.id.desc())
            .limit(1)
        )
        return self._session.scalar(consulta)
```

- [ ] **Step 4: Implementar AnaliseService**

`backend/app/services/analise_service.py`:
```python
"""Análise de produção: indicadores → sinais → score → recomendação → fila → grava.

Regras: só clientes ATIVOS são avaliados; o mês de referência padrão é o último
mês da base; tudo é gravado em uma transação; dashboard e fila leem sempre a
última execução PRODUCAO.
"""

import json
import logging
import time
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from app.core.config import Settings
from app.core.enums import SituacaoCliente, TipoExecucao
from app.core.exceptions import RecursoNaoEncontradoError
from app.models import (
    AcaoRecomendada,
    AvaliacaoRisco,
    Cliente,
    ConfiguracaoSinal,
    EvidenciaRisco,
    ExecucaoAnalise,
)
from app.repositories.acao_repository import AcaoRepository
from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.execucao_repository import ExecucaoRepository
from app.repositories.nps_repository import NpsRepository
from app.repositories.sinal_repository import SinalRepository
from app.services.risco.indicadores import calcular_indicadores
from app.services.risco.priorizacao import ItemAvaliado, priorizar
from app.services.risco.recomendacao import recomendar
from app.services.risco.score import LimiaresFaixa, ResultadoScore, calcular_score
from app.services.risco.sinais import DefinicaoSinal, avaliar_sinais

logger = logging.getLogger(__name__)

COLUNAS_ATENDIMENTO = (
    "chamados_abertos",
    "chamados_criticos",
    "chamados_reabertos",
    "chamados_dentro_sla",
    "pct_sla_cumprido",
    "tempo_medio_resolucao_h",
    "reclamacoes_formais",
    "uso_plataforma_pct",
    "dias_atraso_pagamento",
    "reunioes_previstas",
    "reunioes_realizadas",
)


def _num(valor: Any) -> float | None:
    return None if valor is None else float(valor)


def _dec(valor: float, casas: int) -> Decimal:
    return Decimal(f"{valor:.{casas}f}")


def _dec_opcional(valor: float | None, casas: int) -> Decimal | None:
    return None if valor is None else _dec(valor, casas)


class AnaliseService:
    VERSAO_MODELO = "mvp-regras-1"

    def __init__(
        self,
        clientes: ClienteRepository,
        atendimentos: AtendimentoRepository,
        nps: NpsRepository,
        sinais: SinalRepository,
        acoes: AcaoRepository,
        execucoes: ExecucaoRepository,
        settings: Settings,
    ) -> None:
        self._clientes = clientes
        self._atendimentos = atendimentos
        self._nps = nps
        self._sinais = sinais
        self._acoes = acoes
        self._execucoes = execucoes
        self._settings = settings

    def executar(
        self, mes_referencia: date | None = None, usuario_id: int | None = None
    ) -> ExecucaoAnalise:
        inicio = time.perf_counter()
        mes = mes_referencia or self._atendimentos.ultimo_mes()
        if mes is None:
            raise RecursoNaoEncontradoError(
                "Não há dados para analisar. Importe a planilha primeiro."
            )
        clientes = self._clientes.listar_todos()
        ativos = [
            c
            for c in clientes
            if c.situacao is not None and c.situacao.situacao == SituacaoCliente.ATIVO
        ]
        indicadores = calcular_indicadores(
            self._df_atendimentos(), self._df_pesquisas(), self._df_clientes(clientes), mes
        )
        por_cliente = self._agrupar(indicadores)
        definicoes = [self._definicao(sinal) for sinal in self._sinais.listar_ativos()]
        limiares = LimiaresFaixa(
            critico=self._settings.limiar_critico,
            atencao=self._settings.limiar_atencao,
            monitorar=self._settings.limiar_monitorar,
        )

        resultados: dict[str, ResultadoScore] = {}
        itens: list[ItemAvaliado] = []
        for cliente in ativos:
            disparos = avaliar_sinais(definicoes, por_cliente.get(cliente.cliente_id, {}))
            resultado = calcular_score(disparos, limiares)
            resultados[cliente.cliente_id] = resultado
            itens.append(
                ItemAvaliado(
                    cliente_id=cliente.cliente_id,
                    valor_mensal=float(cliente.valor_mensal),
                    score=resultado.score,
                    faixa=resultado.faixa,
                )
            )
        priorizados = priorizar(itens, self._settings.capacidade_fila)

        acoes = self._acoes.mapa_por_codigo()
        execucao = ExecucaoAnalise(
            tipo=TipoExecucao.PRODUCAO,
            mes_referencia=mes,
            versao_modelo=self.VERSAO_MODELO,
            parametros_json=json.dumps(
                {
                    "capacidade_fila": self._settings.capacidade_fila,
                    "limiares": {
                        "critico": limiares.critico,
                        "atencao": limiares.atencao,
                        "monitorar": limiares.monitorar,
                    },
                    "sinais_ativos": [d.codigo for d in definicoes],
                }
            ),
            executado_por_usuario_id=usuario_id,
            qtd_clientes_avaliados=len(itens),
        )
        for item in priorizados:
            execucao.avaliacoes.append(
                self._avaliacao(item, resultados[item.cliente_id], mes, acoes)
            )
        self._execucoes.gravar(execucao)
        logger.info(
            "Análise %s concluída: mes=%s clientes=%d fila=%d tempo=%.2fs",
            self.VERSAO_MODELO,
            mes,
            len(itens),
            execucao.qtd_na_fila,
            time.perf_counter() - inicio,
        )
        return execucao

    def _df_atendimentos(self) -> pd.DataFrame:
        linhas = [
            {
                "cliente_id": a.cliente_id,
                "mes_ref": a.mes_ref,
                **{coluna: _num(getattr(a, coluna)) for coluna in COLUNAS_ATENDIMENTO},
            }
            for a in self._atendimentos.listar_todos()
        ]
        return pd.DataFrame(linhas, columns=["cliente_id", "mes_ref", *COLUNAS_ATENDIMENTO])

    def _df_pesquisas(self) -> pd.DataFrame:
        linhas = [
            {
                "cliente_id": p.cliente_id,
                "mes_ref": p.mes_ref,
                "respondeu": bool(p.respondeu),
                "nota_nps": _num(p.nota_nps),
            }
            for p in self._nps.listar_todos()
        ]
        return pd.DataFrame(linhas, columns=["cliente_id", "mes_ref", "respondeu", "nota_nps"])

    @staticmethod
    def _df_clientes(clientes: list[Cliente]) -> pd.DataFrame:
        return pd.DataFrame(
            [{"cliente_id": c.cliente_id, "sla_contratado_h": c.sla_contratado_h} for c in clientes],
            columns=["cliente_id", "sla_contratado_h"],
        )

    @staticmethod
    def _agrupar(indicadores: pd.DataFrame) -> dict[str, dict[str, dict[str, Any]]]:
        por_cliente: dict[str, dict[str, dict[str, Any]]] = {}
        for linha in indicadores.to_dict("records"):
            por_cliente.setdefault(linha["cliente_id"], {})[linha["variavel"]] = linha
        return por_cliente

    @staticmethod
    def _definicao(sinal: ConfiguracaoSinal) -> DefinicaoSinal:
        return DefinicaoSinal(
            id=sinal.id,
            codigo=sinal.codigo,
            dimensao=sinal.dimensao,
            variavel=sinal.variavel,
            tipo_regra=sinal.tipo_regra,
            sentido_piora=sinal.sentido_piora,
            limiar=float(sinal.limiar),
            persistencia_min_meses=sinal.persistencia_min_meses,
            peso=float(sinal.peso),
            template_evidencia=sinal.template_evidencia,
            metrica=sinal.metrica,
        )

    @staticmethod
    def _avaliacao(
        item: ItemAvaliado,
        resultado: ResultadoScore,
        mes: date,
        acoes: dict[str, AcaoRecomendada],
    ) -> AvaliacaoRisco:
        codigo_acao = recomendar(resultado.evidencias)
        acao = acoes.get(codigo_acao) if codigo_acao else None
        avaliacao = AvaliacaoRisco(
            cliente_id=item.cliente_id,
            mes_referencia=mes,
            score_risco=_dec(item.score, 4),
            faixa=item.faixa,
            qtd_dimensoes_afetadas=resultado.qtd_dimensoes_afetadas,
            receita_em_risco=_dec(item.receita_em_risco, 2),
            posicao_fila=item.posicao_fila,
            acao_recomendada_id=acao.id if acao else None,
        )
        avaliacao.evidencias = [
            EvidenciaRisco(
                configuracao_sinal_id=e.disparo.sinal.id,
                dimensao=e.disparo.sinal.dimensao,
                valor_observado=_dec(e.disparo.valor_observado, 4),
                linha_base=_dec_opcional(e.disparo.linha_base, 4),
                variacao_pct=_dec_opcional(e.disparo.variacao_pct, 4),
                meses_persistencia=e.disparo.meses_persistencia,
                contribuicao=_dec(e.contribuicao, 4),
                texto=e.disparo.texto[:300],
            )
            for e in resultado.evidencias
        ]
        return avaliacao
```

- [ ] **Step 5: Fábrica, schema, controller, importação e scripts**

Acrescente em `backend/app/services/fabrica.py`:
```python
from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.execucao_repository import ExecucaoRepository
from app.repositories.nps_repository import NpsRepository
from app.services.analise_service import AnaliseService


def criar_analise_service(session: Session, settings: Settings) -> AnaliseService:
    return AnaliseService(
        ClienteRepository(session),
        AtendimentoRepository(session),
        NpsRepository(session),
        SinalRepository(session),
        AcaoRepository(session),
        ExecucaoRepository(session),
        settings,
    )
```

`backend/app/schemas/analise.py`:
```python
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import TipoExecucao


class ExecucaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoExecucao
    mes_referencia: date
    versao_modelo: str
    executado_em: datetime
    qtd_clientes_avaliados: int
    qtd_na_fila: int
```

Em `backend/app/schemas/importacao.py`, importe `ExecucaoResponse` e acrescente o campo `execucao: ExecucaoResponse | None = None` em `RelatorioImportacaoResponse`.

Acrescente em `backend/app/dependencies.py`:
```python
from app.services.analise_service import AnaliseService
from app.services.fabrica import criar_analise_service


def get_analise_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)
) -> AnaliseService:
    return criar_analise_service(db, settings)
```

`backend/app/controllers/analise_controller.py`:
```python
from fastapi import APIRouter, Depends

from app.dependencies import get_analise_service, get_usuario_atual
from app.models import ExecucaoAnalise, Usuario
from app.schemas.analise import ExecucaoResponse
from app.services.analise_service import AnaliseService

router = APIRouter(prefix="/analise", tags=["analise"])


@router.post("/executar", response_model=ExecucaoResponse)
def executar(
    usuario: Usuario = Depends(get_usuario_atual),
    analise: AnaliseService = Depends(get_analise_service),
) -> ExecucaoAnalise:
    return analise.executar(usuario_id=usuario.id)
```

Substitua `backend/app/controllers/importacao_controller.py` por:
```python
from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_analise_service, get_importacao_service, get_usuario_atual
from app.models import Usuario
from app.schemas.analise import ExecucaoResponse
from app.schemas.importacao import RelatorioImportacaoResponse
from app.services.analise_service import AnaliseService
from app.services.importacao_service import ImportacaoService

router = APIRouter(tags=["importacao"])


@router.post("/importacao", response_model=RelatorioImportacaoResponse)
def importar(
    arquivo: UploadFile = File(..., description="Planilha INOVAAPPS (.xlsx)"),
    usuario: Usuario = Depends(get_usuario_atual),
    importacao: ImportacaoService = Depends(get_importacao_service),
    analise: AnaliseService = Depends(get_analise_service),
) -> RelatorioImportacaoResponse:
    """Importa a planilha (substitui os dados de origem) e roda a análise de produção."""
    relatorio = importacao.importar(arquivo.file.read())
    execucao = analise.executar(usuario_id=usuario.id)
    return RelatorioImportacaoResponse(
        contagens=relatorio.contagens,
        avisos=relatorio.avisos,
        execucao=ExecucaoResponse.model_validate(execucao),
    )
```

Em `backend/app/main.py`, inclua `analise_controller.router` com `prefix="/api"`.

Em `backend/scripts/importar_base.py`, importe `criar_analise_service` e, dentro do `with Session(...)`, logo após imprimir os avisos, rode a análise e imprima o resumo:
```python
            execucao = criar_analise_service(session, settings).executar()
            print(
                f"Análise concluída: mês {execucao.mes_referencia}, "
                f"{execucao.qtd_clientes_avaliados} clientes avaliados, "
                f"{execucao.qtd_na_fila} na fila."
            )
```

`backend/scripts/rodar_analise.py`:
```python
"""Roda a análise de produção sobre os dados já importados.

Uso (a partir de backend/):  python -m scripts.rodar_analise [AAAA-MM]
"""

import sys
from datetime import date

from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, criar_engine
from app.services.fabrica import criar_analise_service


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mes = None
    if argv:
        ano, mes_num = argv[0].split("-")
        mes = date(int(ano), int(mes_num), 1)
    settings = get_settings()
    engine = criar_engine(settings.database_url)
    Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False) as session:
            execucao = criar_analise_service(session, settings).executar(mes)
            print(
                f"Análise concluída: mês {execucao.mes_referencia}, "
                f"{execucao.qtd_clientes_avaliados} clientes avaliados, "
                f"{execucao.qtd_na_fila} na fila."
            )
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam (os testes que usam a base real levam alguns segundos).
Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 7: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): análise de produção com fila priorizada e POST /api/analise/executar" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Endpoints do dashboard, sinais e ações

**Files:**
- Create: `backend/app/repositories/avaliacao_repository.py`
- Create: `backend/app/schemas/risco.py`, `backend/app/schemas/dashboard.py`, `backend/app/schemas/catalogo.py`
- Create: `backend/app/services/mapeadores.py`, `backend/app/services/dashboard_service.py`
- Create: `backend/app/controllers/dashboard_controller.py`, `backend/app/controllers/catalogo_controller.py`
- Modify: `backend/app/dependencies.py`, `backend/app/main.py` (routers + seed do catálogo no startup)
- Test: `backend/tests/integration/test_dashboard.py`, `backend/tests/integration/test_catalogo.py`

**Interfaces:**
- Consumes: `ExecucaoRepository` (Task 8), `CatalogoService`, `get_catalogo_service`, `criar_catalogo_service` (Task 5), fixtures `client_com_base`, `auth_headers`, `caminho_xlsx`.
- Produces: `AvaliacaoRepository(session)` com `listar_por_execucao(execucao_id)`, `fila(execucao_id, limite)`, `obter_por_cliente(execucao_id, cliente_id)` (todas carregando cliente, ação e evidências+sinal); schemas `AcaoResumo(codigo, titulo, responsavel, prazo_dias)`, `AcaoDetalhe(+descricao)`, `EvidenciaResponse(codigo_sinal, dimensao, texto, valor_observado, linha_base, variacao_pct, meses_persistencia, contribuicao)`, `AvaliacaoRiscoResponse(mes_referencia, score_risco, faixa, qtd_dimensoes_afetadas, receita_em_risco, posicao_fila, evidencias, acao_recomendada: AcaoDetalhe | None)`, `ResumoDashboard`, `ItemFila`, `SinalResponse`, `AcaoResponse`; `mapeadores.acao_resumo`, `acao_detalhe`, `evidencia_response`, `avaliacao_response`, `item_fila`; `DashboardService(execucoes, avaliacoes).resumo()` / `.fila(limite)`; `GET /api/dashboard/resumo`, `GET /api/dashboard/fila`, `GET /api/sinais`, `GET /api/acoes-recomendadas`.

- [ ] **Step 1: Escrever os testes que falham**

`backend/tests/integration/test_dashboard.py`:
```python
import pandas as pd
import pytest

CHAVES_ITEM_FILA = {
    "posicao",
    "cliente_id",
    "segmento",
    "plano",
    "porte",
    "valor_mensal",
    "score_risco",
    "faixa",
    "receita_em_risco",
    "qtd_dimensoes_afetadas",
    "principais_motivos",
    "acao_recomendada",
    "ultimo_contato",
}


@pytest.mark.parametrize("rota", ["/api/dashboard/resumo", "/api/dashboard/fila"])
def test_dashboard_exige_autenticacao(client, rota):
    assert client.get(rota).status_code == 401


def test_dashboard_sem_analise_responde_vazio(client, auth_headers):
    resumo = client.get("/api/dashboard/resumo", headers=auth_headers)
    fila = client.get("/api/dashboard/fila", headers=auth_headers)

    assert resumo.status_code == 200
    corpo = resumo.json()
    assert corpo["mes_referencia"] is None
    assert corpo["clientes_ativos"] == 0
    assert corpo["receita_em_risco"] == 0
    assert corpo["por_faixa"] == {"CRITICO": 0, "ATENCAO": 0, "MONITORAR": 0, "SAUDAVEL": 0}
    assert fila.status_code == 200 and fila.json() == []


def test_resumo_com_base(client_com_base, auth_headers, caminho_xlsx):
    corpo = client_com_base.get("/api/dashboard/resumo", headers=auth_headers).json()

    clientes = pd.read_excel(caminho_xlsx, sheet_name="clientes")
    situacao = pd.read_excel(caminho_xlsx, sheet_name="situacao_clientes")
    ativos = situacao.loc[situacao["situacao"] == "Ativo", "cliente_id"]
    receita_ativa = float(clientes[clientes["cliente_id"].isin(ativos)]["valor_mensal"].sum())

    assert corpo["mes_referencia"] == "2026-06-01"
    assert corpo["clientes_ativos"] == 58
    assert corpo["receita_ativa"] == pytest.approx(receita_ativa)
    assert 0 < corpo["receita_em_risco"] < corpo["receita_ativa"]
    assert sum(corpo["por_faixa"].values()) == 58
    assert set(corpo["por_dimensao"]) == {"ATENDIMENTO", "SLA", "ENGAJAMENTO", "FINANCEIRO", "SATISFACAO"}
    assert corpo["qtd_na_fila"] == corpo["por_faixa"]["CRITICO"] + corpo["por_faixa"]["ATENCAO"]


def test_fila_no_formato_do_contrato(client_com_base, auth_headers):
    fila = client_com_base.get("/api/dashboard/fila", headers=auth_headers).json()

    assert fila
    assert [item["posicao"] for item in fila] == list(range(1, len(fila) + 1))
    for item in fila:
        assert set(item) == CHAVES_ITEM_FILA
        assert item["faixa"] in ("CRITICO", "ATENCAO")
        assert isinstance(item["valor_mensal"], float)
        assert 1 <= len(item["principais_motivos"]) <= 3
        assert set(item["acao_recomendada"]) == {"codigo", "titulo", "responsavel", "prazo_dias"}
        assert item["ultimo_contato"] is None


def test_fila_respeita_limite(client_com_base, auth_headers):
    assert len(client_com_base.get("/api/dashboard/fila?limite=1", headers=auth_headers).json()) == 1
    assert client_com_base.get("/api/dashboard/fila?limite=0", headers=auth_headers).status_code == 422
```

`backend/tests/integration/test_catalogo.py`:
```python
import pytest


@pytest.mark.parametrize("rota", ["/api/sinais", "/api/acoes-recomendadas"])
def test_catalogo_exige_autenticacao(client, rota):
    assert client.get(rota).status_code == 401


def test_sinais_disponiveis_desde_o_startup(client, auth_headers):
    sinais = client.get("/api/sinais", headers=auth_headers).json()

    assert len(sinais) == 10
    reclamacoes = next(s for s in sinais if s["codigo"] == "RECLAMACOES")
    assert reclamacoes["metrica"] == "soma_3m"
    assert reclamacoes["peso"] == pytest.approx(0.1)
    assert reclamacoes["lift"] is None
    assert reclamacoes["ativo"] is True


def test_acoes_em_ordem_do_playbook(client, auth_headers):
    acoes = client.get("/api/acoes-recomendadas", headers=auth_headers).json()

    assert [a["codigo"] for a in acoes][:2] == ["COMITE_RETENCAO", "CONTATO_EXECUTIVO"]
    assert len(acoes) == 6
    assert set(acoes[0]) == {
        "codigo",
        "titulo",
        "descricao",
        "dimensao_gatilho",
        "responsavel_sugerido",
        "prazo_dias",
        "ordem",
    }
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/integration/test_dashboard.py tests/integration/test_catalogo.py -v`
Expected: FAIL (404 nas rotas novas).

- [ ] **Step 3: Implementar repository, schemas e mapeadores**

`backend/app/repositories/avaliacao_repository.py`:
```python
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import AvaliacaoRisco, EvidenciaRisco


class AvaliacaoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _consulta(execucao_id: int) -> Select[tuple[AvaliacaoRisco]]:
        return (
            select(AvaliacaoRisco)
            .where(AvaliacaoRisco.execucao_id == execucao_id)
            .options(
                selectinload(AvaliacaoRisco.cliente),
                selectinload(AvaliacaoRisco.acao_recomendada),
                selectinload(AvaliacaoRisco.evidencias).selectinload(EvidenciaRisco.sinal),
            )
        )

    def listar_por_execucao(self, execucao_id: int) -> list[AvaliacaoRisco]:
        return list(self._session.scalars(self._consulta(execucao_id)))

    def fila(self, execucao_id: int, limite: int) -> list[AvaliacaoRisco]:
        consulta = (
            self._consulta(execucao_id)
            .where(AvaliacaoRisco.posicao_fila.is_not(None))
            .order_by(AvaliacaoRisco.posicao_fila)
            .limit(limite)
        )
        return list(self._session.scalars(consulta))

    def obter_por_cliente(self, execucao_id: int, cliente_id: str) -> AvaliacaoRisco | None:
        consulta = self._consulta(execucao_id).where(AvaliacaoRisco.cliente_id == cliente_id)
        return self._session.scalar(consulta)
```

`backend/app/schemas/risco.py`:
```python
from datetime import date

from pydantic import BaseModel

from app.core.enums import Dimensao, FaixaRisco, Responsavel


class AcaoResumo(BaseModel):
    codigo: str
    titulo: str
    responsavel: Responsavel
    prazo_dias: int


class AcaoDetalhe(AcaoResumo):
    descricao: str


class EvidenciaResponse(BaseModel):
    codigo_sinal: str
    dimensao: Dimensao
    texto: str
    valor_observado: float
    linha_base: float | None
    variacao_pct: float | None
    meses_persistencia: int
    contribuicao: float


class AvaliacaoRiscoResponse(BaseModel):
    mes_referencia: date
    score_risco: float
    faixa: FaixaRisco
    qtd_dimensoes_afetadas: int
    receita_em_risco: float
    posicao_fila: int | None
    evidencias: list[EvidenciaResponse]
    acao_recomendada: AcaoDetalhe | None
```

`backend/app/schemas/dashboard.py`:
```python
from datetime import date, datetime

from pydantic import BaseModel

from app.core.enums import Dimensao, FaixaRisco, Plano, Porte
from app.schemas.risco import AcaoResumo


class ResumoDashboard(BaseModel):
    mes_referencia: date | None
    executado_em: datetime | None
    clientes_ativos: int
    receita_ativa: float
    receita_em_risco: float
    qtd_na_fila: int
    por_faixa: dict[FaixaRisco, int]
    por_dimensao: dict[Dimensao, int]


class ItemFila(BaseModel):
    posicao: int
    cliente_id: str
    segmento: str
    plano: Plano
    porte: Porte
    valor_mensal: float
    score_risco: float
    faixa: FaixaRisco
    receita_em_risco: float
    qtd_dimensoes_afetadas: int
    principais_motivos: list[str]
    acao_recomendada: AcaoResumo | None
    ultimo_contato: None = None
```

`backend/app/schemas/catalogo.py`:
```python
from pydantic import BaseModel, ConfigDict

from app.core.enums import Dimensao, Responsavel, SentidoPiora, TipoRegra


class SinalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    dimensao: Dimensao
    variavel: str
    tipo_regra: TipoRegra
    sentido_piora: SentidoPiora
    limiar: float
    metrica: str
    persistencia_min_meses: int
    peso: float
    lift: float | None
    cobertura_cancelados: float | None
    taxa_falso_alarme: float | None
    antecedencia_media_meses: float | None
    ativo: bool


class AcaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    titulo: str
    descricao: str
    dimensao_gatilho: Dimensao | None
    responsavel_sugerido: Responsavel
    prazo_dias: int
    ordem: int
```

`backend/app/services/mapeadores.py`:
```python
"""Conversão de models para os schemas de resposta (a "View")."""

from app.models import AcaoRecomendada, AvaliacaoRisco, EvidenciaRisco
from app.schemas.dashboard import ItemFila
from app.schemas.risco import AcaoDetalhe, AcaoResumo, AvaliacaoRiscoResponse, EvidenciaResponse

QTD_MOTIVOS = 3


def _opcional(valor: object) -> float | None:
    return None if valor is None else float(valor)  # type: ignore[arg-type]


def acao_resumo(acao: AcaoRecomendada | None) -> AcaoResumo | None:
    if acao is None:
        return None
    return AcaoResumo(
        codigo=acao.codigo,
        titulo=acao.titulo,
        responsavel=acao.responsavel_sugerido,
        prazo_dias=acao.prazo_dias,
    )


def acao_detalhe(acao: AcaoRecomendada | None) -> AcaoDetalhe | None:
    if acao is None:
        return None
    return AcaoDetalhe(
        codigo=acao.codigo,
        titulo=acao.titulo,
        responsavel=acao.responsavel_sugerido,
        prazo_dias=acao.prazo_dias,
        descricao=acao.descricao,
    )


def evidencia_response(evidencia: EvidenciaRisco) -> EvidenciaResponse:
    return EvidenciaResponse(
        codigo_sinal=evidencia.sinal.codigo,
        dimensao=evidencia.dimensao,
        texto=evidencia.texto,
        valor_observado=float(evidencia.valor_observado),
        linha_base=_opcional(evidencia.linha_base),
        variacao_pct=_opcional(evidencia.variacao_pct),
        meses_persistencia=evidencia.meses_persistencia,
        contribuicao=float(evidencia.contribuicao),
    )


def avaliacao_response(avaliacao: AvaliacaoRisco) -> AvaliacaoRiscoResponse:
    return AvaliacaoRiscoResponse(
        mes_referencia=avaliacao.mes_referencia,
        score_risco=float(avaliacao.score_risco),
        faixa=avaliacao.faixa,
        qtd_dimensoes_afetadas=avaliacao.qtd_dimensoes_afetadas,
        receita_em_risco=float(avaliacao.receita_em_risco),
        posicao_fila=avaliacao.posicao_fila,
        evidencias=[evidencia_response(e) for e in avaliacao.evidencias],
        acao_recomendada=acao_detalhe(avaliacao.acao_recomendada),
    )


def item_fila(avaliacao: AvaliacaoRisco) -> ItemFila:
    cliente = avaliacao.cliente
    return ItemFila(
        posicao=avaliacao.posicao_fila or 0,
        cliente_id=cliente.cliente_id,
        segmento=cliente.segmento,
        plano=cliente.plano,
        porte=cliente.porte,
        valor_mensal=float(cliente.valor_mensal),
        score_risco=float(avaliacao.score_risco),
        faixa=avaliacao.faixa,
        receita_em_risco=float(avaliacao.receita_em_risco),
        qtd_dimensoes_afetadas=avaliacao.qtd_dimensoes_afetadas,
        principais_motivos=[e.texto for e in avaliacao.evidencias[:QTD_MOTIVOS]],
        acao_recomendada=acao_resumo(avaliacao.acao_recomendada),
    )
```

- [ ] **Step 4: Implementar DashboardService, controllers e seed no startup**

`backend/app/services/dashboard_service.py`:
```python
from collections import Counter

from app.core.enums import Dimensao, FaixaRisco
from app.repositories.avaliacao_repository import AvaliacaoRepository
from app.repositories.execucao_repository import ExecucaoRepository
from app.schemas.dashboard import ItemFila, ResumoDashboard
from app.services.mapeadores import item_fila

FAIXAS_EM_RISCO = (FaixaRisco.CRITICO, FaixaRisco.ATENCAO)


class DashboardService:
    """Resumo e fila, sempre a partir da última execução de produção.

    Receita em risco do resumo = soma da receita em risco dos clientes em
    CRITICO ou ATENCAO. Por dimensão = quantos clientes têm ao menos um sinal
    disparado naquela dimensão.
    """

    def __init__(self, execucoes: ExecucaoRepository, avaliacoes: AvaliacaoRepository) -> None:
        self._execucoes = execucoes
        self._avaliacoes = avaliacoes

    def resumo(self) -> ResumoDashboard:
        execucao = self._execucoes.ultima_producao()
        if execucao is None:
            return ResumoDashboard(
                mes_referencia=None,
                executado_em=None,
                clientes_ativos=0,
                receita_ativa=0.0,
                receita_em_risco=0.0,
                qtd_na_fila=0,
                por_faixa=dict.fromkeys(FaixaRisco, 0),
                por_dimensao=dict.fromkeys(Dimensao, 0),
            )
        avaliacoes = self._avaliacoes.listar_por_execucao(execucao.id)
        por_faixa = Counter(a.faixa for a in avaliacoes)
        por_dimensao: Counter[Dimensao] = Counter()
        for avaliacao in avaliacoes:
            por_dimensao.update({e.dimensao for e in avaliacao.evidencias})
        return ResumoDashboard(
            mes_referencia=execucao.mes_referencia,
            executado_em=execucao.executado_em,
            clientes_ativos=len(avaliacoes),
            receita_ativa=round(sum(float(a.cliente.valor_mensal) for a in avaliacoes), 2),
            receita_em_risco=round(
                sum(float(a.receita_em_risco) for a in avaliacoes if a.faixa in FAIXAS_EM_RISCO),
                2,
            ),
            qtd_na_fila=sum(1 for a in avaliacoes if a.posicao_fila is not None),
            por_faixa={faixa: por_faixa.get(faixa, 0) for faixa in FaixaRisco},
            por_dimensao={dimensao: por_dimensao.get(dimensao, 0) for dimensao in Dimensao},
        )

    def fila(self, limite: int) -> list[ItemFila]:
        execucao = self._execucoes.ultima_producao()
        if execucao is None:
            return []
        return [item_fila(a) for a in self._avaliacoes.fila(execucao.id, limite)]
```

Acrescente em `backend/app/dependencies.py`:
```python
from app.repositories.avaliacao_repository import AvaliacaoRepository
from app.repositories.execucao_repository import ExecucaoRepository
from app.services.dashboard_service import DashboardService


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(ExecucaoRepository(db), AvaliacaoRepository(db))
```

`backend/app/controllers/dashboard_controller.py`:
```python
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_dashboard_service, get_usuario_atual
from app.schemas.dashboard import ItemFila, ResumoDashboard
from app.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_usuario_atual)]
)


@router.get("/resumo", response_model=ResumoDashboard)
def resumo(service: DashboardService = Depends(get_dashboard_service)) -> ResumoDashboard:
    return service.resumo()


@router.get("/fila", response_model=list[ItemFila])
def fila(
    limite: int = Query(10, ge=1, le=100, description="Máximo de itens da fila"),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[ItemFila]:
    return service.fila(limite)
```

`backend/app/controllers/catalogo_controller.py`:
```python
from fastapi import APIRouter, Depends

from app.dependencies import get_catalogo_service, get_usuario_atual
from app.models import AcaoRecomendada, ConfiguracaoSinal
from app.schemas.catalogo import AcaoResponse, SinalResponse
from app.services.catalogo_service import CatalogoService

router = APIRouter(tags=["catalogo"], dependencies=[Depends(get_usuario_atual)])


@router.get("/sinais", response_model=list[SinalResponse])
def sinais(service: CatalogoService = Depends(get_catalogo_service)) -> list[ConfiguracaoSinal]:
    return service.listar_sinais()


@router.get("/acoes-recomendadas", response_model=list[AcaoResponse])
def acoes(service: CatalogoService = Depends(get_catalogo_service)) -> list[AcaoRecomendada]:
    return service.listar_acoes()
```

Em `backend/app/main.py`:
1. inclua `dashboard_controller.router` e `catalogo_controller.router` com `prefix="/api"`;
2. logo após criar `app.state.session_factory`, garanta o catálogo seed (idempotente):
```python
    with app.state.session_factory() as session:
        criar_catalogo_service(session, settings).garantir_seeds()
```
(importe `from app.services.fabrica import criar_catalogo_service`).

- [ ] **Step 5: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam.
Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 6: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): endpoints de dashboard (resumo e fila), sinais e ações recomendadas" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: Endpoints de clientes e métricas mensais

**Files:**
- Create: `backend/app/schemas/comum.py`, `backend/app/schemas/cliente.py`, `backend/app/schemas/metrica.py`
- Create: `backend/app/services/cliente_service.py`, `backend/app/services/metrica_service.py`
- Create: `backend/app/controllers/cliente_controller.py`, `backend/app/controllers/metrica_controller.py`
- Modify: `backend/app/repositories/cliente_repository.py` (busca paginada), `backend/app/repositories/atendimento_repository.py` (agregado mensal), `backend/app/services/mapeadores.py` (cliente_resumo), `backend/app/dependencies.py`, `backend/app/main.py`
- Test: `backend/tests/integration/test_clientes.py`, `backend/tests/integration/test_metricas.py`

**Interfaces:**
- Consumes: `ClienteRepository`, `AtendimentoRepository`, `NpsRepository`, `ExecucaoRepository` (Task 8), `AvaliacaoRepository`, `avaliacao_response` (Task 9), `ParametroInvalidoError`, `RecursoNaoEncontradoError` (Task 3).
- Produces: `Pagina[T](itens, total, pagina, tamanho)`; `ClienteResumo`, `ClienteDetalhe(+avaliacao)`, `AtendimentoMes`, `NpsMes`, `HistoricoCliente`; `VariavelMetrica(codigo, rotulo)`, `PontoMensal(mes_ref, valor)`; `FiltroClientes` e `ClienteRepository.buscar(execucao_id, filtro, ordenar, offset, limite) -> tuple[list[tuple[Cliente, AvaliacaoRisco | None]], int]`; `AtendimentoRepository.agregado_mensal(coluna, agregacao) -> list[tuple[date, float]]`; `ClienteService.listar(...)`, `.detalhe(cliente_id)`, `.historico(cliente_id)`; `MetricaService.variaveis()`, `.mensal(variavel, agregacao)`; rotas `GET /api/clientes`, `/api/clientes/{id}`, `/api/clientes/{id}/historico`, `/api/metricas/variaveis`, `/api/metricas/mensal`.

- [ ] **Step 1: Escrever os testes que falham**

`backend/tests/integration/test_clientes.py`:
```python
import pytest

CHAVES_RESUMO = {
    "cliente_id",
    "segmento",
    "porte",
    "plano",
    "valor_mensal",
    "sla_contratado_h",
    "inicio_contrato",
    "situacao",
    "mes_cancelamento",
    "score_risco",
    "faixa",
    "receita_em_risco",
    "posicao_fila",
}


def _listar(client, headers, **params):
    resposta = client.get("/api/clientes", headers=headers, params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


@pytest.mark.parametrize(
    "rota", ["/api/clientes", "/api/clientes/C001", "/api/clientes/C001/historico"]
)
def test_clientes_exige_autenticacao(client, rota):
    assert client.get(rota).status_code == 401


def test_listagem_padrao_paginada(client_com_base, auth_headers):
    pagina = _listar(client_com_base, auth_headers)

    assert (pagina["total"], pagina["pagina"], pagina["tamanho"]) == (80, 1, 20)
    assert len(pagina["itens"]) == 20
    assert pagina["itens"][0]["cliente_id"] == "C001"
    assert set(pagina["itens"][0]) == CHAVES_RESUMO


def test_paginas_seguintes(client_com_base, auth_headers):
    quarta = _listar(client_com_base, auth_headers, pagina=4)
    quinta = _listar(client_com_base, auth_headers, pagina=5)

    assert quarta["itens"][0]["cliente_id"] == "C061"
    assert quinta["itens"] == [] and quinta["total"] == 80


def test_filtros(client_com_base, auth_headers):
    cancelados = _listar(client_com_base, auth_headers, situacao="CANCELADO", tamanho=100)
    assert cancelados["total"] == 22
    assert all(c["situacao"] == "CANCELADO" and c["score_risco"] is None for c in cancelados["itens"])

    assert _listar(client_com_base, auth_headers, plano="ENTERPRISE")["total"] == 19
    assert _listar(client_com_base, auth_headers, porte="PEQUENO")["total"] == 35
    assert _listar(client_com_base, auth_headers, segmento="saude")["total"] == 12
    busca = _listar(client_com_base, auth_headers, busca="c08")
    assert [c["cliente_id"] for c in busca["itens"]] == ["C080"]


def test_filtro_por_faixa_bate_com_o_resumo(client_com_base, auth_headers):
    resumo = client_com_base.get("/api/dashboard/resumo", headers=auth_headers).json()
    atencao = _listar(client_com_base, auth_headers, faixa="ATENCAO", tamanho=100)

    assert atencao["total"] == resumo["por_faixa"]["ATENCAO"]
    assert all(c["faixa"] == "ATENCAO" for c in atencao["itens"])


def test_ordenacao_por_receita_em_risco_deixa_nulos_no_fim(client_com_base, auth_headers):
    itens = _listar(client_com_base, auth_headers, ordenar="receita_em_risco", tamanho=100)["itens"]

    valores = [c["receita_em_risco"] for c in itens]
    preenchidos = [v for v in valores if v is not None]
    assert preenchidos == sorted(preenchidos, reverse=True)
    assert valores[: len(preenchidos)] == preenchidos
    assert all(v is None for v in valores[len(preenchidos) :])


@pytest.mark.parametrize(
    "params", [{"ordenar": "xpto"}, {"faixa": "PESSIMO"}, {"tamanho": 101}, {"pagina": 0}]
)
def test_parametros_invalidos_retornam_422(client_com_base, auth_headers, params):
    resposta = client_com_base.get("/api/clientes", headers=auth_headers, params=params)
    assert resposta.status_code == 422


def test_detalhe_de_cliente_na_fila(client_com_base, auth_headers):
    fila = client_com_base.get("/api/dashboard/fila", headers=auth_headers).json()
    primeiro = fila[0]["cliente_id"]

    detalhe = client_com_base.get(f"/api/clientes/{primeiro.lower()}", headers=auth_headers)

    assert detalhe.status_code == 200
    corpo = detalhe.json()
    assert corpo["cliente_id"] == primeiro
    avaliacao = corpo["avaliacao"]
    assert avaliacao["posicao_fila"] == 1
    assert avaliacao["evidencias"] and avaliacao["evidencias"][0]["texto"]
    assert avaliacao["acao_recomendada"]["descricao"]


def test_detalhe_de_cancelado_nao_tem_avaliacao(client_com_base, auth_headers):
    cancelado = _listar(client_com_base, auth_headers, situacao="CANCELADO")["itens"][0]

    corpo = client_com_base.get(
        f"/api/clientes/{cancelado['cliente_id']}", headers=auth_headers
    ).json()

    assert corpo["situacao"] == "CANCELADO"
    assert corpo["mes_cancelamento"] is not None
    assert corpo["avaliacao"] is None


def test_cliente_inexistente_retorna_404(client_com_base, auth_headers):
    resposta = client_com_base.get("/api/clientes/C999", headers=auth_headers)

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Cliente C999 não encontrado"}
    historico = client_com_base.get("/api/clientes/C999/historico", headers=auth_headers)
    assert historico.status_code == 404


def test_historico_pronto_para_grafico(client_com_base, auth_headers):
    corpo = client_com_base.get("/api/clientes/C001/historico", headers=auth_headers).json()

    assert corpo["cliente_id"] == "C001"
    meses = [linha["mes_ref"] for linha in corpo["atendimento"]]
    assert len(meses) == 18 and meses == sorted(meses)
    assert meses[0] == "2025-01-01"
    assert {"pct_sla_cumprido", "uso_plataforma_pct", "chamados_abertos"} <= set(
        corpo["atendimento"][0]
    )
    assert len(corpo["nps"]) == 6
    assert {"mes_ref", "respondeu", "nota_nps", "classificacao_nps"} == set(corpo["nps"][0])
```

`backend/tests/integration/test_metricas.py`:
```python
import pandas as pd
import pytest


@pytest.mark.parametrize("rota", ["/api/metricas/variaveis", "/api/metricas/mensal?variavel=x"])
def test_metricas_exige_autenticacao(client, rota):
    assert client.get(rota).status_code == 401


def test_variaveis_disponiveis(client, auth_headers):
    variaveis = client.get("/api/metricas/variaveis", headers=auth_headers).json()

    codigos = [v["codigo"] for v in variaveis]
    assert len(codigos) == 11
    assert "pct_sla_cumprido" in codigos
    assert all(v["rotulo"] for v in variaveis)


def test_media_mensal_ignora_nulos(client_com_base, auth_headers, caminho_xlsx):
    pontos = client_com_base.get(
        "/api/metricas/mensal",
        headers=auth_headers,
        params={"variavel": "pct_sla_cumprido", "agregacao": "media"},
    ).json()

    df = pd.read_excel(caminho_xlsx, sheet_name="atendimento_mensal")
    esperado = df.dropna(subset=["pct_sla_cumprido"]).groupby("mes_ref")["pct_sla_cumprido"].mean()

    assert len(pontos) == 18
    assert [p["mes_ref"] for p in pontos] == sorted(p["mes_ref"] for p in pontos)
    assert pontos[0]["mes_ref"] == "2025-01-01"
    assert pontos[0]["valor"] == pytest.approx(esperado["2025-01"], rel=1e-3)


def test_soma_mensal(client_com_base, auth_headers, caminho_xlsx):
    pontos = client_com_base.get(
        "/api/metricas/mensal",
        headers=auth_headers,
        params={"variavel": "chamados_abertos", "agregacao": "soma"},
    ).json()

    df = pd.read_excel(caminho_xlsx, sheet_name="atendimento_mensal")
    assert pontos[0]["valor"] == df[df["mes_ref"] == "2025-01"]["chamados_abertos"].sum()


def test_variavel_ou_agregacao_invalida_retorna_422(client, auth_headers):
    invalida = client.get(
        "/api/metricas/mensal", headers=auth_headers, params={"variavel": "senha_hash"}
    )
    assert invalida.status_code == 422
    assert "senha_hash" in invalida.json()["detail"]
    agregacao = client.get(
        "/api/metricas/mensal",
        headers=auth_headers,
        params={"variavel": "chamados_abertos", "agregacao": "mediana"},
    )
    assert agregacao.status_code == 422


def test_sem_base_retorna_lista_vazia(client, auth_headers):
    pontos = client.get(
        "/api/metricas/mensal", headers=auth_headers, params={"variavel": "chamados_abertos"}
    )
    assert pontos.status_code == 200 and pontos.json() == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/Scripts/python -m pytest tests/integration/test_clientes.py tests/integration/test_metricas.py -v`
Expected: FAIL (404 nas rotas novas).

- [ ] **Step 3: Implementar repositories**

Acrescente em `backend/app/repositories/cliente_repository.py` (ajuste os imports: `from dataclasses import dataclass`, `from sqlalchemy import and_, case, func, or_, select`, `from sqlalchemy.sql.elements import ColumnElement`, `from app.core.enums import FaixaRisco, Plano, Porte, SituacaoCliente`, `from app.models import AvaliacaoRisco, Cliente, Situacao`):
```python
@dataclass(frozen=True)
class FiltroClientes:
    situacao: SituacaoCliente | None = None
    faixa: FaixaRisco | None = None
    plano: Plano | None = None
    porte: Porte | None = None
    segmento: str | None = None
    busca: str | None = None
```
e, na classe `ClienteRepository`:
```python
    def buscar(
        self,
        execucao_id: int | None,
        filtro: FiltroClientes,
        ordenar: str,
        offset: int,
        limite: int,
    ) -> tuple[list[tuple[Cliente, AvaliacaoRisco | None]], int]:
        """Clientes + avaliação da execução informada (outer join), filtrados e paginados."""
        juncao_avaliacao = and_(
            AvaliacaoRisco.cliente_id == Cliente.cliente_id,
            AvaliacaoRisco.execucao_id == (execucao_id if execucao_id is not None else -1),
        )
        condicoes = self._condicoes(filtro)

        total = self._session.scalar(
            select(func.count(Cliente.cliente_id))
            .select_from(Cliente)
            .outerjoin(Situacao, Situacao.cliente_id == Cliente.cliente_id)
            .outerjoin(AvaliacaoRisco, juncao_avaliacao)
            .where(*condicoes)
        )
        consulta = (
            select(Cliente, AvaliacaoRisco)
            .select_from(Cliente)
            .outerjoin(Situacao, Situacao.cliente_id == Cliente.cliente_id)
            .outerjoin(AvaliacaoRisco, juncao_avaliacao)
            .options(selectinload(Cliente.situacao))
            .where(*condicoes)
            .order_by(*self._ordem(ordenar))
            .offset(offset)
            .limit(limite)
        )
        linhas = [(cliente, avaliacao) for cliente, avaliacao in self._session.execute(consulta)]
        return linhas, total or 0

    @staticmethod
    def _condicoes(filtro: FiltroClientes) -> list[ColumnElement[bool]]:
        condicoes: list[ColumnElement[bool]] = []
        if filtro.situacao is not None:
            condicoes.append(Situacao.situacao == filtro.situacao)
        if filtro.faixa is not None:
            condicoes.append(AvaliacaoRisco.faixa == filtro.faixa)
        if filtro.plano is not None:
            condicoes.append(Cliente.plano == filtro.plano)
        if filtro.porte is not None:
            condicoes.append(Cliente.porte == filtro.porte)
        if filtro.segmento:
            condicoes.append(func.lower(Cliente.segmento) == filtro.segmento.strip().lower())
        if filtro.busca and filtro.busca.strip():
            termo = f"%{filtro.busca.strip().lower()}%"
            condicoes.append(
                or_(
                    func.lower(Cliente.cliente_id).like(termo),
                    func.lower(Cliente.segmento).like(termo),
                )
            )
        return condicoes

    @staticmethod
    def _ordem(ordenar: str) -> list:
        # "nulos no fim" portável (SQL Server não tem NULLS LAST)
        if ordenar == "valor_mensal":
            return [Cliente.valor_mensal.desc(), Cliente.cliente_id]
        if ordenar in ("score", "receita_em_risco"):
            coluna = (
                AvaliacaoRisco.score_risco if ordenar == "score" else AvaliacaoRisco.receita_em_risco
            )
            return [case((coluna.is_(None), 1), else_=0), coluna.desc(), Cliente.cliente_id]
        return [Cliente.cliente_id]
```

Acrescente em `backend/app/repositories/atendimento_repository.py`:
```python
    def agregado_mensal(self, coluna: str, agregacao: str) -> list[tuple[date, float]]:
        """Média ou soma mensal de uma coluna de toda a carteira, ignorando nulos."""
        campo = getattr(AtendimentoMensal, coluna)
        funcao = func.avg if agregacao == "media" else func.sum
        consulta = (
            select(AtendimentoMensal.mes_ref, funcao(campo))
            .where(campo.is_not(None))
            .group_by(AtendimentoMensal.mes_ref)
            .order_by(AtendimentoMensal.mes_ref)
        )
        return [(mes, float(valor)) for mes, valor in self._session.execute(consulta)]
```

- [ ] **Step 4: Implementar schemas**

`backend/app/schemas/comum.py`:
```python
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    itens: list[T]
    total: int
    pagina: int
    tamanho: int
```

`backend/app/schemas/cliente.py`:
```python
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.core.enums import ClassificacaoNPS, FaixaRisco, Plano, Porte, SituacaoCliente
from app.schemas.risco import AvaliacaoRiscoResponse


class ClienteResumo(BaseModel):
    cliente_id: str
    segmento: str
    porte: Porte
    plano: Plano
    valor_mensal: float
    sla_contratado_h: int
    inicio_contrato: date
    situacao: SituacaoCliente | None
    mes_cancelamento: date | None
    score_risco: float | None = None
    faixa: FaixaRisco | None = None
    receita_em_risco: float | None = None
    posicao_fila: int | None = None


class ClienteDetalhe(ClienteResumo):
    avaliacao: AvaliacaoRiscoResponse | None = None


class AtendimentoMes(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mes_ref: date
    chamados_abertos: int
    chamados_criticos: int
    chamados_reabertos: int
    chamados_dentro_sla: int
    pct_sla_cumprido: float | None
    tempo_medio_resolucao_h: float
    reclamacoes_formais: int
    uso_plataforma_pct: float
    dias_atraso_pagamento: int
    reunioes_previstas: int
    reunioes_realizadas: int


class NpsMes(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mes_ref: date
    respondeu: bool
    nota_nps: int | None
    classificacao_nps: ClassificacaoNPS


class HistoricoCliente(BaseModel):
    cliente_id: str
    atendimento: list[AtendimentoMes]
    nps: list[NpsMes]
```

`backend/app/schemas/metrica.py`:
```python
from datetime import date

from pydantic import BaseModel


class VariavelMetrica(BaseModel):
    codigo: str
    rotulo: str


class PontoMensal(BaseModel):
    mes_ref: date
    valor: float
```

Acrescente em `backend/app/services/mapeadores.py` (importe `Cliente` de `app.models` e `ClienteResumo` de `app.schemas.cliente`):
```python
def cliente_resumo(cliente: Cliente, avaliacao: AvaliacaoRisco | None) -> ClienteResumo:
    situacao = cliente.situacao
    return ClienteResumo(
        cliente_id=cliente.cliente_id,
        segmento=cliente.segmento,
        porte=cliente.porte,
        plano=cliente.plano,
        valor_mensal=float(cliente.valor_mensal),
        sla_contratado_h=cliente.sla_contratado_h,
        inicio_contrato=cliente.inicio_contrato,
        situacao=situacao.situacao if situacao else None,
        mes_cancelamento=situacao.mes_cancelamento if situacao else None,
        score_risco=float(avaliacao.score_risco) if avaliacao else None,
        faixa=avaliacao.faixa if avaliacao else None,
        receita_em_risco=float(avaliacao.receita_em_risco) if avaliacao else None,
        posicao_fila=avaliacao.posicao_fila if avaliacao else None,
    )
```

- [ ] **Step 5: Implementar services**

`backend/app/services/cliente_service.py`:
```python
from app.core.enums import FaixaRisco, Plano, Porte, SituacaoCliente
from app.core.exceptions import RecursoNaoEncontradoError
from app.models import Cliente
from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.avaliacao_repository import AvaliacaoRepository
from app.repositories.cliente_repository import ClienteRepository, FiltroClientes
from app.repositories.execucao_repository import ExecucaoRepository
from app.repositories.nps_repository import NpsRepository
from app.schemas.cliente import (
    AtendimentoMes,
    ClienteDetalhe,
    ClienteResumo,
    HistoricoCliente,
    NpsMes,
)
from app.schemas.comum import Pagina
from app.services.mapeadores import avaliacao_response, cliente_resumo


class ClienteService:
    """Consultas de clientes combinadas com a última avaliação de risco de produção."""

    def __init__(
        self,
        clientes: ClienteRepository,
        atendimentos: AtendimentoRepository,
        nps: NpsRepository,
        execucoes: ExecucaoRepository,
        avaliacoes: AvaliacaoRepository,
    ) -> None:
        self._clientes = clientes
        self._atendimentos = atendimentos
        self._nps = nps
        self._execucoes = execucoes
        self._avaliacoes = avaliacoes

    def listar(
        self,
        *,
        situacao: SituacaoCliente | None = None,
        faixa: FaixaRisco | None = None,
        plano: Plano | None = None,
        porte: Porte | None = None,
        segmento: str | None = None,
        busca: str | None = None,
        ordenar: str = "cliente_id",
        pagina: int = 1,
        tamanho: int = 20,
    ) -> Pagina[ClienteResumo]:
        execucao = self._execucoes.ultima_producao()
        filtro = FiltroClientes(situacao, faixa, plano, porte, segmento, busca)
        linhas, total = self._clientes.buscar(
            execucao.id if execucao else None, filtro, ordenar, (pagina - 1) * tamanho, tamanho
        )
        return Pagina[ClienteResumo](
            itens=[cliente_resumo(cliente, avaliacao) for cliente, avaliacao in linhas],
            total=total,
            pagina=pagina,
            tamanho=tamanho,
        )

    def detalhe(self, cliente_id: str) -> ClienteDetalhe:
        cliente = self._obter(cliente_id)
        execucao = self._execucoes.ultima_producao()
        avaliacao = (
            self._avaliacoes.obter_por_cliente(execucao.id, cliente.cliente_id)
            if execucao
            else None
        )
        return ClienteDetalhe(
            **cliente_resumo(cliente, avaliacao).model_dump(),
            avaliacao=avaliacao_response(avaliacao) if avaliacao else None,
        )

    def historico(self, cliente_id: str) -> HistoricoCliente:
        cliente = self._obter(cliente_id)
        return HistoricoCliente(
            cliente_id=cliente.cliente_id,
            atendimento=[
                AtendimentoMes.model_validate(a)
                for a in self._atendimentos.listar_por_cliente(cliente.cliente_id)
            ],
            nps=[NpsMes.model_validate(p) for p in self._nps.listar_por_cliente(cliente.cliente_id)],
        )

    def _obter(self, cliente_id: str) -> Cliente:
        codigo = cliente_id.strip().upper()
        cliente = self._clientes.obter(codigo)
        if cliente is None:
            raise RecursoNaoEncontradoError(f"Cliente {codigo} não encontrado")
        return cliente
```

`backend/app/services/metrica_service.py`:
```python
from app.core.exceptions import ParametroInvalidoError
from app.repositories.atendimento_repository import AtendimentoRepository
from app.schemas.metrica import PontoMensal, VariavelMetrica

VARIAVEIS_METRICA: dict[str, str] = {
    "chamados_abertos": "Chamados abertos (qtd)",
    "chamados_criticos": "Chamados críticos (qtd)",
    "chamados_reabertos": "Chamados reabertos (qtd)",
    "chamados_dentro_sla": "Chamados dentro do SLA (qtd)",
    "pct_sla_cumprido": "SLA cumprido (%)",
    "tempo_medio_resolucao_h": "Tempo médio de resolução (h)",
    "reclamacoes_formais": "Reclamações formais (qtd)",
    "uso_plataforma_pct": "Uso da plataforma (%)",
    "dias_atraso_pagamento": "Dias de atraso no pagamento",
    "reunioes_previstas": "Reuniões previstas (qtd)",
    "reunioes_realizadas": "Reuniões realizadas (qtd)",
}


class MetricaService:
    """Evolução mensal agregada de toda a carteira (média ou soma, ignorando nulos)."""

    def __init__(self, atendimentos: AtendimentoRepository) -> None:
        self._atendimentos = atendimentos

    def variaveis(self) -> list[VariavelMetrica]:
        return [VariavelMetrica(codigo=c, rotulo=r) for c, r in VARIAVEIS_METRICA.items()]

    def mensal(self, variavel: str, agregacao: str) -> list[PontoMensal]:
        if variavel not in VARIAVEIS_METRICA:
            raise ParametroInvalidoError(
                f"Variável '{variavel}' inválida. Use uma de: {', '.join(VARIAVEIS_METRICA)}"
            )
        return [
            PontoMensal(mes_ref=mes, valor=round(valor, 4))
            for mes, valor in self._atendimentos.agregado_mensal(variavel, agregacao)
        ]
```

- [ ] **Step 6: Implementar dependências e controllers**

Acrescente em `backend/app/dependencies.py`:
```python
from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.nps_repository import NpsRepository
from app.services.cliente_service import ClienteService
from app.services.metrica_service import MetricaService


def get_cliente_service(db: Session = Depends(get_db)) -> ClienteService:
    return ClienteService(
        ClienteRepository(db),
        AtendimentoRepository(db),
        NpsRepository(db),
        ExecucaoRepository(db),
        AvaliacaoRepository(db),
    )


def get_metrica_service(db: Session = Depends(get_db)) -> MetricaService:
    return MetricaService(AtendimentoRepository(db))
```

`backend/app/controllers/cliente_controller.py`:
```python
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.enums import FaixaRisco, Plano, Porte, SituacaoCliente
from app.dependencies import get_cliente_service, get_usuario_atual
from app.schemas.cliente import ClienteDetalhe, ClienteResumo, HistoricoCliente
from app.schemas.comum import Pagina
from app.services.cliente_service import ClienteService

router = APIRouter(prefix="/clientes", tags=["clientes"], dependencies=[Depends(get_usuario_atual)])

Ordenacao = Literal["cliente_id", "valor_mensal", "score", "receita_em_risco"]


@router.get("", response_model=Pagina[ClienteResumo])
def listar(
    situacao: SituacaoCliente | None = None,
    faixa: FaixaRisco | None = None,
    plano: Plano | None = None,
    porte: Porte | None = None,
    segmento: str | None = Query(None, examples=["Saude"]),
    busca: str | None = Query(None, description="Trecho do código ou do segmento"),
    ordenar: Ordenacao = "cliente_id",
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(20, ge=1, le=100),
    service: ClienteService = Depends(get_cliente_service),
) -> Pagina[ClienteResumo]:
    return service.listar(
        situacao=situacao,
        faixa=faixa,
        plano=plano,
        porte=porte,
        segmento=segmento,
        busca=busca,
        ordenar=ordenar,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get("/{cliente_id}", response_model=ClienteDetalhe)
def detalhe(
    cliente_id: str, service: ClienteService = Depends(get_cliente_service)
) -> ClienteDetalhe:
    return service.detalhe(cliente_id)


@router.get("/{cliente_id}/historico", response_model=HistoricoCliente)
def historico(
    cliente_id: str, service: ClienteService = Depends(get_cliente_service)
) -> HistoricoCliente:
    return service.historico(cliente_id)
```

`backend/app/controllers/metrica_controller.py`:
```python
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_metrica_service, get_usuario_atual
from app.schemas.metrica import PontoMensal, VariavelMetrica
from app.services.metrica_service import MetricaService

router = APIRouter(prefix="/metricas", tags=["metricas"], dependencies=[Depends(get_usuario_atual)])


@router.get("/variaveis", response_model=list[VariavelMetrica])
def variaveis(service: MetricaService = Depends(get_metrica_service)) -> list[VariavelMetrica]:
    return service.variaveis()


@router.get("/mensal", response_model=list[PontoMensal])
def mensal(
    variavel: str = Query(..., examples=["pct_sla_cumprido"]),
    agregacao: Literal["media", "soma"] = "media",
    service: MetricaService = Depends(get_metrica_service),
) -> list[PontoMensal]:
    return service.mensal(variavel, agregacao)
```

Em `backend/app/main.py`, inclua `cliente_controller.router` e `metrica_controller.router` com `prefix="/api"`.

- [ ] **Step 7: Rodar e ver passar**

Run: `cd backend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam.
Run: `cd backend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 8: Commit**

```bash
git add backend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(backend): endpoints de clientes (lista, detalhe, histórico) e métricas mensais" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: Front Streamlit — cliente da API, sessão e tela de login/cadastro

**Files:**
- Create: `frontend/pyproject.toml`, `frontend/requirements.txt`, `frontend/.streamlit/config.toml`
- Create: `frontend/api_client.py`, `frontend/auth.py`, `frontend/Home.py`
- Test: `frontend/tests/__init__.py` (vazio), `frontend/tests/conftest.py`, `frontend/tests/test_api_client.py`, `frontend/tests/test_home.py`

**Interfaces:**
- Consumes: contrato HTTP da API (Tasks 4–10): `POST /auth/cadastro`, `POST /auth/login`, `GET /auth/me`, `GET /dashboard/resumo`, `GET /dashboard/fila`, `GET /clientes`, `GET /clientes/{id}`, `GET /clientes/{id}/historico`, `GET /metricas/variaveis`, `GET /metricas/mensal`, `GET /sinais`, `GET /acoes-recomendadas`, `POST /analise/executar`, `POST /importacao`. Erros vêm como `{"detail": str}` ou, em 422 de validação, `{"detail": [{"loc": [...], "msg": str}, ...]}`.
- Produces: `ApiErro(status, detail)`, `NaoAutenticado(ApiErro)`, `ApiClient(base_url=None, token=None, transport=None, timeout=30.0)` com os métodos `cadastrar(nome_completo, usuario, senha)`, `login(usuario, senha)`, `me()`, `resumo_dashboard()`, `fila(limite=10)`, `listar_clientes(**filtros)`, `cliente(cliente_id)`, `historico(cliente_id)`, `variaveis_metricas()`, `metrica_mensal(variavel, agregacao="media")`, `sinais()`, `acoes()`, `executar_analise()`, `importar(nome_arquivo, conteudo)`; `auth.fabrica_cliente` (ponto de injeção para testes), `auth.cliente_api()`, `auth.esta_logado()`, `auth.iniciar_sessao(resposta_login)`, `auth.encerrar_sessao()`, `auth.exigir_login() -> ApiClient`, `auth.tratar_erro(erro)`; chaves de sessão `"token"` e `"usuario"`; fixture pytest **`api_falsa`** (`ApiFalsa.responder(metodo, caminho, status, corpo)`, `.requisicoes`, `.cliente(token=None)`).

- [ ] **Step 1: Arquivos de projeto e dependências**

`frontend/requirements.txt`:
```text
streamlit>=1.50
httpx>=0.27
pandas>=2.2
plotly>=5.22
pytest>=8
ruff>=0.5
```

`frontend/pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

`frontend/.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#0156FC"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#FAF9F5"
textColor = "#000A1E"
font = "sans serif"
```

Run: `.venv/Scripts/python -m pip install -q -r frontend/requirements.txt`
Expected: instala sem erro.

- [ ] **Step 2: Escrever os testes que falham**

`frontend/tests/conftest.py`:
```python
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
            base_url="http://api.teste/api", token=token, transport=httpx.MockTransport(self.handler)
        )


@pytest.fixture
def api_falsa(monkeypatch: pytest.MonkeyPatch) -> ApiFalsa:
    falsa = ApiFalsa()
    monkeypatch.setattr(auth, "fabrica_cliente", falsa.cliente)
    return falsa
```

`frontend/tests/test_api_client.py`:
```python
import json

import httpx
import pytest

from api_client import ApiClient, ApiErro, NaoAutenticado

TOKEN_RESPOSTA = {
    "access_token": "tok",
    "token_type": "bearer",
    "expira_em": "2026-09-20T02:00:00Z",
    "usuario": {"id": 1, "nome_completo": "Maria", "usuario": "maria"},
}


def test_login_envia_json_e_devolve_corpo(api_falsa):
    api_falsa.responder("POST", "/auth/login", 200, TOKEN_RESPOSTA)

    resposta = api_falsa.cliente().login("maria", "SenhaForte123")

    assert resposta["access_token"] == "tok"
    requisicao = api_falsa.requisicoes[0]
    assert str(requisicao.url) == "http://api.teste/api/auth/login"
    assert json.loads(requisicao.content) == {"usuario": "maria", "senha": "SenhaForte123"}


def test_token_vai_no_cabecalho(api_falsa):
    api_falsa.responder("GET", "/auth/me", 200, {"id": 1})

    api_falsa.cliente(token="abc").me()

    assert api_falsa.requisicoes[0].headers["authorization"] == "Bearer abc"


def test_401_vira_nao_autenticado_com_mensagem(api_falsa):
    api_falsa.responder("POST", "/auth/login", 401, {"detail": "Usuário ou senha inválidos"})

    with pytest.raises(NaoAutenticado) as erro:
        api_falsa.cliente().login("maria", "errada1")

    assert erro.value.detail == "Usuário ou senha inválidos"


def test_422_de_validacao_vira_mensagem_legivel(api_falsa):
    api_falsa.responder(
        "POST",
        "/auth/cadastro",
        422,
        {"detail": [{"loc": ["body", "senha"], "msg": "Value error, A senha deve conter ao menos uma letra e um número"}]},
    )

    with pytest.raises(ApiErro) as erro:
        api_falsa.cliente().cadastrar("Maria", "maria", "semnumero")

    assert erro.value.status == 422
    assert erro.value.detail == "senha: A senha deve conter ao menos uma letra e um número"


def test_409_vira_api_erro(api_falsa):
    api_falsa.responder("POST", "/auth/cadastro", 409, {"detail": "Usuário já cadastrado"})

    with pytest.raises(ApiErro) as erro:
        api_falsa.cliente().cadastrar("Maria", "maria", "SenhaForte123")

    assert not isinstance(erro.value, NaoAutenticado)
    assert (erro.value.status, erro.value.detail) == (409, "Usuário já cadastrado")


def test_api_fora_do_ar_gera_mensagem_amigavel():
    def recusa(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusado", request=request)

    cliente = ApiClient(base_url="http://api.teste/api", transport=httpx.MockTransport(recusa))

    with pytest.raises(ApiErro) as erro:
        cliente.resumo_dashboard()

    assert erro.value.status == 0
    assert "Não foi possível conectar à API" in erro.value.detail


def test_listar_clientes_descarta_filtros_vazios(api_falsa):
    api_falsa.responder("GET", "/clientes", 200, {"itens": [], "total": 0, "pagina": 1, "tamanho": 20})

    api_falsa.cliente(token="t").listar_clientes(situacao=None, faixa="ATENCAO", busca="", pagina=2)

    assert dict(api_falsa.requisicoes[0].url.params) == {"faixa": "ATENCAO", "pagina": "2"}


def test_importar_envia_multipart(api_falsa):
    api_falsa.responder("POST", "/importacao", 200, {"contagens": {}, "avisos": []})

    api_falsa.cliente(token="t").importar("base.xlsx", b"conteudo")

    requisicao = api_falsa.requisicoes[0]
    assert requisicao.headers["content-type"].startswith("multipart/form-data")
    assert b'name="arquivo"; filename="base.xlsx"' in requisicao.content
```

`frontend/tests/test_home.py`:
```python
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

import auth
from api_client import ApiClient

HOME = str(Path(__file__).resolve().parents[1] / "Home.py")
TOKEN_RESPOSTA = {
    "access_token": "tok",
    "token_type": "bearer",
    "expira_em": "2026-09-20T02:00:00Z",
    "usuario": {"id": 1, "nome_completo": "Maria da Silva", "usuario": "maria.silva"},
}


def _app() -> AppTest:
    return AppTest.from_file(HOME, default_timeout=30).run()


def _entrar(at: AppTest, usuario: str, senha: str) -> AppTest:
    at.text_input(key="login_usuario").input(usuario)
    at.text_input(key="login_senha").input(senha)
    return at.button(key="botao_entrar").click().run()


def test_home_mostra_abas_de_login_e_cadastro(api_falsa):
    at = _app()

    assert not at.exception
    assert [aba.label for aba in at.tabs] == ["Entrar", "Criar conta"]


def test_login_com_sucesso_guarda_token_e_sauda(api_falsa):
    api_falsa.responder("POST", "/auth/login", 200, TOKEN_RESPOSTA)

    at = _entrar(_app(), "maria.silva", "SenhaForte123")

    assert not at.exception
    assert at.session_state["token"] == "tok"
    assert any("Maria da Silva" in m.value for m in at.sidebar.markdown)


def test_login_invalido_mostra_mensagem_da_api(api_falsa):
    api_falsa.responder("POST", "/auth/login", 401, {"detail": "Usuário ou senha inválidos"})

    at = _entrar(_app(), "maria.silva", "errada123")

    assert [e.value for e in at.error] == ["Usuário ou senha inválidos"]
    assert "token" not in at.session_state


def test_cadastro_faz_login_automatico(api_falsa):
    api_falsa.responder("POST", "/auth/cadastro", 201, {"id": 1})
    api_falsa.responder("POST", "/auth/login", 200, TOKEN_RESPOSTA)
    at = _app()

    at.text_input(key="cadastro_nome").input("Maria da Silva")
    at.text_input(key="cadastro_usuario").input("maria.silva")
    at.text_input(key="cadastro_senha").input("SenhaForte123")
    at.text_input(key="cadastro_confirmacao").input("SenhaForte123")
    at = at.button(key="botao_cadastrar").click().run()

    assert not at.exception
    assert at.session_state["token"] == "tok"


def test_cadastro_com_senhas_diferentes_nem_chama_a_api(api_falsa):
    at = _app()

    at.text_input(key="cadastro_nome").input("Maria da Silva")
    at.text_input(key="cadastro_usuario").input("maria.silva")
    at.text_input(key="cadastro_senha").input("SenhaForte123")
    at.text_input(key="cadastro_confirmacao").input("Outra123")
    at = at.button(key="botao_cadastrar").click().run()

    assert [e.value for e in at.error] == ["As senhas não conferem."]
    assert api_falsa.requisicoes == []


def test_api_fora_do_ar_mostra_mensagem_amigavel(monkeypatch):
    def recusa(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusado", request=request)

    monkeypatch.setattr(
        auth,
        "fabrica_cliente",
        lambda token=None: ApiClient(
            base_url="http://api.teste/api", token=token, transport=httpx.MockTransport(recusa)
        ),
    )

    at = _entrar(_app(), "maria.silva", "SenhaForte123")

    assert not at.exception
    assert "Não foi possível conectar à API" in at.error[0].value
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd frontend && ../.venv/Scripts/python -m pytest -v`
Expected: ERROR `ModuleNotFoundError: No module named 'auth'` (ou `api_client`).

- [ ] **Step 4: Implementar**

`frontend/api_client.py`:
```python
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
```

`frontend/auth.py`:
```python
"""Sessão do usuário no Streamlit: o JWT fica em st.session_state."""

from collections.abc import Callable

import streamlit as st

from api_client import ApiClient, ApiErro, NaoAutenticado

CHAVE_TOKEN = "token"
CHAVE_USUARIO = "usuario"

# Ponto de injeção para testes: fábrica do cliente da API.
fabrica_cliente: Callable[..., ApiClient] = ApiClient


def cliente_api() -> ApiClient:
    return fabrica_cliente(token=st.session_state.get(CHAVE_TOKEN))


def esta_logado() -> bool:
    return bool(st.session_state.get(CHAVE_TOKEN))


def iniciar_sessao(resposta_login: dict) -> None:
    st.session_state[CHAVE_TOKEN] = resposta_login["access_token"]
    st.session_state[CHAVE_USUARIO] = resposta_login["usuario"]


def encerrar_sessao() -> None:
    for chave in (CHAVE_TOKEN, CHAVE_USUARIO):
        st.session_state.pop(chave, None)


def barra_lateral_usuario() -> None:
    usuario = st.session_state.get(CHAVE_USUARIO) or {}
    st.sidebar.markdown(f"Olá, **{usuario.get('nome_completo', '')}**")
    if st.sidebar.button("Sair", key="botao_sair"):
        encerrar_sessao()
        st.rerun()


def exigir_login() -> ApiClient:
    """Use no topo de cada página protegida (depois de st.set_page_config)."""
    if not esta_logado():
        st.warning("Faça login na página inicial (Home) para acessar esta página.")
        st.stop()
    barra_lateral_usuario()
    return cliente_api()


def tratar_erro(erro: ApiErro) -> None:
    """Mostra o erro da API e interrompe a página. Sessão expirada → desloga."""
    if isinstance(erro, NaoAutenticado):
        encerrar_sessao()
        st.warning("Sua sessão expirou. Faça login novamente na página inicial (Home).")
    else:
        st.error(erro.detail)
    st.stop()
```

`frontend/Home.py`:
```python
import streamlit as st

from api_client import ApiErro
from auth import barra_lateral_usuario, cliente_api, esta_logado, iniciar_sessao

st.set_page_config(page_title="Holder · Retenção de clientes", layout="centered")
st.title("Holder — Fila de retenção de clientes")

if esta_logado():
    barra_lateral_usuario()
    usuario = st.session_state["usuario"]
    st.success(f"Você está conectado como **{usuario['usuario']}**.")
    st.markdown(
        "Use o menu lateral para abrir o **Dashboard** (com quem falar, por quê e em que ordem), "
        "a lista de **Clientes** ou a **Análise mensal**."
    )
    st.stop()

aba_entrar, aba_cadastrar = st.tabs(["Entrar", "Criar conta"])

with aba_entrar:
    usuario = st.text_input("Usuário", key="login_usuario")
    senha = st.text_input("Senha", type="password", key="login_senha")
    if st.button("Entrar", type="primary", key="botao_entrar"):
        resposta = None
        if not usuario or not senha:
            st.error("Informe usuário e senha.")
        else:
            try:
                resposta = cliente_api().login(usuario, senha)
            except ApiErro as erro:
                st.error(erro.detail)
        if resposta:
            iniciar_sessao(resposta)
            st.rerun()

with aba_cadastrar:
    nome = st.text_input("Nome completo", key="cadastro_nome")
    novo_usuario = st.text_input(
        "Usuário",
        key="cadastro_usuario",
        help="3 a 50 caracteres: letras, números, ponto, hífen ou sublinhado.",
    )
    nova_senha = st.text_input(
        "Senha",
        type="password",
        key="cadastro_senha",
        help="8 a 128 caracteres, com ao menos uma letra e um número.",
    )
    confirmacao = st.text_input("Confirme a senha", type="password", key="cadastro_confirmacao")
    if st.button("Criar conta", type="primary", key="botao_cadastrar"):
        resposta = None
        if nova_senha != confirmacao:
            st.error("As senhas não conferem.")
        else:
            try:
                api = cliente_api()
                api.cadastrar(nome, novo_usuario, nova_senha)
                resposta = api.login(novo_usuario, nova_senha)
            except ApiErro as erro:
                st.error(erro.detail)
        if resposta:
            iniciar_sessao(resposta)
            st.rerun()
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd frontend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam. Se algum seletor do `AppTest` não existir na versão instalada (ex.: `at.sidebar.markdown`), ajuste **o teste** para a API equivalente do `streamlit.testing.v1` da versão instalada, sem enfraquecer o que ele verifica.
Run: `cd frontend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 6: Commit**

```bash
git add frontend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(frontend): cliente da API, sessão JWT e tela de login/cadastro em Streamlit" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12: Front Streamlit — páginas Dashboard, Clientes e Análise mensal

**Files:**
- Create: `frontend/formatacao.py`, `frontend/pages/1_Dashboard.py`, `frontend/pages/2_Clientes.py`, `frontend/pages/3_Analise_Mensal.py`
- Test: `frontend/tests/test_formatacao.py`, `frontend/tests/test_paginas.py`

**Interfaces:**
- Consumes: `ApiClient`, `ApiErro`, `exigir_login`, `tratar_erro`, fixture `api_falsa` (Task 11). Formatos de resposta da API: `ResumoDashboard`, `list[ItemFila]`, `Pagina[ClienteResumo]`, `ClienteDetalhe`, `HistoricoCliente`, `list[VariavelMetrica]`, `list[PontoMensal]` (Tasks 9–10).
- Produces: `formatacao.brl(valor) -> str`, `formatacao.percentual(valor, casas=0) -> str`, `formatacao.ROTULO_FAIXA`; três páginas Streamlit.

- [ ] **Step 1: Escrever os testes que falham**

`frontend/tests/test_formatacao.py`:
```python
from formatacao import ROTULO_FAIXA, brl, percentual


def test_brl_formata_no_padrao_brasileiro():
    assert brl(1234.5) == "R$ 1.234,50"
    assert brl(275000) == "R$ 275.000,00"
    assert brl(None) == "—"


def test_percentual():
    assert percentual(0.4567) == "46%"
    assert percentual(0.4567, casas=1) == "45,7%"
    assert percentual(None) == "—"


def test_rotulos_de_faixa():
    assert ROTULO_FAIXA["ATENCAO"] == "Atenção"
    assert set(ROTULO_FAIXA) == {"CRITICO", "ATENCAO", "MONITORAR", "SAUDAVEL"}
```

`frontend/tests/test_paginas.py`:
```python
from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGINAS = Path(__file__).resolve().parents[1] / "pages"
DASHBOARD = str(PAGINAS / "1_Dashboard.py")
CLIENTES = str(PAGINAS / "2_Clientes.py")
ANALISE = str(PAGINAS / "3_Analise_Mensal.py")

RESUMO = {
    "mes_referencia": "2026-06-01",
    "executado_em": "2026-09-19T12:00:00",
    "clientes_ativos": 58,
    "receita_ativa": 700000.0,
    "receita_em_risco": 12000.0,
    "qtd_na_fila": 1,
    "por_faixa": {"CRITICO": 0, "ATENCAO": 1, "MONITORAR": 15, "SAUDAVEL": 42},
    "por_dimensao": {"ATENDIMENTO": 5, "SLA": 3, "ENGAJAMENTO": 2, "FINANCEIRO": 1, "SATISFACAO": 9},
}
ITEM_FILA = {
    "posicao": 1,
    "cliente_id": "C080",
    "segmento": "Saude",
    "plano": "ENTERPRISE",
    "porte": "GRANDE",
    "valor_mensal": 20924.0,
    "score_risco": 0.45,
    "faixa": "ATENCAO",
    "receita_em_risco": 9360.0,
    "qtd_dimensoes_afetadas": 5,
    "principais_motivos": ["Chamados reabertos subiram 214% nos últimos 3 meses"],
    "acao_recomendada": {
        "codigo": "COMITE_RETENCAO",
        "titulo": "Ação coordenada de retenção",
        "responsavel": "EXECUTIVO",
        "prazo_dias": 7,
    },
    "ultimo_contato": None,
}
CLIENTE_RESUMO = {
    "cliente_id": "C080",
    "segmento": "Saude",
    "porte": "GRANDE",
    "plano": "ENTERPRISE",
    "valor_mensal": 20924.0,
    "sla_contratado_h": 6,
    "inicio_contrato": "2021-01-01",
    "situacao": "ATIVO",
    "mes_cancelamento": None,
    "score_risco": 0.45,
    "faixa": "ATENCAO",
    "receita_em_risco": 9360.0,
    "posicao_fila": 1,
}
DETALHE = {
    **CLIENTE_RESUMO,
    "avaliacao": {
        "mes_referencia": "2026-06-01",
        "score_risco": 0.45,
        "faixa": "ATENCAO",
        "qtd_dimensoes_afetadas": 5,
        "receita_em_risco": 9360.0,
        "posicao_fila": 1,
        "evidencias": [
            {
                "codigo_sinal": "REABERTOS_TENDENCIA",
                "dimensao": "ATENDIMENTO",
                "texto": "Chamados reabertos subiram 214% nos últimos 3 meses",
                "valor_observado": 2.14,
                "linha_base": 0.7,
                "variacao_pct": 2.14,
                "meses_persistencia": 3,
                "contribuicao": 0.1,
            }
        ],
        "acao_recomendada": {
            "codigo": "COMITE_RETENCAO",
            "titulo": "Ação coordenada de retenção",
            "responsavel": "EXECUTIVO",
            "prazo_dias": 7,
            "descricao": "Montar comitê.",
        },
    },
}
MES = {
    "chamados_abertos": 5,
    "chamados_criticos": 1,
    "chamados_reabertos": 1,
    "chamados_dentro_sla": 4,
    "pct_sla_cumprido": 80.0,
    "tempo_medio_resolucao_h": 10.0,
    "reclamacoes_formais": 0,
    "uso_plataforma_pct": 75.0,
    "dias_atraso_pagamento": 0,
    "reunioes_previstas": 1,
    "reunioes_realizadas": 1,
}
HISTORICO = {
    "cliente_id": "C080",
    "atendimento": [
        {**MES, "mes_ref": "2026-05-01"},
        {**MES, "mes_ref": "2026-06-01", "pct_sla_cumprido": None},
    ],
    "nps": [
        {"mes_ref": "2026-03-01", "respondeu": True, "nota_nps": 8, "classificacao_nps": "NEUTRO"},
        {"mes_ref": "2026-06-01", "respondeu": False, "nota_nps": None, "classificacao_nps": "SEM_RESPOSTA"},
    ],
}


def _logado(caminho: str) -> AppTest:
    at = AppTest.from_file(caminho, default_timeout=30)
    at.session_state["token"] = "tok"
    at.session_state["usuario"] = {"id": 1, "nome_completo": "Maria", "usuario": "maria"}
    return at


def test_pagina_protegida_sem_login_pede_login(api_falsa):
    at = AppTest.from_file(DASHBOARD, default_timeout=30).run()

    assert not at.exception
    assert "Faça login" in at.warning[0].value
    assert api_falsa.requisicoes == []


def test_dashboard_mostra_kpis_e_fila(api_falsa):
    api_falsa.responder("GET", "/dashboard/resumo", 200, RESUMO)
    api_falsa.responder("GET", "/dashboard/fila", 200, [ITEM_FILA])

    at = _logado(DASHBOARD).run()

    assert not at.exception
    rotulos = [m.label for m in at.metric]
    assert "Receita em risco (mês)" in rotulos
    assert len(at.dataframe) >= 1


def test_dashboard_sem_analise_orienta_importacao(api_falsa):
    vazio = {**RESUMO, "mes_referencia": None, "executado_em": None, "qtd_na_fila": 0}
    api_falsa.responder("GET", "/dashboard/resumo", 200, vazio)
    api_falsa.responder("GET", "/dashboard/fila", 200, [])

    at = _logado(DASHBOARD).run()

    assert not at.exception
    assert "Nenhuma análise" in at.info[0].value


def test_sessao_expirada_desloga_e_avisa(api_falsa):
    api_falsa.responder("GET", "/dashboard/resumo", 401, {"detail": "Token inválido ou expirado"})

    at = _logado(DASHBOARD).run()

    assert not at.exception
    assert any("sessão expirou" in w.value for w in at.warning)
    assert "token" not in at.session_state


def test_clientes_lista_e_detalhe(api_falsa):
    api_falsa.responder(
        "GET", "/clientes", 200, {"itens": [CLIENTE_RESUMO], "total": 1, "pagina": 1, "tamanho": 20}
    )
    api_falsa.responder("GET", "/clientes/C080", 200, DETALHE)
    api_falsa.responder("GET", "/clientes/C080/historico", 200, HISTORICO)

    at = _logado(CLIENTES).run()

    assert not at.exception
    assert len(at.dataframe) >= 1
    textos = " ".join(m.value for m in at.markdown)
    assert "Chamados reabertos subiram 214%" in textos


def test_clientes_sem_resultado(api_falsa):
    api_falsa.responder("GET", "/clientes", 200, {"itens": [], "total": 0, "pagina": 1, "tamanho": 20})

    at = _logado(CLIENTES).run()

    assert not at.exception
    assert "Nenhum cliente" in at.info[0].value


def test_analise_mensal(api_falsa):
    api_falsa.responder(
        "GET", "/metricas/variaveis", 200, [{"codigo": "pct_sla_cumprido", "rotulo": "SLA cumprido (%)"}]
    )
    api_falsa.responder(
        "GET",
        "/metricas/mensal",
        200,
        [{"mes_ref": "2025-01-01", "valor": 80.0}, {"mes_ref": "2025-02-01", "valor": 75.5}],
    )

    at = _logado(ANALISE).run()

    assert not at.exception
    assert api_falsa.requisicoes[-1].url.params["variavel"] == "pct_sla_cumprido"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && ../.venv/Scripts/python -m pytest tests/test_formatacao.py tests/test_paginas.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'formatacao'` e arquivos de página inexistentes).

- [ ] **Step 3: Implementar formatação**

`frontend/formatacao.py`:
```python
ROTULO_FAIXA = {
    "CRITICO": "Crítico",
    "ATENCAO": "Atenção",
    "MONITORAR": "Monitorar",
    "SAUDAVEL": "Saudável",
}
ROTULO_RESPONSAVEL = {
    "CS": "Customer Success",
    "TECNICO": "Técnico",
    "FINANCEIRO": "Financeiro",
    "EXECUTIVO": "Executivo",
}


def _padrao_br(texto: str) -> str:
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def brl(valor: float | None) -> str:
    if valor is None:
        return "—"
    return "R$ " + _padrao_br(f"{valor:,.2f}")


def percentual(valor: float | None, casas: int = 0) -> str:
    if valor is None:
        return "—"
    return _padrao_br(f"{valor * 100:.{casas}f}") + "%"
```

- [ ] **Step 4: Implementar as páginas**

`frontend/pages/1_Dashboard.py`:
```python
import pandas as pd
import streamlit as st

from api_client import ApiErro
from auth import exigir_login, tratar_erro
from formatacao import ROTULO_FAIXA, ROTULO_RESPONSAVEL, brl

st.set_page_config(page_title="Dashboard · Holder", layout="wide")
api = exigir_login()

with st.sidebar:
    if st.button("Reprocessar análise", key="botao_reprocessar"):
        try:
            api.executar_analise()
        except ApiErro as erro:
            tratar_erro(erro)
        st.rerun()

st.title("Com quais clientes falar primeiro?")

try:
    resumo = api.resumo_dashboard()
    fila = api.fila(limite=10)
except ApiErro as erro:
    tratar_erro(erro)

if resumo["mes_referencia"] is None:
    st.info(
        "Nenhuma análise executada ainda. Importe a planilha no backend "
        "(`python -m scripts.importar_base`) e recarregue esta página."
    )
    st.stop()

st.caption(
    f"Mês de referência: {resumo['mes_referencia']} · "
    f"análise executada em {resumo['executado_em']} (UTC)"
)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Clientes ativos", resumo["clientes_ativos"])
col2.metric("Receita ativa (mês)", brl(resumo["receita_ativa"]))
col3.metric("Receita em risco (mês)", brl(resumo["receita_em_risco"]))
col4.metric("Na fila de atenção", resumo["qtd_na_fila"])

st.subheader("Fila priorizada")
if not fila:
    st.success("Nenhum cliente em faixa Crítico ou Atenção no momento.")
else:
    tabela = pd.DataFrame(
        [
            {
                "Posição": item["posicao"],
                "Cliente": item["cliente_id"],
                "Segmento": item["segmento"],
                "Plano": item["plano"].title(),
                "Faixa": ROTULO_FAIXA[item["faixa"]],
                "Score": item["score_risco"],
                "Receita em risco": brl(item["receita_em_risco"]),
                "Por quê": " · ".join(item["principais_motivos"]),
                "O que fazer": (item["acao_recomendada"] or {}).get("titulo", "—"),
                "Responsável": ROTULO_RESPONSAVEL.get(
                    (item["acao_recomendada"] or {}).get("responsavel", ""), "—"
                ),
            }
            for item in fila
        ]
    )
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0.0, max_value=1.0, format="%.2f"
            ),
            "Por quê": st.column_config.TextColumn("Por quê", width="large"),
        },
    )

col_faixa, col_dimensao = st.columns(2)
with col_faixa:
    st.markdown("**Clientes ativos por faixa de risco**")
    st.bar_chart(pd.Series({ROTULO_FAIXA[f]: q for f, q in resumo["por_faixa"].items()}))
with col_dimensao:
    st.markdown("**Clientes com sinal disparado, por dimensão**")
    st.bar_chart(pd.Series(resumo["por_dimensao"]))
```

`frontend/pages/2_Clientes.py`:
```python
import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import ApiErro
from auth import exigir_login, tratar_erro
from formatacao import ROTULO_FAIXA, ROTULO_RESPONSAVEL, brl

st.set_page_config(page_title="Clientes · Holder", layout="wide")
api = exigir_login()

ROTULO_ORDEM = {
    "receita_em_risco": "Receita em risco",
    "score": "Score de risco",
    "valor_mensal": "Valor mensal",
    "cliente_id": "Código do cliente",
}
SEGMENTOS = ["Educacao", "Industria", "Logistica", "Saude", "Servicos", "Varejo"]


def _ou_nada(valor: str) -> str | None:
    return None if valor in ("Todas", "Todos") else valor


def _grafico(df: pd.DataFrame, colunas: list[str], titulo: str, eixo_y: str):
    figura = px.line(
        df,
        x="mes_ref",
        y=colunas,
        markers=True,
        title=titulo,
        labels={"mes_ref": "Mês", "value": eixo_y, "variable": ""},
        template="plotly_white",
    )
    figura.update_layout(
        xaxis_tickformat="%b/%Y",
        hovermode="x unified",
        height=320,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        legend={"orientation": "h"},
    )
    return figura


with st.sidebar:
    st.header("Filtros")
    situacao = st.selectbox("Situação", ["Todas", "ATIVO", "CANCELADO"], key="f_situacao")
    faixa = st.selectbox(
        "Faixa de risco",
        ["Todas", *ROTULO_FAIXA],
        format_func=lambda v: ROTULO_FAIXA.get(v, v),
        key="f_faixa",
    )
    plano = st.selectbox("Plano", ["Todos", "ESSENCIAL", "AVANCADO", "ENTERPRISE"], key="f_plano")
    segmento = st.selectbox("Segmento", ["Todos", *SEGMENTOS], key="f_segmento")
    busca = st.text_input("Buscar (código ou segmento)", key="f_busca")
    ordenar = st.selectbox(
        "Ordenar por", list(ROTULO_ORDEM), format_func=ROTULO_ORDEM.get, key="f_ordenar"
    )
    pagina = st.number_input("Página", min_value=1, value=1, step=1, key="f_pagina")

st.title("Clientes")

try:
    resultado = api.listar_clientes(
        situacao=_ou_nada(situacao),
        faixa=_ou_nada(faixa),
        plano=_ou_nada(plano),
        segmento=_ou_nada(segmento),
        busca=busca.strip() or None,
        ordenar=ordenar,
        pagina=int(pagina),
        tamanho=20,
    )
except ApiErro as erro:
    tratar_erro(erro)

st.caption(f"{resultado['total']} clientes encontrados · página {resultado['pagina']}")
if not resultado["itens"]:
    st.info("Nenhum cliente encontrado com esses filtros.")
    st.stop()

st.dataframe(
    pd.DataFrame(
        [
            {
                "Cliente": c["cliente_id"],
                "Segmento": c["segmento"],
                "Plano": c["plano"].title(),
                "Valor mensal": brl(c["valor_mensal"]),
                "Situação": (c["situacao"] or "—").title(),
                "Faixa": ROTULO_FAIXA.get(c["faixa"] or "", "—"),
                "Score": c["score_risco"],
                "Receita em risco": brl(c["receita_em_risco"]),
                "Posição na fila": c["posicao_fila"],
            }
            for c in resultado["itens"]
        ]
    ),
    hide_index=True,
    width="stretch",
)

st.divider()
escolhido = st.selectbox(
    "Ver detalhe do cliente", [c["cliente_id"] for c in resultado["itens"]], key="cliente_escolhido"
)
try:
    detalhe = api.cliente(escolhido)
    historico = api.historico(escolhido)
except ApiErro as erro:
    tratar_erro(erro)

st.subheader(f"{detalhe['cliente_id']} · {detalhe['segmento']} · {detalhe['plano'].title()}")
avaliacao = detalhe["avaliacao"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Valor mensal", brl(detalhe["valor_mensal"]))
col2.metric("Situação", (detalhe["situacao"] or "—").title())
col3.metric("Faixa", ROTULO_FAIXA[avaliacao["faixa"]] if avaliacao else "—")
col4.metric("Posição na fila", (avaliacao or {}).get("posicao_fila") or "—")

if avaliacao is None:
    st.info("Cliente sem avaliação de risco (apenas clientes ativos são avaliados).")
else:
    st.markdown("**Por quê**")
    if avaliacao["evidencias"]:
        st.markdown("\n".join(f"- {e['texto']}" for e in avaliacao["evidencias"]))
    else:
        st.markdown("- Nenhum sinal de risco disparado.")
    acao = avaliacao["acao_recomendada"]
    if acao:
        st.markdown("**O que fazer**")
        st.info(
            f"**{acao['titulo']}** — responsável: "
            f"{ROTULO_RESPONSAVEL.get(acao['responsavel'], acao['responsavel'])}, "
            f"prazo: {acao['prazo_dias']} dias\n\n{acao['descricao']}"
        )

atendimento = pd.DataFrame(historico["atendimento"])
if not atendimento.empty:
    atendimento["mes_ref"] = pd.to_datetime(atendimento["mes_ref"])
    grafico1, grafico2 = st.columns(2)
    grafico1.plotly_chart(
        _grafico(atendimento, ["uso_plataforma_pct"], "Uso da plataforma", "%"), width="stretch"
    )
    grafico2.plotly_chart(
        _grafico(atendimento, ["pct_sla_cumprido"], "SLA cumprido", "%"), width="stretch"
    )
    grafico3, grafico4 = st.columns(2)
    grafico3.plotly_chart(
        _grafico(
            atendimento,
            ["chamados_abertos", "chamados_criticos", "chamados_reabertos"],
            "Chamados",
            "qtd",
        ),
        width="stretch",
    )
    nps = pd.DataFrame(historico["nps"])
    if not nps.empty:
        nps["mes_ref"] = pd.to_datetime(nps["mes_ref"])
        respondidas = nps[nps["respondeu"]]
        grafico4.plotly_chart(
            _grafico(respondidas, ["nota_nps"], "Nota de NPS (pesquisas respondidas)", "nota"),
            width="stretch",
        )
        sem_resposta = int((~nps["respondeu"]).sum())
        if sem_resposta:
            grafico4.caption(f"{sem_resposta} pesquisa(s) sem resposta no período.")
```

`frontend/pages/3_Analise_Mensal.py`:
```python
import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import ApiErro
from auth import exigir_login, tratar_erro

st.set_page_config(page_title="Análise mensal · Holder", layout="wide")
api = exigir_login()

try:
    variaveis = api.variaveis_metricas()
except ApiErro as erro:
    tratar_erro(erro)
rotulos = {v["codigo"]: v["rotulo"] for v in variaveis}
nomes_agregacao = {"media": "Média", "soma": "Soma"}

with st.sidebar:
    st.header("Configurações do gráfico")
    variavel = st.selectbox("Métrica", list(rotulos), format_func=rotulos.get, key="m_variavel")
    agregacao = st.radio(
        "Cálculo", list(nomes_agregacao), format_func=nomes_agregacao.get, key="m_agregacao"
    )

st.title("Evolução mensal da carteira")

try:
    pontos = api.metrica_mensal(variavel, agregacao)
except ApiErro as erro:
    tratar_erro(erro)

if not pontos:
    st.info("Sem dados para esta métrica. Importe a planilha no backend.")
    st.stop()

df = pd.DataFrame(pontos)
df["mes_ref"] = pd.to_datetime(df["mes_ref"])
titulo = f"{rotulos[variavel]} — {nomes_agregacao[agregacao]} mensal"
figura = px.line(
    df,
    x="mes_ref",
    y="valor",
    markers=True,
    title=titulo,
    labels={"mes_ref": "Mês de referência", "valor": rotulos[variavel]},
    template="plotly_white",
)
figura.update_traces(
    line={"width": 4, "color": "#0156FC"},
    marker={"size": 10, "color": "#000A1E"},
    fill="tozeroy",
    fillcolor="rgba(1, 86, 252, 0.08)",
)
figura.update_layout(xaxis_tickformat="%b/%Y", hovermode="x unified")
st.plotly_chart(figura, width="stretch")

with st.expander("Ver dados em tabela"):
    st.dataframe(
        df.rename(columns={"mes_ref": "Mês", "valor": rotulos[variavel]}),
        hide_index=True,
        width="stretch",
    )
```

- [ ] **Step 5: Rodar e ver passar**

Run: `cd frontend && ../.venv/Scripts/python -m pytest -v`
Expected: todos passam. Se `width="stretch"` não for aceito por `st.dataframe`/`st.plotly_chart` na versão instalada, troque por `use_container_width=True` (e vice-versa se houver aviso de depreciação) — confira com `../.venv/Scripts/python -c "import streamlit; print(streamlit.__version__)"`.
Run: `cd frontend && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`

- [ ] **Step 6: Commit**

```bash
git add frontend
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "feat(frontend): páginas de dashboard com fila, clientes com detalhe e análise mensal" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 13: Documentação e verificação ponta a ponta

**Files:**
- Modify: `README.md` (raiz)
- Create: `.claude/launch.json`

**Interfaces:**
- Consumes: tudo das tasks anteriores.
- Produces: README com passo a passo; configurações de launch para backend (porta 8000) e frontend (porta 8501).

- [ ] **Step 1: Escrever o README da raiz**

Substitua `README.md` por:
````markdown
# Holder — Fila de retenção de clientes (INOVAAPPS 2026)

MVP que identifica, entre os clientes **ativos**, quais estão em risco de cancelar, mostra
**a evidência** e **o que fazer**, numa fila priorizada por receita em risco.

- `backend/` — API FastAPI em MVC (models, repositories, services, controllers, schemas).
- `frontend/` — Streamlit multipágina (login/cadastro, dashboard, clientes, análise mensal) que consome só a API.
- `assistente-consultas/` — widget React (independente deste MVP).
- `app.py`, `ingestao.py`, `analise_sla.py` — scripts exploratórios anteriores (legado).

## Pré-requisitos

Python 3.12+ (no Windows use o launcher `py`).

## Instalação

```bash
py -m venv .venv
.venv/Scripts/python -m pip install -e "backend[dev]" -r frontend/requirements.txt
```
(Linux/macOS: `python3 -m venv .venv` e `.venv/bin/python`.)

## Backend

```bash
cd backend
cp .env.example .env
../.venv/Scripts/python -m scripts.importar_base      # importa ../INOVAAPPS_base_de_dados.xlsx e roda a análise
../.venv/Scripts/python -m uvicorn app.main:create_app --factory --reload --port 8000
```

- Swagger: http://localhost:8000/docs
- Reprocessar a análise: `../.venv/Scripts/python -m scripts.rodar_analise [AAAA-MM]`

## Frontend

```bash
cd frontend
../.venv/Scripts/python -m streamlit run Home.py --server.port 8501
```

Abra http://localhost:8501, crie uma conta na aba **Criar conta** e navegue pelo menu lateral.
A URL da API pode ser trocada com a variável `API_URL` (padrão `http://localhost:8000/api`).

## Testes e qualidade

```bash
cd backend && ../.venv/Scripts/python -m pytest && ../.venv/Scripts/python -m ruff check .
cd frontend && ../.venv/Scripts/python -m pytest && ../.venv/Scripts/python -m ruff check .
```

## Endpoints (prefixo `/api`)

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/health` | não | status da API e do banco |
| POST | `/auth/cadastro` | não | cria usuário |
| POST | `/auth/login` | não | retorna JWT |
| GET | `/auth/me` | sim | usuário logado |
| GET | `/dashboard/resumo` | sim | KPIs da última análise |
| GET | `/dashboard/fila?limite=10` | sim | fila priorizada com motivos e ação |
| GET | `/clientes` | sim | lista paginada com filtros e ordenação |
| GET | `/clientes/{id}` | sim | cadastro + avaliação + evidências + ação |
| GET | `/clientes/{id}/historico` | sim | séries mensais e NPS |
| GET | `/metricas/variaveis` | sim | métricas disponíveis |
| GET | `/metricas/mensal` | sim | média/soma mensal da carteira |
| GET | `/sinais` | sim | catálogo de sinais |
| GET | `/acoes-recomendadas` | sim | playbook |
| POST | `/analise/executar` | sim | roda a análise de produção |
| POST | `/importacao` | sim | upload do xlsx + análise |

## Motor de risco (MVP)

1. **Indicadores** por cliente no mês de referência (só dados até aquele mês): média de 3 meses,
   linha de base dos 6 meses anteriores, variação e meses seguidos de piora.
2. **10 sinais** (seed em `configuracoes_sinal`) com limiares do planejamento e peso igual (0,10).
3. **Score** = Σ peso × intensidade; faixas CRÍTICO ≥ 0,55, ATENÇÃO ≥ 0,30, MONITORAR ≥ 0,15.
   Com menos de 2 dimensões afetadas, a faixa máxima é MONITORAR (anti-alarme-falso).
4. **Ação recomendada** pela dimensão dominante (ou comitê com 3+ dimensões).
5. **Fila**: CRÍTICO e ATENÇÃO, por faixa e receita em risco (score × valor mensal), até `CAPACIDADE_FILA`.

Calibração de pesos, backtest e registro de contatos ficam para a próxima fase.

## Trocar para SQL Server

Os models usam apenas tipos genéricos. Instale o extra `pip install -e "backend[sqlserver]"` e
defina `DATABASE_URL` como no comentário do `backend/.env.example`.
````

- [ ] **Step 2: Criar as configurações de launch**

`.claude/launch.json`:
```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "backend",
      "runtimeExecutable": "cmd",
      "runtimeArgs": ["/c", "cd backend && ..\\.venv\\Scripts\\python -m uvicorn app.main:create_app --factory --port 8000"],
      "port": 8000
    },
    {
      "name": "frontend",
      "runtimeExecutable": "cmd",
      "runtimeArgs": ["/c", "cd frontend && ..\\.venv\\Scripts\\python -m streamlit run Home.py --server.port 8501 --server.headless true"],
      "port": 8501
    }
  ]
}
```

- [ ] **Step 3: Verificação completa**

Run: `cd backend && ../.venv/Scripts/python -m pytest -q && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`
Expected: todos os testes passam; ruff limpo.

Run: `cd frontend && ../.venv/Scripts/python -m pytest -q && ../.venv/Scripts/python -m ruff check . && ../.venv/Scripts/python -m ruff format --check .`
Expected: todos os testes passam; ruff limpo.

Run (a partir de `backend/`, com banco em arquivo temporário para não sujar o repo): `DATABASE_URL=sqlite:///./verificacao.db ../.venv/Scripts/python -m scripts.importar_base && rm -f verificacao.db`
Expected: imprime `clientes: 80`, `atendimentos_mensais: 1295`, `pesquisas_nps: 422`, nenhum AVISO e `Análise concluída: mês 2026-06-01, 58 clientes avaliados, N na fila.` com N ≥ 1.

- [ ] **Step 4: Commit**

```bash
git add README.md .claude/launch.json
git -c user.name="Alan Vival" -c user.email="alan.vival181@gmail.com" commit -m "docs: README com passo a passo do MVP e configurações de launch" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
