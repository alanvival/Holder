"""
Ponte entre o fallback de IA (que lê a planilha via dados.py) e o score
PREDITIVO de cancelamento (holder/dominio/risco/, que lê do
SQL Server, populados por ingestao.py) — os dois motores de dados do
projeto ainda são separados (um por arquivo Excel, outro por banco), mas a
IA precisa conseguir responder sobre os dois. Este módulo só lê o
histórico já persistido (fScoreRisco, tabela populada pelo job mensal de
holder/aplicacao/treino.py) — nunca recalcula o modelo na hora, pra não pagar o custo
de treino/predição a cada pergunta do chat.

Se o SQL Server não estiver acessível (banco fora do ar, driver não
instalado etc.), devolve um erro estruturado em vez de derrubar o
fallback de IA inteiro — a pergunta cai em "não encontrei" normalmente.
"""
from __future__ import annotations

import time

from holder.dominio.risco import ACAO_POR_FAIXA
from holder.infra.persistencia import historico_score

# Antes havia um sys.path.insert aqui: o módulo de score morava na raiz do
# repo, fora de qualquer pacote, e o import só resolvia se o processo
# tivesse sido iniciado a partir da raiz. Com a persistência dentro de
# `holder/`, o import é direto e não depende de onde o processo subiu.

# Cache em memória do histórico completo, com TTL curto — fScoreRisco só
# muda quando o job mensal de treino roda (nunca no meio de uma conversa),
# então reler do SQL Server em toda pergunta é custo puro, sem ganho de
# atualidade. Sob pressão de memória da máquina (ambiente documentado:
# RAM livre caindo a ~600MB com Vite+Flask+Streamlit+Chrome juntos), essa
# leitura sozinha já foi observada ao vivo levando mais de 120s — cachear
# faz só a PRIMEIRA pergunta depois de o processo subir pagar esse custo;
# todas as outras (inclusive as sugestões de "continuar a conversa" do
# próprio widget, que senão caíam em "não encontrei" por timeout) respondem
# na hora. TTL de 5min é só uma rede de segurança pra não ficar servindo
# dado stale indefinidamente se alguém rodar o treino com o servidor no ar.
_CACHE_TTL_SEGUNDOS = 300
_cache_historico = {"df": None, "carregado_em": 0.0}


def _carregar_historico():
    agora = time.monotonic()
    if _cache_historico["df"] is not None and (agora - _cache_historico["carregado_em"]) < _CACHE_TTL_SEGUNDOS:
        return _cache_historico["df"]
    df = historico_score.carregar_historico()
    _cache_historico["df"] = df
    _cache_historico["carregado_em"] = agora
    return df


def _mes_anterior(mes_ref: str) -> str:
    ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
    idx = ano * 12 + (mes - 1) - 1
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def listar_previsao_risco(filtros: dict | None = None, limite: int = 20) -> dict:
    """
    Lista clientes ordenados por probabilidade PREVISTA de cancelamento
    (modelo de regressão logística treinado e validado — AUC~0.95, ver
    testes/test_modelo_risco.py), não um diagnóstico do histórico passado.
    filtros aceita: faixa ('Crítico'/'Em risco'/'Atenção'/'Saudável') e
    tendencia ('subindo'/'caindo'/'estavel') — a tendência só pode ser
    filtrada DEPOIS de calculada (compara com o mês anterior), por isso o
    filtro é aplicado depois do merge, não antes como faixa.
    """
    import json
    try:
        hist = _carregar_historico()
    except Exception as exc:
        return {"erro": f"Não consegui acessar o histórico de previsão de risco (SQL Server indisponível?): {exc}"}

    if hist.empty:
        return {"erro": "Sem histórico de score de risco salvo ainda. Rode `python -m holder.aplicacao.treino` pra treinar e popular."}

    mes_atual = hist["mes_ref"].max()
    mes_ant = _mes_anterior(mes_atual)
    linhas_atual = hist[hist["mes_ref"] == mes_atual].copy()
    linhas_ant = hist[hist["mes_ref"] == mes_ant][["cliente_id", "risco_percentual"]].rename(columns={"risco_percentual": "risco_anterior"})
    linhas_atual = linhas_atual.merge(linhas_ant, on="cliente_id", how="left")

    filtros = filtros or {}
    faixa = filtros.get("faixa")
    if faixa:
        linhas_atual = linhas_atual[linhas_atual["faixa"] == faixa]

    def _tendencia(r):
        if r["risco_anterior"] != r["risco_anterior"]:  # NaN
            return "sem_dado_anterior"
        delta = r["risco_percentual"] - r["risco_anterior"]
        return "subindo" if delta > 3 else ("caindo" if delta < -3 else "estavel")

    linhas_atual = linhas_atual.assign(tendencia=linhas_atual.apply(_tendencia, axis=1))

    tendencia_filtro = filtros.get("tendencia")
    if tendencia_filtro:
        linhas_atual = linhas_atual[linhas_atual["tendencia"] == tendencia_filtro]

    total_no_filtro = len(linhas_atual)
    linhas_atual = linhas_atual.sort_values("risco_percentual", ascending=False)
    limite = max(1, min(limite or 20, 100))
    pagina = linhas_atual.head(limite)

    clientes = [
        {
            "cliente_id": r["cliente_id"],
            "risco_percentual": round(r["risco_percentual"], 1),
            "faixa": r["faixa"],
            "tendencia": r["tendencia"],
            "acao_sugerida": ACAO_POR_FAIXA.get(r["faixa"], ""),
        }
        for _, r in pagina.iterrows()
    ]

    return {
        "mes_referencia": mes_atual,
        "total_clientes": total_no_filtro,
        "clientes": clientes,
        "truncado": total_no_filtro > limite,
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
        "acao_sugerida": ACAO_POR_FAIXA.get(atual["faixa"], ""),
        "sinais_detalhados": sinais,
        "trajetoria_ultimos_meses": trajetoria,
        "nota": (
            "Probabilidade prevista por modelo de regressão logística (não heurística) — "
            "sinais_detalhados mostra a contribuição de cada variável (coeficiente × desvio) "
            "pra essa probabilidade específica. Quando um sinal tiver 'media_cancelados', é a "
            "mediana histórica (média, no caso de reclamações) desse indicador entre TODOS os "
            "meses de clientes que já cancelaram — a comparação mais objetiva disponível. "
            "Cite valor_atual lado a lado com media_cancelados nesses sinais (ex: 'SLA "
            "cumprido: 75% — mediana de quem já cancelou: 68%'), sem qualificar como "
            "'bom'/'ruim' além do que os dois números já mostram. acao_sugerida é a "
            "recomendação padrão da faixa — use isso pra responder 'o que fazer', não invente "
            "outra ação."
        ),
    }
