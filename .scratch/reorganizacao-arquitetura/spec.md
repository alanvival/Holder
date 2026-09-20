# Reorganização arquitetural do repositório

Status: aprovado (2026-09-20)
Branch: `feature/HOLDER-Madrugas`

## Objetivo

Reorganizar o repo em camadas explícitas. O projeto é um **MVP avaliado por banca, sem
continuidade depois** — então o critério que guia cada escolha **não** é manutenibilidade
futura, e sim:

1. **A solução não pode se contradizer na frente do avaliador.** Hoje o chat e o dashboard
   respondem "quem está em risco?" por caminhos diferentes, com pesos que o próprio código
   admite estarem "mantidos em sincronia manualmente".
2. **Nenhuma função pode ser perdida.** Em particular, a resposta determinística offline do
   widget (que funciona com o backend fora do ar) é função, não detalhe.

## Restrições dadas

- Não pode quebrar nada nem retirar função. "Não quebrar" = gráficos e funcionalidades
  operando normalmente.
- SQL Server local (`localhost`, banco `holder`) estará no ar durante o trabalho.
- Chamadas à Groq ficam mockadas nos testes.
- Tudo em PT-BR (código, pastas, docs).
- O front deve seguir o `design-tokens.md`.

## Decisões

### Arquitetura
- Camadas leves com portas: `dominio` (zero I/O) → `aplicacao` → `infra` → `interfaces`.
- Pacote único `holder/` na raiz (não `src/`, não módulos soltos). Habilita `python -m holder.x`
  e elimina o `sys.path.insert` que hoje existe em `previsao_risco.py`.
- Acesso a dado atrás de **uma porta com dois adaptadores** (SQL Server e Excel coexistem,
  escolha por configuração). Mata a string ODBC triplicada.
- Efeitos colaterais em tempo de import viram chamada explícita.

### Escopo (o que unificar)
Unificar **apenas o que pode divergir na demo**:
- lógica de risco (hoje em 3 cópias),
- fatores de churn (hoje em 2 fórmulas),
- definições de métrica (hoje em 2 arquivos com 4 ids diferentes).

**Não** unificar os motores de dados numa fonte só. **Não** eliminar o resolvedor de métricas
em JS (é o que preserva a resposta offline).

### Domínio: dois conceitos, não um
| Conceito | O que é | Escala | Responde |
|---|---|---|---|
| **Score de risco** | Regressão logística treinada (AUC≈0.95, Brier≈0.085) | Saudável / Atenção / Em risco / Crítico | "em que ordem?" |
| **Índice de alerta** | 8 sinais com pesos derivados dos dados | Alto / Médio / Baixo | "por quê?" |

O rename "risco → alerta" vai até o texto de tela e as descrições das tools do LLM: hoje o
modelo tem duas tools que respondem "quem está em risco?" sem descrição que as distinga, e
escolhe a errada. Cada escala ganha cor própria no `design-tokens.md`.

### Fonte única
- `definicoes_metricas.json` é a **fonte** das definições de métrica (id, agregação, coluna,
  filtro de linha, escala, rótulo). Cada lado implementa apenas as 5 agregações nomeadas que
  os dois já têm hoje.
- Os **pesos do índice de alerta** são *gerados* pelo Python (são calculados a partir dos
  fatores de churn, não declarados).
- Os 4 ids divergentes resolvem para os nomes do JS: `atraso_medio_pagamento`,
  `taxa_cancelamento`, `uso_medio_plataforma`, `nps_carteira`. Motivo: o padrão da casa já diz
  a agregação no nome, e `churn` é anglicismo num repo 100% PT-BR.
- Tokens de design **não** viram fonte gerada — eles nunca divergiram. Ficam presos por teste.

## Árvore final

```
holder/
├── dominio/            zero I/O, zero streamlit, zero flask
│   ├── metricas/       resolvedor.py, definicoes.py, nps.py
│   ├── risco/          modelo.py, faixas.py, dataset.py
│   ├── alerta/         sinais.py, pesos.py, indice.py
│   ├── churn/          fatores.py
│   └── carteira/       preparacao.py   (ex-carregar_dados() de app.py)
├── aplicacao/
│   ├── assistente/     ia_fallback.py, tools.py, tools_genericas.py, campos.py
│   └── priorizacao/    ordem.py  (score x valor_mensal)
├── infra/
│   ├── dados/          porta.py, adaptador_sqlserver.py, adaptador_excel.py, conexao.py
│   ├── persistencia/   admin_sqlite.py, historico_score.py
│   ├── ia/             cliente_groq.py, guardrails.py
│   └── etl/            ingestao.py
└── interfaces/
    ├── dashboard/      app.py + matriz.py, monitor.py, score.py
    └── api/            servidor.py + rotas/
dados/                  INOVAAPPS_base_de_dados.xlsx + gerado/
interface-web/          (ex-assistente-consultas)
testes/                 pytest
scripts/                geradores + explorar_fatores_churn.py
docs/                   adr/, agents/, desafio/, design-tokens.md
CONTEXT.md  README.md
```

Comandos novos:
```
streamlit run holder/interfaces/dashboard/app.py
python -m holder.interfaces.api
python -m holder.infra.etl.ingestao
python -m holder.dominio.risco.modelo
pytest
```

## Mudanças de comportamento assumidas

Consequências conscientes das decisões acima, não efeitos colaterais:

1. **Strikes do dashboard**: janela de recência passa de calendário (`DateOffset(months=1)`)
   para "2 últimos meses com dado". Para cliente com mês faltante, o strike pode mudar.
2. **Conexão do dashboard** passa a usar `Encrypt=no` (mais rápida, mesmo resultado).
3. **4 ids de métrica mudam**, inclusive no `enum` da tool `consultar_metrica` do LLM.
4. **Textos de tela mudam** onde diziam "risco" para o conceito heurístico.
5. **Todos os comandos de execução mudam.**
6. **Ordem de inicialização fica explícita**: importar módulo deixa de criar banco, ler
   planilha e criar `logs/`.
7. **Porta do CORS alinhada em 5173** (padrão do Vite, que é o que o README já dizia).

## Verificação

`pytest` (marcadores para o que exige SQL Server) + `npm run test:metricas` + **conferência
visual das 3 abas e do chat** ao fim de cada fase.

Decisão explícita do usuário: a verificação é **visual, sem baseline numérico**. Portanto o
relato de cada fase diz "conferi as telas e estão iguais", **nunca** "os números são
idênticos" — sem snapshot não há como afirmar isso.

## Fora de escopo

- Não tocar no modelo de regressão (features, alvo, treino, hiperparâmetros).
- Não mudar fórmula de métrica (exceto a unificação de janela do item 1 acima).
- Não mudar o design visual, além de adicionar as cores semânticas de faixa/nível.
- Não gerar tokens de design por script.
- Não transformar o widget em cliente de API.

## Fases

Uma fase por commit, revertível isoladamente. Ver `issues/`.

| # | Fase |
|---|---|
| 01 | Documentação de domínio (CONTEXT.md, 3 ADRs, `.md` → `docs/`) |
| 02 | Rede de teste (pytest, `testes/`, marcadores, asserts reais) |
| 03 | Efeitos colaterais de import explícitos |
| 04 | `holder/infra/` — porta de dados + 2 adaptadores + conexão única |
| 05 | `holder/dominio/` — métricas, risco, alerta, churn, carteira |
| 06 | `holder/aplicacao/` + `holder/interfaces/` |
| 07 | `definicoes_metricas.json` como fonte única |
| 08 | Vocabulário risco→alerta + cores semânticas |
| 09 | `interface-web/` |
| 10 | Limpeza + README |
