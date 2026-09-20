# Desafio INOVAAPPS 2026: Prevenção de Cancelamento (Churn)

## 1. Contexto Geral do Negócio
O modelo de negócio é de contrato recorrente. O cliente paga um valor mensal fixo para ter sua operação atendida, e a empresa aloca horas técnicas para entregar o serviço. 
Isso define a economia do negócio: enquanto o cliente permanece, a receita se repete sem novo esforço de venda; quando ele sai, a empresa perde uma anuidade inteira e ainda gasta para conquistar um substituto. **Reter custa uma fração do que custa conquistar.**

## 2. Contexto do Desafio
A carteira analisada reúne 80 clientes, atendidos por um time pequeno de relacionamento. Nos últimos dezoito meses, 22 deles cancelaram, representando cerca de R$ 275 mil de receita mensal, ou R$ 3,3 milhões ao ano.

Em praticamente todos os casos, a empresa só soube da saída quando o cliente comunicou a decisão e, quando isso acontece, a decisão já foi tomada internamente há semanas. 
Os sinais existiam. Olhando o histórico depois do fato, esses clientes vinham há meses usando menos o serviço, abrindo chamados que demoravam mais para fechar, faltando às reuniões, atrasando pagamentos, recebendo atendimento fora do prazo contratado e dando notas menores nas pesquisas de satisfação quando respondiam.

**O problema não é falta de dado. É que ninguém lê esses dados em conjunto, nem a tempo.**

### 2.1. Modelo atual de acompanhamento
* Chamados, SLA e pesquisas de satisfação são registrados, mas cada um vive em um relatório próprio e ninguém compila os três juntos.
* A percepção sobre a saúde de cada conta depende de quem está mais próximo dela.
* Um cliente que reclama pouco recebe pouca atenção, mesmo quando está se afastando.
* A empresa age depois que o problema aparece e aí a negociação já é de desconto, não de valor.

### 2.2. Riscos de manter o modelo atual
* Perda de receita recorrente que poderia ter sido preservada.
* Descoberta tardia, quando a única saída é conceder desconto.
* Atenção concentrada em quem reclama, não em quem corre risco.
* Clientes de alto valor tratados com a mesma prioridade de clientes pequenos.
* Dependência do *feeling* de quem atende, que se perde quando a pessoa sai.
* Impossibilidade de aprender com os cancelamentos já ocorridos.

---

## 3. O Desafio (O que precisa ser desenvolvido)
**Cenário:** Você recebe o histórico de dezoito meses dessa carteira (chamados, SLA, uso, pagamento, reuniões e pesquisas de satisfação), incluindo os 22 clientes que cancelaram e o mês em que cada um saiu.

**Objetivo:** Desenvolver uma solução digital que identifique, entre os clientes ainda ativos, quais estão em risco de cancelar, mostrando a evidência que sustenta o alerta e o que deve ser feito a respeito.

**O teste de completude:** Ao abrir a solução, alguém que trabalha com a carteira precisa conseguir responder três perguntas:
1. Com quais clientes falar?
2. Por que cada um deles?
3. Em que ordem?

*Nota:* Como a solução se organiza para responder a isso é decisão do grupo. Não há formato de tela, tecnologia ou técnica obrigatória. O resultado esperado não é um número por cliente, e sim uma ordem de atendimento que alguém possa seguir.

### 3.1. Como definir o que pesa mais
Este enunciado não atribui peso a nenhuma variável de propósito. Mapear as variáveis e definir como elas se combinam é o núcleo do desafio. A base permite descobrir, em vez de opinar: os 22 cancelamentos trazem o mês exato da saída. É possível observar como cada variável se comportou nos meses que antecederam cada uma delas e comparar com os clientes que permaneceram.

Três perguntas ajudam a estruturar esse trabalho:
1. **Com quanta antecedência o sinal aparece?** Um sinal que só se manifesta no mês da saída pode ser certeiro e, ainda assim, inútil: não sobra tempo de agir.
2. **Quão bem ele separa?** Um sinal que também aparece em muitos clientes que permaneceram gera alarme falso, e alarme falso faz a equipe deixar de olhar.
3. **Quanto está em jogo?** Risco alto em um contrato pequeno e risco médio em um contrato grande não pedem a mesma urgência.

### 3.2. Pontos de partida para a solução
* O que caracteriza um cliente prestes a sair, olhando o histórico dos 22 que já cancelaram?
* Como distinguir uma piora passageira de um afastamento real?
* Como combinar sinais de origens diferentes: atendimento, SLA, uso, pagamento e satisfação?
* Como considerar o tamanho do contrato na hora de priorizar?
* Como evitar o excesso de alarme?
* Qual seria o modelo de negócio de uma solução como essa?

---

## 4. Dados de Referência
**Arquivo:** `INOVAAPPS_base_de_dados.xlsx`
* 80 clientes, com o histórico mensal de janeiro de 2025 a junho de 2026.
* 1.295 linhas de atendimento (uma por cliente por mês).
* 422 registros de pesquisa de satisfação.
* 22 clientes cancelaram no período; 58 seguem ativos.

### 4.1. Variáveis disponíveis para análise
São dezessete variáveis de origens diferentes. Nenhuma delas explica um cancelamento sozinha.

* **Contrato e cliente:** Segmento, porte, plano, valor mensal, SLA contratado em horas e data de início.
* **Volume e criticidade:** Chamados abertos no mês e chamados críticos.
* **Reincidência:** Chamados reabertos (os que voltaram depois de dados como resolvidos).
* **Cumprimento de prazo:** Chamados resolvidos dentro do SLA, percentual de SLA cumprido no mês e tempo médio de resolução.
* **Insatisfação declarada:** Reclamações formais e a pesquisa de NPS (nota de 0 a 10, classificação em promotor, neutro ou detrator, e o registro de quem foi convidado e não respondeu).
* **Engajamento:** Uso da plataforma e reuniões previstas contra realizadas.
* **Saúde financeira:** Dias de atraso de pagamento.
* **Desfecho:** Ativo ou cancelado, com o mês da saída.

**Observação sobre o NPS:** A nota é apenas mais uma variável, e não vale por si só. Um detrator pode permanecer anos e um promotor pode cancelar. O que costuma informar é a nota lida junto com as demais, sua trajetória ao longo do tempo e o fato de o cliente ter deixado de responder. **Ausência de resposta não é dado faltante, é comportamento.**