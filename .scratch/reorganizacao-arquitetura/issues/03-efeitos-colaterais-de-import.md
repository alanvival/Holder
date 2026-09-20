# 03 — Efeitos colaterais de import explícitos

Status: aberto
Fase: 3 de 10 · Bloqueado por: 02

## Problema

Importar módulo neste repo não é operação neutra. Isso impede testar domínio sem infra e torna
qualquer verificação por import perigosa:

| Onde | Efeito no import |
|---|---|
| `ingestao.py:40-41` | conecta no SQL Server `master` e **pode executar `CREATE DATABASE [holder]`** |
| `fallback_ia/dados.py:16` | lê a planilha inteira (`sheet_name=None`) |
| `fallback_ia/armazenamento.py:233` | conecta no SQLite e roda 3 `CREATE TABLE` |
| `fallback_ia/guardrails.py:32,36-42` | cria `logs/` e abre `FileHandler` |
| `app.py:13,219` | `st.set_page_config()` e `carregar_dados()` no nível do módulo |
| `fallback_ia/testar_metricas.py` | executa as asserções (sem `__main__`) — resolvido na fase 02 |

Além disso: `modelo_risco.carregar_modelo():153-160` **treina e grava** (pickle +
`INSERT fModeloRiscoLog`) se o `.pkl` não existir — um "carregar" muta o banco.

## Entregas

- `dados.py` carrega sob demanda com cache (`@lru_cache`), devolvendo o mesmo objeto de hoje —
  nenhuma fórmula muda.
- `armazenamento.inicializar()` passa a ser chamado pelo servidor, não pelo import.
- `guardrails` cria diretório e handler numa função de inicialização.
- `ingestao` sem conexão no nível do módulo.
- `app.py` sem `carregar_dados()` no nível do módulo.
- `carregar_modelo()` deixa de treinar implicitamente: erro claro se o `.pkl` não existir, com
  a instrução do comando de treino.

## Verificação

`pytest` + conferência visual das 3 abas e do chat.
