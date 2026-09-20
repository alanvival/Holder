# Score de risco e índice de alerta coexistem como conceitos distintos

Status: aceita

O projeto tem duas formas de responder "quem está em risco?": um **score de risco** produzido
por regressão logística treinada contra os cancelamentos reais da base, e um **índice de
alerta** que soma sinais observáveis com pesos derivados dos dados. Antes desta decisão os dois
se chamavam "risco", em três implementações e com três escalas diferentes (0-100 probabilístico,
0-100 de pontos e contagem de strikes), o que fazia o dashboard e o assistente darem respostas
diferentes para a mesma pergunta.

Decidimos **manter os dois** e separá-los pelo vocabulário: o score de risco responde "em que
ordem falar?" e o índice de alerta responde "por quê?". O rename vai até o texto de tela e as
descrições das ferramentas expostas ao modelo de IA, e cada escala tem cores próprias.

## Considered Options

- **Unificar num só score** (o treinado como canônico, o heurístico como mera evidência): mais
  simples, mas perderia a explicação por sinal que o enunciado do desafio pede explicitamente
  ("mostrando a evidência que sustenta o alerta").
- **O heurístico como canônico** e o modelo treinado como material de metodologia: descartada
  porque o enunciado pede descobrir os pesos nos dados em vez de opinar.

## Consequences

Dois conceitos exigem disciplina de nomenclatura permanente. A ferramenta de IA que lista
clientes por índice de alerta e a que lista por score de risco precisam de descrições que as
distingam — sem isso o modelo escolhe a errada, que é justamente a divergência mais visível
numa demonstração ao vivo.
