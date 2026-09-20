# 07 — `definicoes_metricas.json` como fonte única

Status: resolvido

## Resultado

`79 passed` (74 + 5 de contrato), `18/18` no lado JS, e `npm run build` passa — o que prova que
o import do arquivo compartilhado funciona também em build, não só no dev server.

Nenhum número mudou: ticket 12287.05, atraso 3.1822, churn 27.5, uso 79.8102, SLA 75.9559,
reabertura 12.2323, NPS -6.8 / nota 7.11.

Os pesos calculados (83, 70, 48, 24, 22, 14, 10, 12) são **exatamente** os que estavam
hardcoded no JavaScript — ou seja, hoje estavam em sincronia. Gerar não mudou valor nenhum;
mudou a garantia de que continuem batendo.

### Guarda contra falha silenciosa

`pesos_dos_sinais()` ganhou uma checagem que **levanta erro** se uma chave de fator não
existir. Sem ela, renomear um id de métrica faria o peso cair para o mínimo em silêncio, e o
índice de alerta inteiro mudaria de valor sem ninguém notar. Foi a primeira coisa que quase
aconteceu ao convergir os ids.

### Extras

- O JS ganhou a agregação `antiguidade_dias`, que existia só no Python — agora os dois
  resolvedores cobrem as 13 métricas da fonte única, sem assimetria.
- `vite.config.js` ganhou `server.fs.allow: ['..']`, porque o arquivo compartilhado fica fora
  da raiz do projeto do front.
- O NPS passou a ser detectado pela **agregação declarada**, não por `id == "nps"` — que era
  justamente um dos ids que mudaram.
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
