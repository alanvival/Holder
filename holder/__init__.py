"""
Pacote da solução de prevenção de cancelamento.

Quatro camadas, e a dependência só aponta para dentro:

- `dominio/`     regras e cálculos. Lê pela porta de dados, sem saber de
                 qual adaptador o dado veio; nada de Streamlit nem Flask.
- `aplicacao/`   casos de uso, que orquestram domínio e infra.
- `infra/`       tudo que fala com o mundo: SQL Server, planilha, SQLite, IA.
- `interfaces/`  dashboard, API e o que mais apresentar a solução.

Não é hexagonal puro: os cálculos recebem e devolvem DataFrames, e o
domínio chama a porta em vez de recebê-la injetada. Foi decisão consciente —
transformar tudo em tipos próprios significaria reescrever as fórmulas, não
reorganizá-las.

Ver `CONTEXT.md` (vocabulário) e `docs/adr/` (decisões) na raiz do repo.
"""
