# 04 — `holder/infra/` — porta de dados e conexão única

Status: resolvido
Fase: 4 de 10 · Bloqueado por: 02, 03

## Resultado

`74 passed` (63 + 11 novos em `test_porta_de_dados.py`). API e dashboard sobem sem erro de
import. Os dois adaptadores concordam nas quatro contagens, e elas batem com o enunciado:
80 clientes, 1.295 linhas de atendimento, 80 situações, 422 pesquisas.

O `test_porta_de_dados.py` existe para transformar em falha o risco que o ADR 0002 aceita por
escrito: divergência entre adaptadores não aparece como erro, aparece como número diferente.

### Ficou para depois, com motivo

- **`fModeloRiscoLog`** (criação, INSERT e leitura) continua em `modelo_risco.py`. É
  persistência, mas está entrelaçada com as métricas do treino; sai na fase 5, junto do modelo.
- **`holder/infra/ia/cliente_groq.py` não foi extraído.** A chamada à API vive em
  `_chamar_modelo`, dentro de `ia_fallback.py`, e os 22 casos de teste mockam exatamente
  `ia_fallback._chamar_modelo`. Extrair agora quebraria a suíte inteira por um ganho de
  organização; vai na fase 6, junto com a mudança do assistente para `aplicacao/`.
- **`score_risco.py` virou arquivo de transição**: só domínio (`FAIXAS`, `faixa_de`, `_num`)
  mais reexportações da infra, para não quebrar `import score_risco as sr` em `modelo_risco.py`,
  `app.py` e `previsao_risco.py`. Ele se dissolve na fase 5.
- **`fallback_ia/dados.py`** deixou de ler a planilha: agora pega as tabelas no adaptador de
  Excel e só monta os índices por `cliente_id`. Virou o que sempre foi de fato — os acessos por
  cliente que o assistente usa.

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
