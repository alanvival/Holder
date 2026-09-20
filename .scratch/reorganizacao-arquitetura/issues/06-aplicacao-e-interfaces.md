# 06 — `holder/aplicacao/` e `holder/interfaces/`

Status: aberto
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

## Comandos novos (decisão Q5=b — sem stubs de compatibilidade)

```
streamlit run holder/interfaces/dashboard/app.py
python -m holder.interfaces.api
python -m holder.infra.etl.ingestao
python -m holder.dominio.risco.modelo
```

## Verificação

`pytest` + conferência visual das 3 abas + chat respondendo (catálogo e fallback de IA).
