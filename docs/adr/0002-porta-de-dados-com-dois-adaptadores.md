# Porta de dados com dois adaptadores (SQL Server e Excel coexistem)

Status: aceita

A mesma planilha do desafio alimenta dois caminhos independentes: um ETL que carrega um modelo
dimensional no SQL Server (de onde vêm o dashboard e o score de risco) e uma leitura direta em
memória (de onde vêm o assistente e os dados do front). Um leitor razoável assumiria que isso é
acidente a ser corrigido.

É deliberado. Decidimos **unificar o acesso, não a fonte**: uma porta de leitura com dois
adaptadores, escolhidos por configuração. O modelo dimensional é narrativa técnica que vale a
pena manter de pé, e a leitura direta da planilha é o que permite o assistente funcionar sem o
banco no ar.

## Considered Options

- **SQL Server como fonte única**: transformaria uma dependência hoje opcional em obrigatória
  para o assistente — mais um jeito de a demonstração falhar.
- **Excel como fonte única**: rodaria em qualquer máquina sem instalar SQL Server, mas jogaria
  fora o ETL e o modelo dimensional.

## Consequences

Os dois adaptadores precisam devolver as mesmas quatro tabelas com os mesmos tipos. Divergência
entre eles não aparece como erro, e sim como número diferente — é o risco que esta decisão
aceita em troca de robustez de demonstração.
