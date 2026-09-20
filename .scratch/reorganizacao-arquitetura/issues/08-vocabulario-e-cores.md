# 08 — Vocabulário risco→alerta e cores semânticas

Status: resolvido

## Resultado

`88 passed` (+2 de cores semânticas), `18/18` no JS, `npm run build` passa.

Renomeações, com o critério de que **quem lê a tela** precisa distinguir os três conceitos:

| Antes | Agora |
|---|---|
| `clientes_em_risco` (tool + função) | `clientes_em_alerta` |
| `prever_risco_cancelamento` (tool + função) | `clientes_com_strikes` / `avaliar_strikes` |
| `calcularRisco` (JS) | `calcularIndiceAlerta` |
| `clientesComRisco` (JS) | `clientesEmAlerta` |
| `PESOS_SINAIS_RISCO`, `SINAIS_RISCO_CACHE` | `PESOS_SINAIS_ALERTA`, `INDICE_ALERTA_CACHE` |
| intent `situacao_risco_cliente` | `situacao_alerta_cliente` |
| "Risco atual: Alto" (chat) | "Índice de alerta: Alto" |
| "Linha de Risco (Média de Cancelados)" (dashboard) | "Linha de corte (perfil de quem cancelou)" |
| `pontuacao_risco` | `pontuacao_alerta` |

`listar_previsao_risco` e `detalhar_previsao_cliente` **mantêm** "risco" no nome: elas são o
score do modelo treinado, onde a palavra está correta.

As descrições das duas tools heurísticas ganharam um bloco "NÃO CONFUNDIR" explícito, que
nomeia as outras duas leituras e avisa que **podem apontar clientes diferentes**. Era o risco
concreto: o modelo escolhia a tool errada porque nada nas descrições as separava.

## Cores semânticas

Seção nova no `docs/design-tokens.md`, com as 4 faixas (escala quente, como já eram) e os 3
níveis de alerta em **azul de marca** — deliberadamente frios, pra que as duas escalas não se
confundam de olho. Propagadas para `tokens.css` e `estilo.py`, e presas por dois testes novos:
um confere as três cópias contra a fonte, o outro falha se as duas escalas passarem a
compartilhar cor.
Fase: 8 de 10 · Bloqueado por: 07

## Problema

Existem dois conceitos com o mesmo nome. Decisão Q15=(b): eles **coexistem**, mas o heurístico
para de se chamar "risco" — senão a ambiguidade volta pela porta do vocabulário.

| Conceito | Escala | Faixas |
|---|---|---|
| **Score de risco** (modelo treinado) | 0-100 probabilístico | Saudável / Atenção / Em risco / Crítico |
| **Índice de alerta** (8 sinais com peso) | 0-100 de pontos | Alto / Médio / Baixo |

## Entregas

Rename até o texto de usuário (decisão Q27=c):

- **Código**: `_calcular_risco_cliente` → `calcular_indice_alerta`, `calcularRisco` →
  `calcularIndiceAlerta`, `SINAIS_RISCO_CACHE` → equivalente de alerta.
- **Tools do LLM**: `clientes_em_risco` → `clientes_em_alerta`, e as descrições das duas tools
  passam a distinguir explicitamente "índice de alerta" (heurístico) de "score de risco"
  (`listar_previsao_risco`, modelo treinado). Hoje o modelo tem duas tools que respondem
  "quem está em risco?" sem descrição que as separe — e escolhe a errada.
- **Texto de tela**: respostas do chat e rótulos do dashboard.

Cores semânticas (decisão Q32=a):

- Seção "Cores semânticas" no `docs/design-tokens.md` com as 4 faixas + os 3 níveis, derivadas
  da paleta existente.
- `app.py` passa a ler de um só lugar; `tokens.css` ganha os mesmos tokens, para o widget
  pintar faixa igual ao dashboard.
- Motivo: se o chat disser "Alto" e o dashboard pintar "Crítico" em cores parecidas, a
  distinção entre os dois conceitos não chega aos olhos de quem avalia.

## Verificação

`pytest` + `testes/test_tokens.py` + chat respondendo as duas perguntas ("quem está em alerta?"
e "quem tem score de risco alto?") **sem confundir os conceitos**.
