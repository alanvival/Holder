# MVP — Backend FastAPI (MVC) + Front Streamlit

Data: 2026-09-19
Referências: `PLANEJAMENTO_BACKEND.md` (plano completo, 10 fases) e `entidades_base_de_dados.md` (entidades da planilha).

## 1. Objetivo

Entregar um MVP utilizável em que o usuário:

1. cria conta e faz login numa interface Streamlit;
2. vê a **fila priorizada** de clientes ativos em risco (com quem falar, por quê, em que ordem);
3. consulta clientes, detalhe (evidências + ação recomendada) e histórico mensal;
4. consulta a evolução mensal agregada de qualquer métrica (o gráfico do `app.py` atual).

Tudo servido por uma API FastAPI organizada em MVC, que é a única fonte de dados do Streamlit.

### Decisões tomadas (divergências do plano completo)

| Tema | Plano completo | MVP |
|---|---|---|
| Front | React separado | Streamlit multipágina consumindo a API (React `assistente-consultas` intocado) |
| Banco | SQL Server + Alembic + docker-compose | SQLite em arquivo via `DATABASE_URL`; `Base.metadata.create_all` no startup. Models usam só tipos genéricos → troca para SQL Server = mudar a URL + instalar `pyodbc` |
| Python | 3.12 | 3.12+ (ambiente local tem 3.14) |
| Motor de risco | Indicadores persistidos, calibração, backtest | Indicadores em memória, 10 sinais seed com limiares do plano e pesos fixos; sem calibração/backtest |
| Contatos | `registros_contato` + endpoints | Fora; `ultimo_contato` sempre `null` |

Arquivos existentes na raiz (`app.py`, `ingestao.py`, `analise_sla.py`, `INOVAAPPS_base_de_dados.xlsx`) permanecem; o README da raiz passa a documentar o novo fluxo.

## 2. Arquitetura

```
backend/
  app/
    main.py            # cria app, CORS, routers, handlers de erro, create_all no startup
    dependencies.py    # get_db, get_usuario_atual (HTTPBearer), fábricas de services
    core/
      config.py        # Settings (pydantic-settings)
      database.py      # engine, SessionLocal, Base
      security.py      # HasherSenha (pwdlib argon2), GerenciadorToken (PyJWT HS256)
      enums.py         # enums de domínio
      exceptions.py    # exceções de domínio + registro dos handlers HTTP
    models/            # SQLAlchemy 2.0 Mapped[]
    schemas/           # DTOs Pydantic v2 (a "View")
    repositories/      # única camada com queries; recebe Session
    services/          # regras de negócio; risco/ contém funções puras
    controllers/       # routers FastAPI; chamam apenas services
  scripts/
    importar_base.py   # importa o xlsx e roda a análise
    rodar_analise.py   # roda só a análise de produção
  tests/
    conftest.py        # SQLite em memória (StaticPool), override de get_db, TestClient
    unit/
    integration/
  pyproject.toml
  .env.example
frontend/
  Home.py              # login/cadastro
  pages/1_Dashboard.py
  pages/2_Clientes.py
  pages/3_Analise_Mensal.py
  api_client.py        # única camada HTTP (httpx)
  auth.py              # exigir_login(), sessão
  .streamlit/config.toml
  requirements.txt
  tests/
```

### Regras de dependência (obrigatórias)

- Controller chama **apenas** services; sem regra de negócio.
- Service chama repositories e outros services; nunca importa `fastapi` (só `dependencies.py` o faz).
- Repository recebe `Session` e só faz I/O de banco.
- `pandas` só em `services/` e `scripts/`.
- Services recebem dependências pelo construtor.
- Funções analíticas (indicadores, score, recomendação, priorização) são puras.
- Valores de negócio (horizonte, capacidade da fila, limiares de faixa, persistência mínima) ficam em `Settings` ou `configuracoes_sinal`.

## 3. Configuração (`Settings`)

