# 03 — Efeitos colaterais de import explícitos

Status: resolvido
Fase: 3 de 10 · Bloqueado por: 02

## Resultado

`63 passed` (59 + 4 novos). API sobe e responde `/api/health`, `/api/perguntas` e
`/api/historico` com 200 — o SQLite passa a ser inicializado pelo servidor. Dashboard sobe com
200 e sem erro no log.

A carga preguiçosa do `dados.py` usa `lru_cache` + `__getattr__` de módulo (PEP 562), o que
preservou os ~20 pontos de uso de `dados.clientes`, `dados.SEGMENTOS` etc. sem tocá-los. Só os
três que liam no **nível do módulo** precisaram mudar: os dois `_ABAS` (metricas e
tools_genericas) viraram `dados.aba(nome)`, e `_CATEGORIAS_VALIDAS` virou função, porque
`segmento` é derivado da planilha.

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
- `carregar_modelo()` deixa de treinar implicitamente: erro claro se o `.pkl` não existir, com
  a instrução do comando de treino.
- `testes/test_sem_efeito_no_import.py` (novo): prende o invariante em subprocessos limpos —
  importar não lê a planilha, não configura log em disco, não cria motor de conexão, e a
  planilha continua sendo lida uma única vez por processo.

## Movido para a fase 6

O item "`app.py` sem `carregar_dados()` no nível do módulo" **saiu desta fase**. Executar no
nível do módulo *é* o contrato do Streamlit: ele reexecuta o script inteiro a cada interação.
Tirar a chamada de lá exige envolver as 667 linhas num `main()`, que é exatamente o trabalho da
fase 6 (quebrar o dashboard por aba). Fazer agora significaria reestruturar o arquivo duas
vezes. `st.set_page_config()` na linha 13 continua onde está pelo mesmo motivo: o Streamlit
exige que seja a primeira chamada.

## Verificação

`pytest` + conferência visual das 3 abas e do chat.
