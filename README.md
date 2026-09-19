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