| Variável | Default |
|---|---|
| `DATABASE_URL` | `sqlite:///./holder.db` |
| `JWT_SECRET` | `trocar-em-producao` |
| `JWT_EXPIRA_MINUTOS` | `480` |
| `CORS_ORIGENS` | `http://localhost:8501,http://localhost:5173` |
| `CAPACIDADE_FILA` | `10` |
| `LIMIAR_CRITICO` / `LIMIAR_ATENCAO` / `LIMIAR_MONITORAR` | `0.55` / `0.30` / `0.15` |
| `PERSISTENCIA_MIN_MESES` | `2` |
| `CAMINHO_XLSX` | `../INOVAAPPS_base_de_dados.xlsx` |

Para SQLite, a engine usa `check_same_thread=False`. Para `mssql+pyodbc`, `fast_executemany=True`.

## 4. Modelo de dados

Convenções: tabelas snake_case no plural; `Unicode` para texto livre; `Numeric(12,2)` para dinheiro; `DateTime` em UTC para auditoria; `Date` com dia 1 para meses; enums armazenados como `String` com o nome do membro.

### Enums

- `Porte`: `PEQUENO`, `MEDIO`, `GRANDE`
- `Plano`: `ESSENCIAL`, `AVANCADO`, `ENTERPRISE`
- `SituacaoCliente`: `ATIVO`, `CANCELADO`
- `ClassificacaoNPS`: `PROMOTOR`, `NEUTRO`, `DETRATOR`, `SEM_RESPOSTA`
- `Dimensao`: `ATENDIMENTO`, `SLA`, `ENGAJAMENTO`, `FINANCEIRO`, `SATISFACAO`
- `TipoRegra`: `NIVEL`, `TENDENCIA`, `EVENTO`
- `SentidoPiora`: `AUMENTO`, `QUEDA`
- `FaixaRisco`: `CRITICO`, `ATENCAO`, `MONITORAR`, `SAUDAVEL`
- `TipoExecucao`: `PRODUCAO`, `CALIBRACAO`, `BACKTEST`
- `Responsavel`: `CS`, `TECNICO`, `FINANCEIRO`, `EXECUTIVO`

### Tabelas do MVP

- **`usuarios`**: `id` PK, `nome_completo` Unicode(150), `usuario` Unicode(50) UNIQUE (minúsculas), `senha_hash` Unicode(255), `ativo` bool default true, `criado_em`, `ultimo_login_em` NULL.
- **`clientes`**: `cliente_id` String(10) PK, `segmento` Unicode(50), `porte`, `plano`, `valor_mensal` Numeric(12,2), `sla_contratado_h` int, `inicio_contrato` Date.
- **`situacao_clientes`**: `cliente_id` PK/FK, `situacao`, `mes_cancelamento` Date NULL.
- **`atendimentos_mensais`**: `id` PK, `cliente_id` FK, `mes_ref` Date (índice), `chamados_abertos`, `chamados_criticos`, `chamados_reabertos`, `chamados_dentro_sla` int, `pct_sla_cumprido` Numeric(5,1) NULL, `tempo_medio_resolucao_h` Numeric(6,1), `reclamacoes_formais` int, `uso_plataforma_pct` Numeric(5,1), `dias_atraso_pagamento` int, `reunioes_previstas` int, `reunioes_realizadas` int. UNIQUE (`cliente_id`, `mes_ref`).
- **`pesquisas_nps`**: `id`, `cliente_id` FK, `mes_ref` Date, `respondeu` bool, `nota_nps` int NULL, `classificacao_nps`. UNIQUE (`cliente_id`, `mes_ref`).
- **`configuracoes_sinal`**: conforme plano §5.3 (`codigo` UNIQUE, `dimensao`, `variavel`, `tipo_regra`, `sentido_piora`, `limiar` Numeric(10,4), `metrica` String(20) default `media_3m` — **coluna nova**: qual indicador a regra NIVEL compara (`media_3m` ou `soma_3m`), `persistencia_min_meses`, `peso` Numeric(6,4), `lift`/`cobertura_cancelados`/`taxa_falso_alarme`/`antecedencia_media_meses` NULL, `template_evidencia` Unicode(300), `ativo`, `atualizado_em`).
- **`acoes_recomendadas`**: `id`, `codigo` UNIQUE, `titulo`, `descricao` UnicodeText, `dimensao_gatilho` NULL, `responsavel_sugerido`, `prazo_dias`, `ordem`.
- **`execucoes_analise`**: `id`, `tipo`, `mes_referencia` Date, `versao_modelo` String(20), `parametros_json` UnicodeText, `executado_por_usuario_id` FK NULL, `executado_em`, `qtd_clientes_avaliados`.
- **`avaliacoes_risco`**: `id`, `execucao_id` FK, `cliente_id` FK, `mes_referencia`, `score_risco` Numeric(5,4), `faixa`, `qtd_dimensoes_afetadas`, `receita_em_risco` Numeric(12,2), `posicao_fila` NULL, `acao_recomendada_id` FK NULL. UNIQUE (`execucao_id`, `cliente_id`).
- **`evidencias_risco`**: `id`, `avaliacao_id` FK, `configuracao_sinal_id` FK, `dimensao`, `valor_observado`, `linha_base` NULL, `variacao_pct` NULL, `meses_persistencia`, `contribuicao` Numeric(6,4), `texto` Unicode(300).

