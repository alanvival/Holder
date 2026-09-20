# 02 — Rede de teste

Status: resolvido
Fase: 2 de 10 · Bloqueia todas as fases seguintes

## Resultado

`59 passed, 0 skipped` em ~13s, e `18/18` no lado JS. Desvios do plano original, todos
deliberados:

- **Marcador `ia` não foi criado**: a Groq é sempre mockada nos testes, então o marcador
  nasceria morto. Em vez dele existe `lento`, que marca o treino e o backtest do modelo.
- **`fScoreRisco` estava vazia** nesta máquina — por isso 3 testes de previsão pulavam (e a
  aba 3 do dashboard renderizava vazia). Estado pré-existente, não regressão. Populada com o
  job documentado (`python modelo_risco.py`): AUC 0.948, histórico de 2025-01 a 2026-06.
  Depois disso, os 3 testes rodam e passam.
- **Quarta cópia de tokens descoberta** durante a fase 1 (`exportarPdf.js`, em RGB). O
  `test_tokens.py` cobre 3 das 4; as cores de faixa de `app.py` entram na fase 8, quando
  passarem a existir no `design-tokens.md`.

## Por que primeiro

Sem isto, "não quebrou" é chute. Nenhuma fase que move código pode começar antes desta.

## Estado atual

| Arquivo | Invocação | SQL Server | Estilo |
|---|---|---|---|
| `testar_modelo_risco.py` | `python testar_modelo_risco.py` | **exigido** | `assert` real |
| `fallback_ia/testar_fallback_mock.py` | `python -m fallback_ia.testar_fallback_mock` | opcional (4 casos dão SKIP) | `assert` real |
| `fallback_ia/testar_metricas.py` | `python -m fallback_ia.testar_metricas` | não | `print` + `SystemExit(1)` |
| `assistente-consultas/scripts/testar-metricas.mjs` | `npm run test:metricas` | não | `print` + `process.exit(1)` |

Não existe `pytest.ini`, `pyproject.toml`, `conftest.py` nem CI. Os nomes são `testar_*`, que o
pytest não coletaria. `fallback_ia/testar_metricas.py` **não tem `__main__`** — as 17 asserções
rodam no import.

## Entregas

- `pytest` no `requirements.txt`.
- Suítes Python → `testes/`, renomeadas para `test_*`, com `__main__` removido onde havia
  execução no import.
- Marcadores: `@pytest.mark.sqlserver` (para o que precisa do banco) e `@pytest.mark.ia`.
- Converter `print`+`exit(1)` em `assert` real nos dois arquivos que hoje só mudam exit code.
- `testes/test_tokens.py` — lê os hex do `docs/design-tokens.md` e falha se qualquer cópia
  divergir (decisão Q31: tokens seguem cópia conforme, presos por teste, em vez de gerados por
  script). São **quatro** cópias a conferir, descobertas na fase 1:
  1. `interface-web/src/styles/tokens.css` (hoje 100% conforme),
  2. o bloco `[theme]` do `.streamlit/config.toml` (4 hex),
  3. as cores de faixa em `app.py` (2 definições, e **não existem** no `design-tokens.md` —
     resolvido na fase 8),
  4. `interface-web/src/utils/exportarPdf.js` — tokens replicados **em RGB** porque o jsPDF não
     lê CSS custom properties; o teste precisa converter hex→RGB antes de comparar.
- `npm run test:metricas` fica como está — é o lado JS do teste de contrato.

## Verificação

`pytest` verde, `npm run test:metricas` verde, e **screenshot das 3 abas do dashboard** como
referência visual para as fases seguintes.
