# 10 — Limpeza e README

Status: aberto
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