Fora do MVP: `indicadores_mensais`, `registros_contato`, `resultados_backtest`.

## 5. Importação (`ImportacaoService`)

`importar(origem: str | Path | bytes) -> RelatorioImportacao`

- Lê as abas `clientes`, `atendimento_mensal`, `pesquisas_nps`, `situacao_clientes` com `pandas.read_excel`.
- Valida colunas esperadas; ausência → `ImportacaoInvalidaError` (HTTP 422).
- Normaliza: `mes_ref`/`mes_cancelamento` `AAAA-MM` → `date(a, m, 1)`; `inicio_contrato` → `date`; NaN → `None`; `nota_nps` via `Int64`; `"Cancelado"` → `CANCELADO`, `"Sem resposta"` → `SEM_RESPOSTA`, `"Medio"` → `MEDIO`, `"Avancado"` → `AVANCADO` (normalização remove acentos, maiúsculas, espaços→`_`). Valor fora do enum → `ImportacaoInvalidaError`.
- Idempotente: numa transação, apaga avaliações/evidências/execuções e as quatro tabelas de origem, e reinsere.
- Garante seeds (sinais e ações) se ausentes.
- Retorna contagens por tabela e avisos de sanidade (esperado: 80 clientes, 1.295 atendimentos, 422 NPS, 22 cancelados).
- Após importar, o chamador (script/controller) dispara `AnaliseService.executar`.

## 6. Motor de risco simples (`services/risco/`)

Todas as funções abaixo são puras.

### 6.1 Indicadores (`indicadores.py`)

`calcular_indicadores(atendimentos: DataFrame, nps: DataFrame, clientes: DataFrame, mes_referencia: date) -> DataFrame`

- Filtra `mes_ref <= mes_referencia` (sem vazamento).
- Variáveis por cliente-mês: `chamados_abertos`, `chamados_criticos`, `chamados_reabertos`, `taxa_reabertura` (NULL se abertos=0), `pct_sla_cumprido` (NULL preservado), `tempo_resolucao_vs_sla` (NULL se abertos=0 — decisão sobre o ponto 2 do documento de entidades), `reclamacoes_formais`, `uso_plataforma_pct`, `dias_atraso_pagamento`, `pct_reunioes_realizadas` (NULL se previstas=0).
- NPS, alinhado ao mês de referência usando só pesquisas ≤ M: `nps_nota` (última nota respondida), `nps_variacao` (última − anterior respondida), `nps_sem_resposta_consecutivas` (pesquisas seguidas sem resposta no fim da série, contando só se já respondeu antes).
- Para cada cliente × variável no mês M (saída: uma linha por cliente × variável):
  - `valor_mes`
  - `media_3m`: média de M−2..M ignorando NULL
  - `soma_3m`: soma de M−2..M ignorando NULL
  - `linha_base_6m`: média de M−8..M−3 ignorando NULL (NULL se não houver dados)
  - `variacao_pct` = (media_3m − linha_base) / max(|linha_base|, 0,5); NULL se linha_base NULL. O denominador mínimo 0,5 (em vez de ε) evita percentuais explosivos quando a base de contagens é ~0
  - `meses_consecutivos_piora`: meses seguidos terminando em M em que `valor_mes` está estritamente pior que a `linha_base_6m` **daquele mês** no sentido de piora da variável (mês com valor ou base NULL interrompe a contagem)

