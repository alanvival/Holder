from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGINAS = Path(__file__).resolve().parents[1] / "pages"
DASHBOARD = str(PAGINAS / "1_Dashboard.py")
CLIENTES = str(PAGINAS / "2_Clientes.py")
ANALISE = str(PAGINAS / "3_Analise_Mensal.py")

RESUMO = {
    "mes_referencia": "2026-06-01",
    "executado_em": "2026-09-19T12:00:00",
    "clientes_ativos": 58,
    "receita_ativa": 700000.0,
    "receita_em_risco": 12000.0,
    "qtd_na_fila": 1,
    "por_faixa": {"CRITICO": 0, "ATENCAO": 1, "MONITORAR": 15, "SAUDAVEL": 42},
    "por_dimensao": {
        "ATENDIMENTO": 5,
        "SLA": 3,
        "ENGAJAMENTO": 2,
        "FINANCEIRO": 1,
        "SATISFACAO": 9,
    },
}
ITEM_FILA = {
    "posicao": 1,
    "cliente_id": "C080",
    "segmento": "Saude",
    "plano": "ENTERPRISE",
    "porte": "GRANDE",
    "valor_mensal": 20924.0,
    "score_risco": 0.45,
    "faixa": "ATENCAO",
    "receita_em_risco": 9360.0,
    "qtd_dimensoes_afetadas": 5,
    "principais_motivos": ["Chamados reabertos subiram 214% nos últimos 3 meses"],
    "acao_recomendada": {
        "codigo": "COMITE_RETENCAO",
        "titulo": "Ação coordenada de retenção",
        "responsavel": "EXECUTIVO",
        "prazo_dias": 7,
    },
    "ultimo_contato": None,
}
CLIENTE_RESUMO = {
    "cliente_id": "C080",
    "segmento": "Saude",
    "porte": "GRANDE",
    "plano": "ENTERPRISE",
    "valor_mensal": 20924.0,
    "sla_contratado_h": 6,
    "inicio_contrato": "2021-01-01",
    "situacao": "ATIVO",
    "mes_cancelamento": None,
    "score_risco": 0.45,
    "faixa": "ATENCAO",
    "receita_em_risco": 9360.0,
    "posicao_fila": 1,
}
DETALHE = {
    **CLIENTE_RESUMO,
    "avaliacao": {
        "mes_referencia": "2026-06-01",
        "score_risco": 0.45,
        "faixa": "ATENCAO",
        "qtd_dimensoes_afetadas": 5,
        "receita_em_risco": 9360.0,
        "posicao_fila": 1,
        "evidencias": [
            {
                "codigo_sinal": "REABERTOS_TENDENCIA",
                "dimensao": "ATENDIMENTO",
                "texto": "Chamados reabertos subiram 214% nos últimos 3 meses",
                "valor_observado": 2.14,
                "linha_base": 0.7,
                "variacao_pct": 2.14,
                "meses_persistencia": 3,
                "contribuicao": 0.1,
            }
        ],
        "acao_recomendada": {
            "codigo": "COMITE_RETENCAO",
            "titulo": "Ação coordenada de retenção",
            "responsavel": "EXECUTIVO",
            "prazo_dias": 7,
            "descricao": "Montar comitê.",
        },
    },
}
MES = {
    "chamados_abertos": 5,
    "chamados_criticos": 1,
    "chamados_reabertos": 1,
    "chamados_dentro_sla": 4,
    "pct_sla_cumprido": 80.0,
    "tempo_medio_resolucao_h": 10.0,
    "reclamacoes_formais": 0,
    "uso_plataforma_pct": 75.0,
    "dias_atraso_pagamento": 0,
    "reunioes_previstas": 1,
    "reunioes_realizadas": 1,
}
HISTORICO = {
    "cliente_id": "C080",
    "atendimento": [
        {**MES, "mes_ref": "2026-05-01"},
        {**MES, "mes_ref": "2026-06-01", "pct_sla_cumprido": None},
    ],
    "nps": [
        {"mes_ref": "2026-03-01", "respondeu": True, "nota_nps": 8, "classificacao_nps": "NEUTRO"},
        {
            "mes_ref": "2026-06-01",
            "respondeu": False,
            "nota_nps": None,
            "classificacao_nps": "SEM_RESPOSTA",
        },
    ],
}


def _logado(caminho: str) -> AppTest:
    at = AppTest.from_file(caminho, default_timeout=30)
    at.session_state["token"] = "tok"
    at.session_state["usuario"] = {"id": 1, "nome_completo": "Maria", "usuario": "maria"}
    return at


def test_pagina_protegida_sem_login_pede_login(api_falsa):
    at = AppTest.from_file(DASHBOARD, default_timeout=30).run()

    assert not at.exception
    assert "Faça login" in at.warning[0].value
    assert api_falsa.requisicoes == []


def test_dashboard_mostra_kpis_e_fila(api_falsa):
    api_falsa.responder("GET", "/dashboard/resumo", 200, RESUMO)
    api_falsa.responder("GET", "/dashboard/fila", 200, [ITEM_FILA])

    at = _logado(DASHBOARD).run()

    assert not at.exception
    rotulos = [m.label for m in at.metric]
    assert "Receita em risco (mês)" in rotulos
    assert len(at.dataframe) >= 1


def test_dashboard_sem_analise_orienta_importacao(api_falsa):
    vazio = {**RESUMO, "mes_referencia": None, "executado_em": None, "qtd_na_fila": 0}
    api_falsa.responder("GET", "/dashboard/resumo", 200, vazio)
    api_falsa.responder("GET", "/dashboard/fila", 200, [])

    at = _logado(DASHBOARD).run()

    assert not at.exception
    assert "Nenhuma análise" in at.info[0].value


def test_sessao_expirada_desloga_e_avisa(api_falsa):
    api_falsa.responder("GET", "/dashboard/resumo", 401, {"detail": "Token inválido ou expirado"})

    at = _logado(DASHBOARD).run()

    assert not at.exception
    assert any("sessão expirou" in w.value for w in at.warning)
    assert "token" not in at.session_state


def test_clientes_lista_e_detalhe(api_falsa):
    api_falsa.responder(
        "GET", "/clientes", 200, {"itens": [CLIENTE_RESUMO], "total": 1, "pagina": 1, "tamanho": 20}
    )
    api_falsa.responder("GET", "/clientes/C080", 200, DETALHE)
    api_falsa.responder("GET", "/clientes/C080/historico", 200, HISTORICO)

    at = _logado(CLIENTES).run()

    assert not at.exception
    assert len(at.dataframe) >= 1
    textos = " ".join(m.value for m in at.markdown)
    assert "Chamados reabertos subiram 214%" in textos


def test_clientes_sem_resultado(api_falsa):
    api_falsa.responder(
        "GET", "/clientes", 200, {"itens": [], "total": 0, "pagina": 1, "tamanho": 20}
    )

    at = _logado(CLIENTES).run()

    assert not at.exception
    assert "Nenhum cliente" in at.info[0].value


def test_analise_mensal(api_falsa):
    api_falsa.responder(
        "GET",
        "/metricas/variaveis",
        200,
        [{"codigo": "pct_sla_cumprido", "rotulo": "SLA cumprido (%)"}],
    )
    api_falsa.responder(
        "GET",
        "/metricas/mensal",
        200,
        [{"mes_ref": "2025-01-01", "valor": 80.0}, {"mes_ref": "2025-02-01", "valor": 75.5}],
    )

    at = _logado(ANALISE).run()

    assert not at.exception
    assert api_falsa.requisicoes[-1].url.params["variavel"] == "pct_sla_cumprido"
