# 07 — `definicoes_metricas.json` como fonte única

Status: aberto
Fase: 7 de 10 · Bloqueado por: 06

## Por que é possível sem reescrever fórmula

Os dois lados **já** são "definição declarativa + resolvedor genérico": `metricas.js:224-265`
tem um `agregar()` com 5 agregações nomeadas (`media`, `media_ponderada`, `razao_soma`,
`proporcao_linhas`, `soma`), e `metricas.py:81-181` tem a mesma estrutura. A fórmula não está
espalhada — está nessas 5 agregações, implementadas nas duas linguagens.

## Entregas

- `definicoes_metricas.json` — **a fonte** (id, agregação, coluna, filtro de linha, escala,
  rótulo, leitura alternativa). Lido pelos **dois** lados; cada um só implementa as 5
  agregações. Um resolvedor por linguagem continua existindo — é isso que preserva a resposta
  offline do widget.
- Pesos do índice de alerta **gerados** pelo Python para o JS (não declarados: são calculados
  a partir dos fatores de churn). Mata o comentário de `inovaappsDatabase.js:126-131`, que
  admite por escrito que os pesos são "mantidos em sincronia manualmente".
- **Convergir os 4 ids divergentes** para os nomes do JS:

| Antes (JS) | Antes (Python) | Agora |
|---|---|---|
| `atraso_medio_pagamento` | `atraso_pagamento` | `atraso_medio_pagamento` |
| `taxa_cancelamento` | `churn` | `taxa_cancelamento` |
| `uso_medio_plataforma` | `uso_plataforma` | `uso_medio_plataforma` |
| `nps_carteira` | `nps` | `nps_carteira` |

  Muda também o `enum` de métricas da tool `consultar_metrica` exposta ao LLM e os literais do
  teste de métricas em Python. `antiguidade_contrato` e `sla_contratado` (só em Python) ficam.

## Verificação

Os **20 números de referência batendo dos dois lados**: `pytest` + `npm run test:metricas`.
Este é o teste de contrato que prova que os dois resolvedores concordam.
