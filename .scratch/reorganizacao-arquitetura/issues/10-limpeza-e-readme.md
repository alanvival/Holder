# 10 — Limpeza e README

Status: resolvido

## Resultado

Rodei a sequência inteira do README do zero: ingestão, treino, geradores, API, dashboard.
`88 passed`, `18/18` no JS, `npm run build` passa, API com CORS correto, dashboard em 200.

### Bug encontrado NA verificação do README

A ingestão crashava com `UnicodeEncodeError: 'charmap' codec can't encode character '❌'`.
Causa: o `print` de sucesso usava o emoji `✓`, que o console padrão do Windows (cp1252) não
encoda. Pior — o `print` do erro no `except` também era emoji (`❌`), então a falha do print de
sucesso caía no except e crashava de novo, **escondendo a causa real** atrás de uma mensagem
sobre o caractere errado. Com `PYTHONIOENCODING=utf-8` tudo passava, o que explica por que
nunca apareceu antes.

Defeito pré-existente, mas num comando que o README manda rodar como passo 1. Marcadores agora
em ASCII.

### Não entregue, de propósito

`aplicacao/priorizacao/ordem.py` estava previsto no issue 06 e **não foi criado**. Seria código
novo, não reorganização: o ranking de priorização já existe e está na aba 1 do dashboard
(`Ranking de Priorização de Contato`). Criar um módulo que ninguém chama seria código morto.
Fase: 10 de 10 · Bloqueado por: 09

## Entregas

- `dados/` — `INOVAAPPS_base_de_dados.xlsx` sai da raiz; `dados/gerado/` recebe
  `modelo_risco.pkl`, `dados_admin.sqlite3` e `logs/`. Atualizar os 4 pontos que leem a
  planilha e o `.gitignore`.
- Corrigir `app.py:468`: instrui "Rode `python score_risco.py`", mas esse arquivo **não tem
  `__main__`** — o comando é no-op. O certo é o comando de treino do modelo. É texto que a
  banca pode ler na tela.
- `TenantContext`: manter o contexto (multi-tenant é narrativa útil para a pergunta de modelo
  de negócio do enunciado, §3.2), mas **parar de passá-lo** para as 6 funções de
  `assistenteApi.js` que o recebem e descartam; registrar no `CONTEXT.md` que é placeholder
  declarado, não funcionalidade.
- `README.md` real — escrito por último, de propósito: ele descreve como rodar o estado final.
  Os 4 processos (SQL Server → ingestão → API → Vite → Streamlit), os comandos novos, e como
  rodar os testes.

## Verificação

**Subir tudo do zero seguindo apenas o README**, numa sessão limpa: ingestão, treino, API,
front, dashboard. Se algum passo exigir conhecimento que não está no README, o README está
errado.