### 6.2 Sinais (`sinais.py`)

Seeds (limiar do plano §6.2), peso inicial 0,10 cada:

| Código | Dimensão | Variável | Regra | Sentido | Limiar | Métrica comparada |
|---|---|---|---|---|---|---|
| REABERTOS_TENDENCIA | ATENDIMENTO | chamados_reabertos | TENDENCIA | AUMENTO | 0,50 | variacao_pct |
| CRITICOS_TENDENCIA | ATENDIMENTO | chamados_criticos | TENDENCIA | AUMENTO | 0,50 | variacao_pct |
| RESOLUCAO_LENTA | SLA | tempo_resolucao_vs_sla | TENDENCIA | AUMENTO | 0,25 | variacao_pct |
| SLA_BAIXO | SLA | pct_sla_cumprido | NIVEL | QUEDA | 65 | media_3m |
| USO_EM_QUEDA | ENGAJAMENTO | uso_plataforma_pct | TENDENCIA | QUEDA | 0,15 | −variacao_pct |
| REUNIOES_CANCELADAS | ENGAJAMENTO | pct_reunioes_realizadas | NIVEL | QUEDA | 0,5 | media_3m |
| ATRASO_PAGAMENTO | FINANCEIRO | dias_atraso_pagamento | NIVEL | AUMENTO | 6 | media_3m |
| RECLAMACOES | SATISFACAO | reclamacoes_formais | NIVEL | AUMENTO | 2 | soma_3m |
| NPS_EM_QUEDA | SATISFACAO | nps_variacao | EVENTO | QUEDA | 2 | −valor_mes |
| NPS_SILENCIO | SATISFACAO | nps_sem_resposta_consecutivas | EVENTO | AUMENTO | 1 | valor_mes |

Regras de disparo:
- **TENDENCIA**: `v = variacao_pct` (ou `−variacao_pct` se QUEDA); dispara se `v ≥ limiar` **e** `meses_consecutivos_piora ≥ persistencia_min_meses`.
- **NIVEL**: compara `media_3m` (ou `soma_3m` para RECLAMACOES); dispara se `x ≥ limiar` (AUMENTO) ou `x ≤ limiar` (QUEDA). A janela de 3 meses já expressa persistência, então NIVEL não exige `meses_consecutivos_piora`.
- **EVENTO**: `v = valor_mes` (ou `−valor_mes` se QUEDA); dispara se `v ≥ limiar`; sem persistência.
- Métrica NULL → não dispara.

Intensidade ∈ [0,1]: `excesso = (x − limiar)/|limiar|` para métricas orientadas a AUMENTO (TENDENCIA, EVENTO, NIVEL-AUMENTO) e `(limiar − x)/|limiar|` para NIVEL-QUEDA; `intensidade = 0,5 + 0,5 × min(1, excesso)`. Ou seja, disparo exatamente no limiar vale 0,5 e satura em 1,0 a 2× o limiar. Limiar 0 não ocorre nos seeds.

Evidência: `template_evidencia` preenchido com `variacao_pct`, `media_3m`, `soma_3m`, `valor_mes`, `linha_base` (ex.: `"Chamados reabertos subiram {variacao_pct:.0%} nos últimos 3 meses"`).

### 6.3 Score (`score.py`)

`calcular_score(disparos: list[Disparo], limiares: LimiaresFaixa) -> ResultadoScore`

- `contribuicao = peso × intensidade`; `score = min(1, Σ contribuicoes)`.
- `qtd_dimensoes_afetadas` = dimensões distintas com ≥1 disparo.
- Faixa por limiares de `Settings`; se `qtd_dimensoes_afetadas < 2`, faixa máxima `MONITORAR`.
- Evidências ordenadas por contribuição desc.

### 6.4 Recomendação (`recomendacao.py`)

`recomendar(evidencias) -> codigo | None` (None quando não há disparo):
1. ≥ 3 dimensões → `COMITE_RETENCAO`
2. dispararam `REUNIOES_CANCELADAS` e `NPS_SILENCIO` → `CONTATO_EXECUTIVO`
3. senão, pela dimensão de maior contribuição somada: ATENDIMENTO/SLA → `REVISAO_TECNICA`; ENGAJAMENTO → `REUNIAO_VALOR`; FINANCEIRO → `CONVERSA_FINANCEIRA`; SATISFACAO → `PLANO_DE_RECUPERACAO`.

