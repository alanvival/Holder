"""
Port da tool `buscar_registro_cliente` — busca pontual sobre um cliente
específico. Mesma fonte de dados de metricas.py (dados.py), sem cálculo
agregado nenhum: aqui é sempre "o que está registrado", nunca uma conta.

Nota: o enum de `campo` no prompt inclui "ultimo_acompanhamento", que é um
conceito do domínio mock genérico do Assistente de Consultas (pessoas/
acompanhamentos em src/data/mockDatabase.js) — a base do desafio INOVAAPPS
não tem essa tabela. Tratado abaixo como "campo não aplicável a esta base"
em vez de estourar erro ou inventar dado.
"""
from __future__ import annotations

from . import dados


def _historico_chamados(cliente_id: str) -> dict:
    df = dados.atendimento_mensal[dados.atendimento_mensal["cliente_id"] == cliente_id]
    df = df.sort_values("mes_ref").tail(6)
    if len(df) == 0:
        return {"erro": "Sem histórico de atendimento para esse cliente."}
    return {
        "cliente_id": cliente_id,
        "meses": [
            {
                "mes_ref": row.mes_ref,
                "chamados_abertos": int(row.chamados_abertos),
                "chamados_criticos": int(row.chamados_criticos),
                "pct_sla_cumprido": None if row.pct_sla_cumprido != row.pct_sla_cumprido else float(row.pct_sla_cumprido),
            }
            for row in df.itertuples()
        ],
    }


def _historico_nps(cliente_id: str) -> dict:
    df = dados.pesquisas_nps[dados.pesquisas_nps["cliente_id"] == cliente_id]
    df = df.sort_values("mes_ref")
    if len(df) == 0:
        return {"erro": "Sem pesquisas de NPS registradas para esse cliente."}
    return {
        "cliente_id": cliente_id,
        "pesquisas": [
            {
                "mes_ref": row.mes_ref,
                "respondeu": bool(row.respondeu),
                "nota_nps": None if row.nota_nps != row.nota_nps else float(row.nota_nps),
                "classificacao_nps": row.classificacao_nps,
            }
            for row in df.itertuples()
        ],
    }


def buscar_registro_cliente(cliente_id: str, campo: str) -> dict:
    if not dados.cliente_existe(cliente_id):
        return {"erro": f"Cliente {cliente_id} não encontrado na base."}

    if campo == "situacao":
        situacao = dados.buscar_situacao(cliente_id)
        return {"cliente_id": cliente_id, **situacao} if situacao else {"erro": "Situação não encontrada."}

    if campo == "plano":
        cliente = dados.buscar_cliente(cliente_id)
        return {
            "cliente_id": cliente_id,
            "plano": cliente["plano"],
            "porte": cliente["porte"],
            "segmento": cliente["segmento"],
            "valor_mensal": float(cliente["valor_mensal"]),
        }

    if campo == "historico_chamados":
        return _historico_chamados(cliente_id)

    if campo == "historico_nps":
        return _historico_nps(cliente_id)

    if campo == "ultimo_acompanhamento":
        return {"erro": "Campo não aplicável a esta base — a INOVAAPPS não tem registro de acompanhamentos."}

    return {"erro": f"Campo desconhecido: {campo}"}
