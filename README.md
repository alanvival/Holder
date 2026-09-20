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

## As três perguntas do enunciado, respondidas com número

O desafio lista três perguntas que estruturam o trabalho. Cada uma tem uma resposta medida na
própria base, e um lugar na tela onde ela aparece:

| Pergunta | Resposta medida | Onde aparece |
|---|---|---|
| **Com quanta antecedência o sinal aparece?** | O risco médio previsto já está na faixa Crítico **3 meses antes** do cancelamento real (75,7%), sobe para 84,0% a dois meses e 91,6% no último mês. Seis meses antes ainda está em 25,4%. | aba Score de Risco → *Qualidade do sinal* |
| **Quão bem ele separa?** | **AUC 0,948** e Brier 0,085 em validação cruzada 5-fold. Para comparar: os sinais isolados disparam para 29% (SLA), 43% (reclamação) e 22% (NPS) dos ativos — por isso o score pondera os sete indicadores em vez de contar sinais. | aba Score de Risco → *Qualidade do sinal* |
| **Quanto está em jogo?** | **Receita mensal em risco** = valor do contrato × probabilidade do modelo. Hoje são R$ 83.459,08/mês concentrados em 11 clientes, e é esse número que define a ordem de atendimento. | aba Quem Contatar |

A medição da antecedência é um backtest retroativo nos 22 clientes que já cancelaram
([`holder/dominio/risco/antecedencia.py`](holder/dominio/risco/antecedencia.py)): para cada um,
qual score o modelo teria dado 1 a 6 meses antes da saída real. A mesma função alimenta o
gráfico do dashboard e o teste que a valida, então o número da tela é o número testado.

Sobre o NPS, o enunciado observa que "ausência de resposta não é dado faltante, é
comportamento". Medimos o silêncio e ele **não separa nesta base** — clientes ativos ignoram o
último convite com frequência maior (27,6%) que os cancelados (22,7%). Por isso ele fica
deliberadamente fora do score, com o número que sustenta a decisão registrado na
[ADR 0004](docs/adr/0004-silencio-no-nps-nao-entra-no-score.md).

## Modelo de negócio

O enunciado pergunta qual seria o modelo de negócio de uma solução como essa. A conta sai da
própria base.

**O que está em jogo.** A carteira do desafio tem 80 clientes e perdeu 22 em dezoito meses —
R$ 274.966 de receita mensal, R$ 3,3 milhões ao ano. O enunciado é direto sobre a assimetria
que sustenta o produto: *"reter custa uma fração do que custa conquistar"*. Cada mês de
antecedência é um mês a mais para negociar valor em vez de desconto.

**Como cobrar.** Assinatura mensal por carteira acompanhada, não por usuário: quem se beneficia
é o time de relacionamento inteiro, e cobrar por assento puniria justamente o hábito que o
produto quer criar (mais gente olhando a mesma lista). O valor acompanha o tamanho da carteira,
porque é ele que determina tanto o custo de processar quanto o risco coberto.

**Por que se paga.** Nesta carteira, quem cancelou tinha contrato médio de R$ 12.498/mês.
Evitar **um único** desses preserva R$ 150 mil em doze meses. A solução não precisa acertar
todos os 22 — precisa dar ao time três meses de antecedência sobre os casos que ele já teria
perdido de qualquer forma.

**Onde escala.** Nada aqui é específico de um segmento: o modelo é treinado contra os
cancelamentos da própria carteira do cliente, então cada empresa que instala reaprende os pesos
da sua realidade em vez de herdar os de outra. O que se reaproveita é o método — as três
leituras de risco, a ordem por receita em risco e a explicação por sinal —, não os coeficientes.

**Qual é o limite honesto.** Uma carteira pequena demais ou sem histórico de cancelamento não
tem o que treinar; abaixo de algumas dezenas de saídas registradas, o índice de alerta e os
strikes continuam funcionando (não dependem de treino), mas o score de risco não. Vender a
solução para quem nunca perdeu cliente seria vender uma tela bonita sem modelo por trás.

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
streamlit run holder/interfaces/dashboard/app.py             # dashboard :8501
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