Seed das 6 ações com título, descrição, responsável e prazo (7 dias para COMITE_RETENCAO/CONTATO_EXECUTIVO, 15 para as demais).

### 6.5 Priorização (`priorizacao.py`)

`priorizar(itens: list[ItemAvaliado], capacidade: int) -> list[ItemAvaliado]`
- `receita_em_risco = score × valor_mensal` (arredondado a 2 casas).
- Fila: faixa ∈ {CRITICO, ATENCAO}, ordenada por faixa (CRITICO primeiro) e receita em risco desc; `posicao_fila` 1..capacidade; demais `None`.

### 6.6 Orquestração (`services/analise_service.py`)

`executar(mes_referencia: date | None = None, usuario_id: int | None = None) -> ExecucaoAnalise`
1. Default de `mes_referencia`: maior `mes_ref` da base.
2. Carrega dados via repositories, monta DataFrames, calcula indicadores, avalia sinais ativos para cada cliente **ativo** (situação ATIVO), calcula score, recomendação e prioridade.
3. Numa transação grava `execucoes_analise` (tipo PRODUCAO, `versao_modelo="mvp-regras-1"`, parâmetros em JSON), `avaliacoes_risco`, `evidencias_risco`.
4. Loga tempo e quantidade de clientes.

Critério de sanidade com a base real: a fila não pode sair vazia. Validado em protótipo com pesos 0,10: em 2026-06 saem 3 ATENCAO, 15 MONITORAR, 40 SAUDAVEL (fila com 3 clientes: C080, C067, C002).

## 7. Autenticação

Conforme plano §7:
- Cadastro: `nome_completo` 3–150 (strip), `usuario` 3–50 `^[a-zA-Z0-9._-]+$` → minúsculas, `senha` 8–128 com letra e número. 201 `UsuarioResponse` (`id`, `nome_completo`, `usuario`, `criado_em`); 409 "Usuário já cadastrado"; 422 validação.
- Login JSON: 200 `{access_token, token_type:"bearer", expira_em, usuario}`; 401 "Usuário ou senha inválidos" para inexistente e senha errada; 403 inativo; atualiza `ultimo_login_em`. JWT: `sub` (id como string), `usuario`, `iat`, `exp`.
- `GET /auth/me`.
- `get_usuario_atual` com `HTTPBearer(auto_error=False)`: sem token / token inválido / expirado → 401.
- Exceções: `UsuarioJaExisteError` 409, `CredenciaisInvalidasError` 401, `UsuarioInativoError` 403, `TokenInvalidoError` 401, `RecursoNaoEncontradoError` 404, `ImportacaoInvalidaError` 422. Corpo de erro: `{"detail": "<mensagem>"}`.

## 8. Endpoints (prefixo `/api`)

| Método | Rota | Auth | Resposta |
|---|---|---|---|
| GET | `/health` | não | `{status:"ok", banco:"ok"\|"erro"}` |
| POST | `/auth/cadastro` | não | 201 `UsuarioResponse` |
| POST | `/auth/login` | não | 200 `TokenResponse` |
| GET | `/auth/me` | sim | `UsuarioResponse` |
| GET | `/dashboard/resumo` | sim | `ResumoDashboard`: `mes_referencia`, `executado_em`, `clientes_ativos`, `receita_ativa`, `receita_em_risco`, `por_faixa` {faixa: qtd}, `por_dimensao` {dimensao: qtd clientes} |
| GET | `/dashboard/fila?limite=10` | sim | `list[ItemFila]` (formato do plano §8; `principais_motivos` = top 3 textos; `ultimo_contato` null) |
| GET | `/clientes` | sim | `Pagina[ClienteResumo]`: filtros `situacao`, `faixa`, `plano`, `porte`, `segmento`, `busca` (substring em `cliente_id`/`segmento`), `ordenar` (`receita_em_risco`, `score`, `valor_mensal`, `cliente_id`; default `cliente_id`), `pagina` (≥1), `tamanho` (1–100, default 20). `ClienteResumo`: dados cadastrais + situação + `score_risco`/`faixa`/`receita_em_risco`/`posicao_fila` da última execução (null se não avaliado) |
| GET | `/clientes/{id}` | sim | `ClienteDetalhe`: cadastro, situação, `avaliacao` (score, faixa, dimensões, receita em risco, posição, `evidencias[]`, `acao_recomendada`) ou null; 404 se inexistente |
| GET | `/clientes/{id}/historico` | sim | `HistoricoCliente`: `atendimento[]` (todas as colunas por mês) e `nps[]` |
| GET | `/metricas/mensal?variavel=&agregacao=media\|soma` | sim | `list[{mes_ref, valor}]` da carteira inteira, ignorando NULL; `variavel` restrita às colunas numéricas de atendimento (422 caso contrário) |
| GET | `/sinais` | sim | `list[SinalResponse]` |
| GET | `/acoes-recomendadas` | sim | `list[AcaoResponse]` |
| POST | `/analise/executar` | sim | `ExecucaoResponse` (id, mes_referencia, executado_em, qtd_clientes_avaliados, qtd_na_fila) |
| POST | `/importacao` | sim | multipart `arquivo` → `RelatorioImportacao` (contagens, avisos) + análise executada |

