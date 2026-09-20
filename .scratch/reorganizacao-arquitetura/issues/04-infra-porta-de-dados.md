# 04 — `holder/infra/` — porta de dados e conexão única

Status: aberto
Fase: 4 de 10 · Bloqueado por: 02, 03

## Problema

A string ODBC está **triplicada** em `app.py:105-110`, `score_risco.py:40-46` e
`ingestao.py:15-20` — e só uma delas usa `Encrypt=no`. E as duas origens de dado (SQL Server e
Excel) são acessadas por caminhos totalmente independentes, sem interface comum.

## Entregas

- `holder/infra/dados/porta.py` — interface de leitura das 4 tabelas do domínio.
- `holder/infra/dados/adaptador_sqlserver.py` e `adaptador_excel.py` — os dois coexistem,
  escolha por configuração (decisão Q16: **não** unificar numa fonte só; unificar o *acesso*).
- `holder/infra/dados/conexao.py` — string ODBC única. **`Encrypt=no` vence** (versão mais
  simples e rápida, já documentada em `score_risco.py`); muda o comportamento de conexão do
  dashboard, sem mudar resultado.
- `holder/infra/persistencia/` — SQLite do admin e histórico (`fScoreRisco`/`fModeloRiscoLog`).
- `holder/infra/ia/` — cliente Groq e guardrails.
- `holder/infra/etl/ingestao.py`.

## Verificação

`pytest` + conferência visual das 3 abas e do chat.
