"""
Ponte entre o fallback de IA (que lê a planilha via dados.py) e o score
PREDITIVO de cancelamento (modelo_risco.py + score_risco.py, que leem do
SQL Server, populados por ingestao.py) — os dois motores de dados do
projeto ainda são separados (um por arquivo Excel, outro por banco), mas a
IA precisa conseguir responder sobre os dois. Este módulo só lê o
histórico já persistido (fScoreRisco, tabela populada pelo job mensal de
modelo_risco.py) — nunca recalcula o modelo na hora, pra não pagar o custo
de treino/predição a cada pergunta do chat.

Se o SQL Server não estiver acessível (banco fora do ar, driver não
instalado etc.), devolve um erro estruturado em vez de derrubar o
fallback de IA inteiro — a pergunta cai em "não encontrei" normalmente.
"""
from __future__ import annotations

import sys
from pathlib import Path

# score_risco.py/modelo_risco.py moram na raiz do repo, fora do pacote
# fallback_ia — funciona quando o processo roda a partir da raiz (`python
# server.py`), mas garantimos o path aqui também pra não depender de onde
# o processo foi iniciado.
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))


def _carregar_historico():
    import score_risco as sr
    return sr.carregar_historico()


def _mes_anterior(mes_ref: str) -> str:
    ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
    idx = ano * 12 + (mes - 1) - 1
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


# Ação sugerida por faixa — dado estruturado (não a IA "decidindo" sozinha
# o que recomendar a cada resposta, texto fixo e auditável por faixa,
# igual as próprias faixas em score_risco.FAIXAS).
_ACAO_POR_FAIXA = {
    "Saudável": "Nenhuma ação necessária — monitoramento passivo.",
    "Atenção": "Sinalizar no radar do CS responsável, sem alerta ativo ainda — acompanhar a tendência do próximo mês.",
    "Em risco": "Alerta ativo: o CS deve investigar a causa (ver sinais_detalhados) e agendar contato proativo com o cliente.",
    "Crítico": "Alerta prioritário — ação imediata recomendada: contato executivo, plano de retenção e revisão do relacionamento nos próximos dias.",
}


def listar_previsao_risco(filtros: dict | None = None, limite: int = 20) -> dict:
    """
    Lista clientes ordenados por probabilidade PREVISTA de cancelamento
    (modelo de regressão logística treinado e validado — AUC~0.95, ver
    testar_modelo_risco.py), não um diagnóstico do histórico passado.
    filtros aceita: faixa ('Crítico'/'Em risco'/'Atenção'/'Saudável').
    """
    import json
    try:
        hist = _carregar_historico()
    except Exception as exc:
        return {"erro": f"Não consegui acessar o histórico de previsão de risco (SQL Server indisponível?): {exc}"}

    if hist.empty:
        return {"erro": "Sem histórico de score de risco salvo ainda. Rode `python modelo_risco.py` pra treinar e popular."}

    mes_atual = hist["mes_ref"].max()
    mes_ant = _mes_anterior(mes_atual)
    linhas_atual = hist[hist["mes_ref"] == mes_atual].copy()
    linhas_ant = hist[hist["mes_ref"] == mes_ant][["cliente_id", "risco_percentual"]].rename(columns={"risco_percentual": "risco_anterior"})
    linhas_atual = linhas_atual.merge(linhas_ant, on="cliente_id", how="left")

    filtros = filtros or {}
    faixa = filtros.get("faixa")
    if faixa:
        linhas_atual = linhas_atual[linhas_atual["faixa"] == faixa]

    linhas_atual = linhas_atual.sort_values("risco_percentual", ascending=False)
    limite = max(1, min(limite or 20, 100))
    pagina = linhas_atual.head(limite)

    clientes = []
    for _, r in pagina.iterrows():
        tendencia = "sem_dado_anterior"
        if r["risco_anterior"] == r["risco_anterior"]:  # not NaN
            delta = r["risco_percentual"] - r["risco_anterior"]
            tendencia = "subindo" if delta > 3 else ("caindo" if delta < -3 else "estavel")
        clientes.append({
            "cliente_id": r["cliente_id"],
            "risco_percentual": round(r["risco_percentual"], 1),
            "faixa": r["faixa"],
            "tendencia": tendencia,
            "acao_sugerida": _ACAO_POR_FAIXA.get(r["faixa"], ""),
        })

    return {
        "mes_referencia": mes_atual,
        "total_clientes": len(linhas_atual),
        "clientes": clientes,
        "truncado": len(linhas_atual) > limite,
        "nota": (
            "risco_percentual é a probabilidade real prevista por um modelo de regressão "
            "logística treinado e validado (AUC~0.95, Brier~0.085) contra os cancelamentos "
            "reais da base — não é uma nota heurística. Faixas: Saudável (0-29%), Atenção "
            "(30-54%), Em risco (55-74%), Crítico (75-100%). acao_sugerida é a recomendação "
            "padrão da faixa — use isso pra responder 'o que fazer', não invente outra ação."
        ),
    }


def detalhar_previsao_cliente(cliente_id: str) -> dict:
    """Detalhe da previsão de UM cliente: probabilidade atual, tendência,
    explicabilidade (quais sinais mais contribuem) e trajetória recente."""
    import json
    try:
        hist = _carregar_historico()
    except Exception as exc:
        return {"erro": f"Não consegui acessar o histórico de previsão de risco (SQL Server indisponível?): {exc}"}

    if hist.empty:
        return {"erro": "Sem histórico de score de risco salvo ainda."}

    cliente_id = cliente_id.strip().upper() if cliente_id else cliente_id
    if cliente_id and cliente_id.startswith("C") and len(cliente_id) > 1:
        cliente_id = "C" + cliente_id[1:].replace("O", "0")

    hist_cliente = hist[hist["cliente_id"] == cliente_id].sort_values("mes_ref")
    if hist_cliente.empty:
        return {"erro": f"Sem previsão salva pra {cliente_id} (cliente inexistente, ou ainda sem histórico suficiente)."}

    atual = hist_cliente.iloc[-1]
    sinais = json.loads(atual["sinais_detalhados"])

    trajetoria = [
        {"mes_ref": r["mes_ref"], "risco_percentual": round(r["risco_percentual"], 1)}
        for _, r in hist_cliente.tail(6).iterrows()
    ]

    return {
        "cliente_id": cliente_id,
        "mes_referencia": atual["mes_ref"],
        "risco_percentual": round(atual["risco_percentual"], 1),
        "faixa": atual["faixa"],
        "acao_sugerida": _ACAO_POR_FAIXA.get(atual["faixa"], ""),
        "sinais_detalhados": sinais,
        "trajetoria_ultimos_meses": trajetoria,
        "nota": (
            "Probabilidade prevista por modelo de regressão logística (não heurística) — "
            "sinais_detalhados mostra a contribuição de cada variável (coeficiente × desvio) "
            "pra essa probabilidade específica. acao_sugerida é a recomendação padrão da "
            "faixa — use isso pra responder 'o que fazer', não invente outra ação."
        ),
    }