Se não houver execução ainda, dashboard/fila retornam estruturas vazias (não erro).

## 9. Streamlit

- `api_client.py`: classe `ApiClient(base_url, token=None, transport=None)` com um método por endpoint; erros HTTP viram `ApiErro(status, detail)`; 401 em rota protegida → `NaoAutenticado`.
- `auth.py`: `exigir_login()` — sem token em `st.session_state` → aviso + `st.stop()`; captura `NaoAutenticado` limpando a sessão. Sidebar mostra "Olá, {nome}" e botão Sair.
- `Home.py`: abas **Entrar** / **Criar conta** com `st.form`; após cadastro com sucesso faz login automático; exibe `detail` da API em `st.error`.
- `pages/1_Dashboard.py`: métricas (ativos, receita ativa, receita em risco, qtd CRITICO/ATENCAO), tabela da fila (posição, cliente, segmento, plano, faixa, score, receita em risco, motivos, ação), botão "Reprocessar análise".
- `pages/2_Clientes.py`: filtros na sidebar, tabela paginada, selectbox de cliente → detalhe (métricas, evidências, ação) e gráficos Plotly (uso, SLA, chamados abertos/críticos/reabertos, NPS).
- `pages/3_Analise_Mensal.py`: equivalente ao `app.py` atual consumindo `/metricas/mensal`.
- `.streamlit/config.toml`: `primaryColor="#0156FC"`, `textColor="#000A1E"`, `backgroundColor="#FFFFFF"`, `secondaryBackgroundColor="#FAF9F5"`.
- `API_URL` via variável de ambiente (default `http://localhost:8000/api`).

## 10. Testes e verificação

- Backend (`backend/tests`): pytest + TestClient, SQLite em memória com `StaticPool`, override de `get_db`, fixture de usuário autenticado.
  - Unit: security, validações de schema, indicadores (média 3m, base 6m, NULL ignorado, persistência, sem vazamento de M+1), sinais (cada tipo de regra, NULL não dispara), score (saturação, regra 2 dimensões, faixas), recomendação, priorização (ordem, capacidade).
  - Integração: auth (todos os casos §7), importação do xlsx real (80/1.295/422/80, 22 cancelados, reimportação não duplica, `pct_sla_cumprido` NULL preservado — 23 linhas), análise gera avaliações e fila não vazia, cada endpoint de consulta (incluindo 401 sem token e 404).
- Frontend (`frontend/tests`): `ApiClient` com `httpx.MockTransport`; smoke de `Home.py` com `streamlit.testing.v1.AppTest`.
- `ruff check` e `ruff format --check` limpos.
- Verificação final manual: uvicorn + streamlit, fluxo cadastro → login → dashboard → detalhe no navegador.

## 11. Próximos passos (fora do MVP)

SQL Server + Alembic + docker-compose; persistir `indicadores_mensais`; calibração de sinais (lift, cobertura, falso alarme, antecedência) e `trajetoria_cancelados`; backtest; `registros_contato` e endpoints de contato; integração do React `assistente-consultas` com a API.
