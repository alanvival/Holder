# 05 — `holder/dominio/`

Status: resolvido (5a e 5b)

## Resultado de 5b

`74 passed`. `score_risco.py` e `modelo_risco.py` deixaram de existir; `app.py` caiu de 645
para 549 linhas. O job de treino virou `python -m holder.aplicacao.treino` — mora em
`aplicacao/` e não em `dominio/risco/` porque é orquestração (pede o dataset, manda treinar,
grava pickle, registra log, regrava histórico). Desvio consciente do comando previsto na spec.

### A janela de recência (Q22) não mudou nenhum número nesta base

Medido: a janela nova (`[-2:]` = `['2026-05','2026-06']`) e a antiga (`DateOffset(months=1)`)
**coincidem**, porque nenhum cliente ativo está sem registro no último mês. A mudança é de
robustez, não de valor — ela passa a valer se a base ganhar buraco na série.

### Divergência REAL encontrada e corrigida: "Último NPS detrator"

Ao comparar painel e motor, apareceram 40 contra 41 clientes com strike. A causa não era a
janela: o painel pegava a **última linha** de pesquisa sem filtrar `respondeu`, enquanto o
motor pegava a última **respondida**. Um cliente que foi detrator e depois ignorou o convite
seguinte aparecia com classificação vazia e **perdia o strike** — 3 clientes nesta base
(C012, C069, C080).

Isso contradizia o próprio `CONTEXT.md`, que diz que não-resposta é comportamento observado e
não dado faltante. A regra passou a ser única (`holder/dominio/strikes/nps_recente.py`): vale a
pesquisa mais recente respondida. Depois da correção, painel e motor concordam em **71 strikes,
41 clientes, cliente a cliente, zero divergência**.

Era exatamente o tipo de contradição que a Q8=(b) existia para matar: ninguém veria erro na
tela, só dois números diferentes para a mesma pergunta.
Fase: 5 de 10 · Bloqueado por: 04

## Dividida em duas, por volume

- **5a (resolvido)** — o domínio que o assistente usa: `metricas/`, `churn/`, `alerta/`,
  `strikes/`, e os acessos por cliente para `holder/infra/dados/carteira.py`.
- **5b (aberto)** — o domínio do score e da carteira: `risco/` (de `modelo_risco.py`) e
  `carteira/preparacao.py` (de `app.py`), mais a unificação da janela de recência no painel de
  Strikes do dashboard.

## Correção de modelo de domínio (Q33)

O `CONTEXT.md` da fase 1 estava **errado**: dizia que strike era só forma de apresentar um
sinal de alerta. São mecanismos diferentes, e a diferença é observável — medido nesta base:
**índice de alerta Alto = 6 clientes; strikes ≥ 1 = 41 clientes**, dos mesmos 58 ativos. Um
olha se o cliente piorou em relação a si mesmo; o outro, se ele se parece com quem já
cancelou. Agora são três conceitos no glossário, com `dominio/alerta/` e `dominio/strikes/`
separados, e os verbetes "Strike" e "Linha de corte" corrigidos.

## Resultado de 5a

`74 passed`, mesma contagem de antes — nenhum teste perdido na divisão. `fallback_ia/metricas.py`
(690 linhas, três conceitos misturados) **deixou de existir**, sem shim: os consumidores apontam
direto para o domínio. O `sys.path.insert` de `previsao_risco.py` também morreu, porque a
persistência agora está dentro de `holder/`.

Os nomes de função que ainda dizem "risco" (`clientes_em_risco`,
`prever_risco_cancelamento`) ficam como estão até a fase 8, que é a fase de vocabulário —
misturar renomeação com movimentação tornaria os dois commits ilegíveis.

## Entregas

- `dominio/metricas/` — resolvedor + definições + NPS (de `fallback_ia/metricas.py`).
- `dominio/risco/` — `modelo.py` (regressão), `faixas.py` (as 4 faixas), `dataset.py`.
- `dominio/alerta/` — `sinais.py`, `pesos.py`, `indice.py` (o heurístico de 8 sinais).
- `dominio/churn/fatores.py` — **contraste de médias vence** (decisão Q19). `churn.py` sai da
  raiz para `scripts/explorar_fatores_churn.py` e passa a chamar esta função, mantendo o
  gráfico Plotly; a fórmula de Pearson deixa de existir em paralelo.
- `dominio/carteira/preparacao.py` — extração de `carregar_dados()` (`app.py:94-217`), a função
  que produz os 9 objetos que alimentam todos os gráficos das 3 abas.
- **Janela de recência unificada em `[-2:]`** (dois últimos meses com dado) — decisão Q22.
  `app.py:199` usava calendário (`DateOffset(months=1)`).

## Mudança de comportamento nesta fase

O strike de um cliente com mês faltante na série pode mudar de valor. É a única mudança de
cálculo prevista em todo o plano, e foi decidida explicitamente: "reclamação recente" deve
olhar os dois últimos meses **em que houve medição**, não o calendário.

Remover também o universo hardcoded `"Ativos (58) vs Cancelados (22), 80 clientes"` de
`metricas.py:423` — passa a ser contado dos dados.

## Verificação

`pytest` + conferência visual das 3 abas e do chat. Atenção especial ao painel de Strikes
(aba 1) por causa da mudança de janela.
