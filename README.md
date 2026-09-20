# Holder — prevenção de cancelamento

Solução para o Desafio INOVAAPPS 2026 ([enunciado](docs/desafio/contexto_do_desafio_inovaapps_2026.md)):
identificar, entre os clientes ativos de uma carteira de contratos recorrentes, quais estão em
risco de cancelar — mostrando a evidência que sustenta o alerta e **em que ordem** falar com
cada um.

O vocabulário do domínio está em [`CONTEXT.md`](CONTEXT.md) e as decisões arquiteturais em
[`docs/adr/`](docs/adr/). **Comece pelo `CONTEXT.md`**: o projeto tem três leituras distintas de
"este cliente vai embora?", e confundi-las é o erro mais fácil de cometer aqui.

## As três leituras de risco

| | Compara o cliente com | Responde | Escala |
|---|---|---|---|
| **Score de risco** | os cancelamentos reais, via modelo treinado | "em que ordem falar?" | Saudável / Atenção / Em risco / Crítico |
| **Índice de alerta** | a **própria história** dele | "este cliente piorou?" | Alto / Médio / Baixo |
| **Strikes** | o **perfil de quem já cancelou** | "se parece com quem saiu?" | 0 a 4 |

Não são sinônimos e podem apontar clientes diferentes — é esperado. Nesta base, 6 clientes
têm índice de alerta Alto e 41 têm pelo menos um strike, dos mesmos 58 ativos.

## Arquitetura

```
holder/
├── dominio/       regras e cálculos (lê pela porta de dados, sem Streamlit nem Flask)
│   ├── metricas/  catálogo + as 5 agregações nomeadas
│   ├── risco/     score do modelo treinado
│   ├── alerta/    índice de alerta (8 sinais contra a própria história)
│   ├── strikes/   semelhança com quem já cancelou
│   ├── churn/     fatores de cancelamento (de onde saem os pesos do alerta)
│   └── carteira/  preparação dos dados do dashboard
├── aplicacao/     casos de uso: assistente (tool use) e treino do modelo
├── infra/         SQL Server, planilha, SQLite, IA — uma porta, dois adaptadores
└── interfaces/    dashboard (Streamlit) e API (Flask)

interface-web/     shell da aplicação em React: navegação, iframe do dashboard, admin,
                   e o widget do assistente
dados/             a planilha do desafio (entrada) + gerado/ (banco, modelo, logs)
docs/              adr/, desafio/, design-tokens.md
scripts/           geradores e exploração
testes/            pytest
```

## Pré-requisitos

- **Python 3.11+** e `pip install -r requirements.txt`
- **Node 18+** (para o `interface-web/`)
- **SQL Server Express** local, instância `localhost`, com o
  **ODBC Driver 17 for SQL Server** e autenticação Windows. O banco `holder` é criado pela
  ingestão se não existir.
- Uma chave da [Groq](https://console.groq.com) para o fallback de IA do assistente. Sem ela o
  catálogo determinístico continua respondendo — só as perguntas fora do catálogo deixam de
  ser atendidas.

## Subindo do zero

```bash
pip install -r requirements.txt

cp .env.example .env                       # preencha GROQ_API_KEY
cp interface-web/.env.example interface-web/.env

# Crie o usuário do Jenkins no SQL com o seguinte comando no banco de dados:

USE [master];
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.server_principals
    WHERE name = 'holder_jenkins'
)
BEGIN
    CREATE LOGIN [holder_jenkins]
    WITH PASSWORD = 'Holder@123456',
         CHECK_POLICY = OFF,
         CHECK_EXPIRATION = OFF;
END;
GO

USE [holder];
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_principals
    WHERE name = 'holder_jenkins'
)
BEGIN
    CREATE USER [holder_jenkins]
    FOR LOGIN [holder_jenkins];
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_role_members drm
    INNER JOIN sys.database_principals role_principal
        ON drm.role_principal_id = role_principal.principal_id
    INNER JOIN sys.database_principals user_principal
        ON drm.member_principal_id = user_principal.principal_id
    WHERE role_principal.name = 'db_datareader'
      AND user_principal.name = 'holder_jenkins'
)
BEGIN
    ALTER ROLE [db_datareader]
    ADD MEMBER [holder_jenkins];
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_role_members drm
    INNER JOIN sys.database_principals role_principal
        ON drm.role_principal_id = role_principal.principal_id
    INNER JOIN sys.database_principals user_principal
        ON drm.member_principal_id = user_principal.principal_id
    WHERE role_principal.name = 'db_datawriter'
      AND user_principal.name = 'holder_jenkins'
)
BEGIN
    ALTER ROLE [db_datawriter]
    ADD MEMBER [holder_jenkins];
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_role_members drm
    INNER JOIN sys.database_principals role_principal
        ON drm.role_principal_id = role_principal.principal_id
    INNER JOIN sys.database_principals user_principal
        ON drm.member_principal_id = user_principal.principal_id
    WHERE role_principal.name = 'db_ddladmin'
      AND user_principal.name = 'holder_jenkins'
)
BEGIN
    ALTER ROLE [db_ddladmin]
    ADD MEMBER [holder_jenkins];
END;
GO







# 1. Carrega a planilha no modelo dimensional do SQL Server
python -m holder.infra.etl.ingestao

# 2. Treina o modelo de risco e popula o histórico mensal (fScoreRisco).
#    Sem este passo, a aba "Score de Risco" do dashboard abre vazia.
python -m holder.aplicacao.treino

# 3. Gera os dados e os pesos que o front consome
python scripts/gerar_dados_inovaapps.py
python scripts/gerar_pesos_alerta.py
```

Depois, três processos, cada um no seu terminal:

```bash
python -m holder.interfaces.api                              # API      :8000
python -m streamlit run holder/interfaces/dashboard/app.py             # dashboard :8501
cd interface-web && npm install && npm run dev               # front     :5173
```

Abra **http://localhost:5173** — é o shell que embute o dashboard e carrega o assistente.
O dashboard também abre sozinho em `:8501`, se você quiser só ele.

> A porta do front é fixa (`strictPort`) porque o CORS do backend libera exatamente essa
> origem. Se o Vite escolhesse outra porta em silêncio, o navegador passaria a descartar as
> respostas da API e o assistente cairia no modo local **sem acusar erro**.

## Testes

```bash
pytest                          # tudo
pytest -m "not sqlserver"       # sem o que depende do banco
pytest -m "not lento"           # sem treino nem backtest
cd interface-web && npm run test:metricas    # os números do catálogo
cd interface-web && npm run test:catalogo    # as intenções montam e respondem
```

`pytest` e `test:metricas` formam um **teste de contrato**: os mesmos números de referência são
conferidos em Python e em JavaScript. Os dois resolvedores de métrica são duplicados de
propósito — é o que faz o catálogo responder no navegador sem backend no ar — e leem a mesma
definição declarativa
([`definicoes_metricas.json`](holder/dominio/metricas/definicoes_metricas.json)). Ver
[ADR 0003](docs/adr/0003-resolvedor-de-metricas-duplicado-de-proposito.md).

## Exploração

```bash
python scripts/explorar_fatores_churn.py   # o que difere entre quem saiu e quem ficou
```

É de onde vêm os pesos do índice de alerta: eles não são escolhidos à mão, são calculados a
partir desses fatores.
