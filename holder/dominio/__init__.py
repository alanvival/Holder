"""
Camada de domínio: as regras e os cálculos da solução.

Quatro leituras distintas de "este cliente vai embora?", e elas não são
sinônimos — ver `CONTEXT.md` na raiz:

- `risco/`    score de risco: modelo treinado nos cancelamentos reais.
              Responde "em que ordem falar?".
- `alerta/`   índice de alerta: soma ponderada de 8 sinais, comparando o
              cliente com a PRÓPRIA história. Responde "este cliente
              piorou?".
- `strikes/`  semelhança com quem já cancelou: linhas de corte sobre o
              perfil dos meses que antecederam saídas reais. Responde
              "este cliente se parece com quem saiu?".
- `churn/`    fatores de cancelamento: o que difere entre ativos e
              cancelados. É de onde saem os pesos do índice de alerta.

Mais `metricas/` (o catálogo agregado) e `carteira/` (preparação dos dados
para o dashboard).

Sobre I/O: o domínio lê **pela porta** (`holder/infra/dados/`), sem saber de
qual adaptador o dado veio. Não é hexagonal puro — os cálculos recebem e
devolvem DataFrames, e isso foi decisão consciente: transformar tudo em
tipos próprios significaria reescrever as fórmulas, não reorganizá-las.
"""
