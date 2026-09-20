# 05 — `holder/dominio/`

Status: aberto
Fase: 5 de 10 · Bloqueado por: 04

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
