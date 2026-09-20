# 06 — `holder/aplicacao/` e `holder/interfaces/`

Status: resolvido

## Resultado

`74 passed`. Os dois comandos novos sobem: `python -m holder.interfaces.api` responde
`/api/health`, e `streamlit run holder/interfaces/dashboard/app.py` devolve 200. A raiz do repo
não tem mais nenhum `.py`.

`app.py` saiu de 549 linhas para 55: `estilo.py` (CSS e as cores de faixa, que estavam
declaradas duas vezes no mesmo arquivo), `matriz.py`, `monitor.py` e `score.py`. Tudo roda
dentro de `main()`, então importar o módulo não dispara interface.

Dois bugs latentes que a divisão eliminou: na fase 5b, um `sed` meu deixou
`historico_score = _carregar_historico_score()` e `log_treinos = log_treinos.carregar()` —
ambos rebindando por cima do módulo importado. Funcionava por acidente (o Streamlit reexecuta
o script inteiro a cada interação, refazendo o import), mas quebraria em qualquer outro
contexto. Agora são `df_historico` e `df_log`.

`cliente_groq.py` foi extraído, mas `_chamar_modelo` **continua em ia_fallback.py e com esse
nome** — é a costura que os 22 casos de teste mockam. Extrair a costura junto com o cliente
quebraria a suíte inteira por ganho nenhum.

`aplicacao/priorizacao/ordem.py` **não foi criado** — seria código novo, não reorganização, e
o ranking de priorização já existe na aba 1 do dashboard. Um módulo que ninguém chama é código
morto.

Lacuna encontrada e deixada visível: `padroes_churn` e `taxa_falso_alarme` são calculados pela
preparação e **não são exibidos por nenhuma aba** — já era assim antes. Ficam nomeados no
desempacotamento, com comentário, em vez de descartados em silêncio.
Fase: 6 de 10 · Bloqueado por: 05

## Entregas

- `aplicacao/assistente/` — `ia_fallback.py`, `tools.py`, `tools_genericas.py`, `campos.py`
  (de `fallback_ia/`). O `sys.path.insert` de `previsao_risco.py:24-26` desaparece: com pacote
  nomeado, não há mais import de módulo solto na raiz.
- `aplicacao/priorizacao/ordem.py` — ordem de atendimento (score × `valor_mensal`), que é a
  resposta à pergunta 3 do teste de completude do enunciado ("em que ordem?").
- `interfaces/api/` — `servidor.py` + rotas (de `server.py`, 12 endpoints).
- `interfaces/dashboard/` — `app.py` **quebrado por aba**: `matriz.py` (`app.py:236-338`),
  `monitor.py` (`:340-425`), `score.py` (`:427-667`). Sem isto, `app.py` continua sendo o
  arquivo de 667 linhas, só noutro endereço.
- Deduplicar `CORES_FAIXA` (`app.py:67`) e `cores_faixa` (`app.py:524`) — mesmos 4 hex, duas
  definições.
- **Herdado da fase 3 (feito)**: tirar `carregar_dados()` do nível do módulo, envolvendo o script num
  `main()`. Só faz sentido aqui, junto da quebra por aba — executar no nível do módulo é o
  contrato do Streamlit, e mexer nisso antes significaria reestruturar o arquivo duas vezes.
  `st.set_page_config()` permanece como primeira chamada, por exigência do Streamlit.

## Comandos novos (decisão Q5=b — sem stubs de compatibilidade)

```
streamlit run holder/interfaces/dashboard/app.py
python -m holder.interfaces.api
python -m holder.infra.etl.ingestao
python -m holder.dominio.risco.modelo
```

## Verificação

`pytest` + conferência visual das 3 abas + chat respondendo (catálogo e fallback de IA).
