"""
Allowlist central de campos consultáveis — fonte única da verdade de todo
campo que qualquer tool genérica pode ler. Nenhuma tool referencia nome de
coluna do pandas diretamente: sempre passa pelo "campo lógico" daqui, que
resolve pra (aba, coluna, tipo, e_serie_temporal).

Isso existe pra parar de crescer uma tool nova pra cada pergunta nova — em
vez disso, as tools genéricas (tools_genericas.py) recebem "campo" como
parâmetro e validam contra este dicionário antes de montar qualquer filtro.
Campo fora da lista nunca vira acesso direto a coluna nem erro cru — vira um
dict de erro com sugestão dos campos mais parecidos (ver `resolver_campo`).
"""
from __future__ import annotations

import difflib

# campo_logico: (aba, coluna, tipo, e_serie_temporal)
CAMPOS_PERMITIDOS: dict[str, tuple[str, str, str, bool]] = {
    "cliente_id": ("clientes", "cliente_id", "texto", False),
    "segmento": ("clientes", "segmento", "texto", False),
    "porte": ("clientes", "porte", "texto", False),
    "plano": ("clientes", "plano", "texto", False),
    "valor_mensal": ("clientes", "valor_mensal", "numero", False),
    "sla_contratado_h": ("clientes", "sla_contratado_h", "numero", False),
    "inicio_contrato": ("clientes", "inicio_contrato", "data", False),
    "situacao": ("situacao_clientes", "situacao", "texto", False),
    "mes_cancelamento": ("situacao_clientes", "mes_cancelamento", "texto", False),
    "chamados_abertos": ("atendimento_mensal", "chamados_abertos", "numero", True),
    "chamados_criticos": ("atendimento_mensal", "chamados_criticos", "numero", True),
    "chamados_reabertos": ("atendimento_mensal", "chamados_reabertos", "numero", True),
    "pct_sla_cumprido": ("atendimento_mensal", "pct_sla_cumprido", "numero", True),
    "tempo_medio_resolucao_h": ("atendimento_mensal", "tempo_medio_resolucao_h", "numero", True),
    "reclamacoes_formais": ("atendimento_mensal", "reclamacoes_formais", "numero", True),
    "uso_plataforma_pct": ("atendimento_mensal", "uso_plataforma_pct", "numero", True),
    "dias_atraso_pagamento": ("atendimento_mensal", "dias_atraso_pagamento", "numero", True),
    "reunioes_realizadas": ("atendimento_mensal", "reunioes_realizadas", "numero", True),
    "reunioes_previstas": ("atendimento_mensal", "reunioes_previstas", "numero", True),
    "nota_nps": ("pesquisas_nps", "nota_nps", "numero", True),
    "classificacao_nps": ("pesquisas_nps", "classificacao_nps", "texto", True),
}


def resolver_campo(nome: str):
    """Retorna a tupla (aba, coluna, tipo, e_serie_temporal) do allowlist, ou
    None se o campo não existe — nunca deixa a tool seguir com um nome de
    coluna não validado."""
    return CAMPOS_PERMITIDOS.get(nome)


def erro_campo_invalido(nome) -> dict:
    # `nome` pode vir None: o modelo de IA às vezes omite um parâmetro
    # obrigatório do schema. Sem esta guarda, o difflib recebia None e
    # levantava TypeError, derrubando a execução da tool em vez de devolver
    # o erro estruturado que o fluxo sabe tratar.
    sugestoes = (
        difflib.get_close_matches(nome, CAMPOS_PERMITIDOS.keys(), n=3, cutoff=0.4)
        if isinstance(nome, str) else []
    )
    return {
        "erro": f"Campo desconhecido: {nome!r}." if nome else "Nenhum campo informado.",
        "campos_validos": sorted(CAMPOS_PERMITIDOS.keys()),
        "sugestoes": sugestoes,
    }
