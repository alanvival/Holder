# O resolvedor de métricas é duplicado de propósito (Python e JavaScript)

Status: aceita

As métricas agregadas têm **uma** definição — um arquivo declarativo com id, agregação, coluna,
filtro e escala, lido pelos dois lados — mas **dois resolvedores**, um em Python e um em
JavaScript, cada um implementando as mesmas cinco agregações nomeadas. Isso parece duplicação a
ser eliminada. Não é.

O resolvedor em JavaScript é o que faz o catálogo de perguntas rodar inteiramente no navegador:
instantâneo, sem rede, sem custo de modelo e **sem depender do backend estar no ar**. Eliminá-lo
em favor de chamadas à API transformaria toda pergunta hoje determinística em inferência de LLM,
sujeita a timeout e limite de uso, e removeria a resposta offline — que é função, não detalhe.

## Consequences

Os dois resolvedores podem divergir silenciosamente. A proteção é um teste de contrato: os
mesmos números de referência são conferidos nas duas linguagens, e a suíte falha se um lado
discordar do outro. Quem mexer numa das cinco agregações precisa rodar os dois lados.
