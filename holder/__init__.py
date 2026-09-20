"""
Pacote da solução de prevenção de cancelamento.

Quatro camadas, e a dependência só aponta para dentro:

- `dominio/`     regras e cálculos. Zero I/O, zero Streamlit, zero Flask.
- `aplicacao/`   casos de uso, que orquestram domínio e infra.
- `infra/`       tudo que fala com o mundo: SQL Server, planilha, SQLite, IA.
- `interfaces/`  dashboard, API e o que mais apresentar a solução.

Ver `CONTEXT.md` (vocabulário) e `docs/adr/` (decisões) na raiz do repo.
"""
