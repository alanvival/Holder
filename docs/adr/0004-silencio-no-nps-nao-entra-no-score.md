# Silêncio no NPS não entra no score, porque não separa nesta base

Status: aceita

O enunciado do desafio destaca, em itálico, uma observação sobre o NPS:

> O que costuma informar é a nota lida junto com as demais, sua trajetória ao longo do tempo e
> o fato de o cliente ter deixado de responder, **ausência de resposta não é dado faltante, é
> comportamento**.

É uma pista explícita, e o projeto filtra `respondeu == 1` em todos os cálculos — ou seja,
trata a ausência de resposta exatamente como dado faltante, o oposto do que a pista sugere.

Antes de mudar isso, **medimos**. Nas 422 pesquisas da base (338 respondidas, 84 ignoradas):

| Recorte | Ativos | Cancelados |
|---|---|---|
| Taxa média de resposta por cliente | 81,0% | 75,2% |
| Ignorou o **último** convite | 27,6% | 22,7% |
| Ignorou os **dois últimos** convites | 4 clientes | 2 clientes |

Entre os 6 clientes que ficaram em silêncio nos dois últimos convites, 33,3% cancelaram —
contra 27,0% entre os 74 que responderam. Uma diferença de 6 pontos percentuais sobre uma
amostra de 6 clientes.

Decidimos **não usar o silêncio como sinal do score**. Nesta base ele não separa: clientes
ativos ignoram o último convite com frequência *maior* que os cancelados. Incluí-lo adicionaria
um sinal que dispara para 27,6% dos ativos sem distinguir quem sai de quem fica — exatamente o
alarme falso que o enunciado pede para evitar ("alarme falso faz a equipe deixar de olhar").

## Considered Options

- **Incluir como variável do modelo** (taxa de resposta, ou flag de silêncio recente): seria
  seguir a pista ao pé da letra. Descartada porque os números acima mostram que o sinal não
  separa — e o enunciado é claro que a definição dos pesos "faz parte do que será avaliado" e
  deve sair dos dados, não da opinião. Seguir uma pista contra a evidência da própria base
  seria opinar.
- **Incluir só como evidência na tela, sem entrar no score**: descartada por enquanto porque
  "este cliente parou de responder" ao lado de um score que não considera isso convida à
  leitura errada de que o silêncio pesou no número.
- **Ignorar a pista em silêncio**: é o que estava acontecendo por omissão. Descartada porque a
  observação é explícita no enunciado, e não responder a ela parece descuido, não decisão.

## Consequences

O silêncio continua fora do score e fora do índice de alerta. Em compensação, a decisão fica
registrada com o número que a sustenta — se a base crescer e o sinal passar a separar, este
documento é o ponto de partida para reavaliar, e a medição é reproduzível a partir da própria
base.

Vale notar o que **é** usado: a última classificação de NPS considerada é sempre a última em
que o cliente de fato respondeu (ver `holder/dominio/strikes/nps_recente.py`), e não a última
linha de pesquisa. Sem esse cuidado, um cliente que foi detrator e depois ignorou o convite
seguinte perdia o strike — três clientes nesta base.
