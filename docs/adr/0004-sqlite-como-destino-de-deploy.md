# SQLite é o destino de gravação no deploy

Status: aceita

O ADR 0002 registrou dois adaptadores de **leitura** da carteira: SQL Server e planilha. A
planilha resolve ler as quatro tabelas do domínio sem banco no ar, e é isso que permite o
assistente responder offline. Mas ela não resolve o deploy do dashboard, porque duas tabelas
não vêm da planilha: `fScoreRisco` e `fModeloRiscoLog` são **resultado de treino**, existem só
como tabela, e sem elas a aba "Score de Risco" não sobe.

O host do deploy (Streamlit Cloud) é Linux, sem o driver ODBC da Microsoft e sem alcance ao
`localhost` da máquina de desenvolvimento. Publicar um SQL Server gerenciado resolveria, mas
custa dinheiro ou exige cadastro em serviço externo para um dashboard que é leitura pura.

A decisão: `conexao.criar_engine()` passa a escolher o banco por `HOLDER_BANCO`, com
`sqlserver` como padrão. O deploy liga `sqlite` e lê um arquivo versionado em
`dados/holder.sqlite3`, gerado por `scripts/gerar_banco_de_deploy.py` mais a ingestão normal.

O que **não** muda: sem a variável, tudo se comporta exatamente como antes. Quem roda local
não configura nada. A string ODBC, o `Encrypt=no` e o modelo dimensional continuam intactos.

## Consequences

O arquivo SQLite é um **retrato**, não um banco vivo. O filesystem do Streamlit Cloud é
efêmero: escritas (`salvar_mes`, `registrar`) sobrevivem até o container reiniciar e depois
voltam ao que foi commitado. Isso é aceitável porque o treino roda na máquina de quem
desenvolve e o dashboard, em produção, só lê — mas significa que **treinar pelo app publicado
não persiste**. Se um dia o treino passar a rodar no host, este ADR precisa ser revisto.

O retrato pode ficar defasado em relação ao SQL Server sem que nada acuse. A proteção é a
mesma do ADR 0002 e tem o mesmo limite: `testes/test_banco_sqlite.py` garante que o SQLite
responde com as contagens do enunciado, não que ele esteja sincronizado com o banco local.
Regerar o arquivo é passo manual de quem publica.

Há agora uma terceira DDL a manter em sincronia: `historico_score.DDL` e `log_treinos.DDL`
têm uma entrada por dialeto, e criar coluna num sem criar no outro só aparece no deploy.
