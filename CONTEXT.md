# Prevenção de cancelamento

Acompanhamento de uma carteira de contratos recorrentes para identificar, entre os clientes
ativos, quais estão em risco de cancelar — mostrando a evidência que sustenta o alerta e em
que ordem falar com cada um.

## Language

### Carteira e contrato

**Carteira**:
Conjunto de clientes sob acompanhamento do time de relacionamento.
_Avoid_: base, portfólio

**Cliente**:
Organização que mantém um contrato recorrente.
_Avoid_: conta, empresa, usuário

**Contrato**:
Acordo de serviço recorrente, com valor mensal fixo e SLA contratado em horas.
_Avoid_: plano (plano é uma característica do contrato, não o contrato)

**Valor mensal**:
Receita recorrente de um contrato. É o que está em jogo quando o cliente sai.
_Avoid_: ticket, mensalidade, MRR

**Situação**:
Se o contrato está Ativo ou Cancelado.
_Avoid_: status, estado

**Cancelamento**:
Encerramento do contrato por decisão do cliente, com um mês de saída registrado.
_Avoid_: churn, desistência, perda

**Mês de referência**:
O mês a que se refere um registro mensal de atendimento.
_Avoid_: período, competência

### Risco, alerta e strikes

São **três conceitos distintos**, com mecanismos, escalas e propósitos diferentes. Não são
sinônimos e não se substituem:

| Conceito | Compara o cliente com | Responde |
|---|---|---|
| Score de risco | os cancelamentos reais da base, via modelo treinado | "em que ordem falar?" |
| Índice de alerta | a **própria história** dele | "este cliente piorou?" |
| Strikes | o **perfil de quem já cancelou** | "este cliente se parece com quem saiu?" |

A diferença entre os dois últimos é observável: um cliente sempre-ruim-mas-estável dispara
strikes e **não** dispara índice de alerta; um cliente ótimo que piorou de repente dispara o
índice de alerta e **pode não** disparar strike nenhum.

**Score de risco**:
Probabilidade estimada, por modelo treinado nos cancelamentos já ocorridos, de que o cliente
esteja nos meses que antecedem uma saída.
_Avoid_: risco, score, probabilidade de churn

**Faixa**:
Classificação de um score de risco em Saudável, Atenção, Em risco ou Crítico.
_Avoid_: nível, banda, categoria

**Índice de alerta**:
Soma ponderada dos sinais de alerta observados no comportamento recente de um cliente. É
composição de pontos, não probabilidade.
_Avoid_: score heurístico, risco heurístico, termômetro

**Nível de alerta**:
Classificação de um índice de alerta em Alto, Médio ou Baixo.
_Avoid_: faixa (faixa é do score de risco)

**Sinal de alerta**:
Uma das oito condições que compõem o índice de alerta, cada uma comparando o mês mais recente
do cliente com a média dos meses anteriores **dele**: queda de SLA, queda de uso, atraso de
pagamento crescente, chamados críticos, chamados reabertos, reunião prevista não realizada,
reclamação formal, último NPS detrator.
_Avoid_: strike, feature, indicador, flag

**Strike**:
Uma das quatro condições que indicam semelhança com quem já cancelou, cada uma comparando o
cliente ativo com a linha de corte extraída do perfil de quem saiu: SLA crítico, lentidão de
resolução, reclamação recente, último NPS detrator.
_Avoid_: sinal de alerta (mecanismo diferente: sinal olha a própria história, strike olha o
perfil de quem cancelou)

**Linha de corte**:
O valor de referência de um strike, tirado dos meses de clientes já cancelados — mediana, ou
média nas contagens esparsas como reclamações formais.
_Avoid_: threshold, limite, meta

**Recência**:
Os dois últimos meses **em que houve medição** para aquele cliente. Deliberadamente não é o
calendário: um cliente sem registro no mês corrente não deve ter seus sinais escondidos.
_Avoid_: mês corrente, último mês

**Fator de cancelamento**:
Variável cuja média difere entre clientes ativos e cancelados, usada para derivar o peso de
cada sinal de alerta a partir dos dados em vez de por opinião.
_Avoid_: driver, causa, correlação

**Ordem de atendimento**:
Sequência priorizada de clientes com quem falar, cruzando score de risco com valor mensal. É o
resultado esperado da solução — não um número por cliente.
_Avoid_: ranking de risco, lista de risco

### Métricas e consultas

**Métrica**:
Cálculo agregado sobre a carteira, com fórmula própria e identificador estável (ticket médio,
SLA cumprido, taxa de cancelamento, NPS da carteira).
_Avoid_: indicador, KPI

**Campo**:
Atributo de cliente ou de registro mensal que pode ser lido diretamente, sem cálculo.
_Avoid_: coluna, variável

**Intenção**:
Pergunta que o catálogo reconhece e responde sem recorrer a IA generativa.
_Avoid_: intent, comando

**Catálogo**:
Conjunto de intenções resolvidas de forma determinística, sem chamada de rede.
_Avoid_: base de perguntas

**Fallback de IA**:
Caminho acionado apenas quando o catálogo não reconhece a pergunta. A IA escolhe a consulta;
quem calcula é sempre o domínio.
_Avoid_: IA, chatbot, assistente (o assistente é a interface, não o fallback)

**Pergunta cadastrada**:
Intenção criada pelo administrador em tempo de execução, sem alteração de código.
_Avoid_: pergunta customizada

**Sugestão**:
Pergunta que ninguém soube responder, registrada para triagem do administrador.
_Avoid_: feedback, dúvida

**Não-resposta**:
Convite de pesquisa de satisfação enviado e não respondido. É comportamento observado, não
dado faltante, e conta como sinal.
_Avoid_: dado faltante, nulo, sem resposta

**Tenant**:
Placeholder declarado de multi-organização. Não é funcionalidade: nenhuma decisão do produto
depende dele hoje.
_Avoid_: tratar tenant como isolamento real de dados
