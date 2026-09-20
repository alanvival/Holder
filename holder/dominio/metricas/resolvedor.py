"""
O resolvedor genérico do catálogo: recebe um id de métrica e filtros, aplica
a definição declarativa e devolve o número.

É o que a tool `consultar_metrica` chama de verdade. O modelo de IA nunca
calcula nada — só escolhe a métrica e os filtros; quem soma e divide é
daqui para baixo.

Existe um irmão deste arquivo em JavaScript, de propósito, para o catálogo
responder no navegador sem backend no ar. Ver
`docs/adr/0003-resolvedor-de-metricas-duplicado-de-proposito.md`.
"""
from __future__ import annotations

from holder.infra.dados import carteira

from .definicoes import METRICAS, PLANO_LABELS, PORTE_LABELS


def aba_tem_periodo(aba: str) -> bool:
    return aba in ("atendimento_mensal", "pesquisas_nps")


def filtrar(aba: str, filtros: dict):
    df = carteira.aba(aba)

    cliente_id = filtros.get("cliente_id")
    plano = filtros.get("plano")
    porte = filtros.get("porte")
    segmento = filtros.get("segmento")
    situacao = filtros.get("situacao")
    inicio = filtros.get("periodo_inicio")
    fim = filtros.get("periodo_fim")

    if cliente_id:
        df = df[df["cliente_id"] == cliente_id]
    if plano:
        df = df[df["cliente_id"].map(carteira.plano_do_cliente) == plano]
    if porte:
        df = df[df["cliente_id"].map(carteira.porte_do_cliente) == porte]
    if segmento:
        df = df[df["cliente_id"].map(carteira.segmento_do_cliente) == segmento]
    if situacao:
        df = df[df["cliente_id"].map(carteira.situacao_do_cliente) == situacao]
    if aba_tem_periodo(aba):
        if inicio:
            df = df[df["mes_ref"] >= inicio]
        if fim:
            df = df[df["mes_ref"] <= fim]

    return df


def descrever_universo(aba: str, filtros: dict, df) -> str:
    n_clientes = df["cliente_id"].nunique() if "cliente_id" in df.columns else 0
    partes = [f"{n_clientes} cliente(s)"]
    if filtros.get("plano"):
        partes.append(f"plano {PLANO_LABELS.get(filtros['plano'], filtros['plano'])}")
    if filtros.get("porte"):
        partes.append(f"porte {PORTE_LABELS.get(filtros['porte'], filtros['porte'])}")
    if filtros.get("segmento"):
        partes.append(f"segmento {filtros['segmento']}")
    if filtros.get("situacao"):
        partes.append("ativos" if filtros["situacao"] == "Ativo" else "cancelados")
    if filtros.get("cliente_id"):
        partes.append(f"cliente {filtros['cliente_id']}")

    descricao = f"Considerando {', '.join(partes)}"
    if aba_tem_periodo(aba):
        inicio = filtros.get("periodo_inicio") or carteira.PRIMEIRO_MES_DADOS
        fim = filtros.get("periodo_fim") or carteira.ULTIMO_MES_DADOS
        descricao += f", de {inicio} a {fim}"
    return descricao + "."


def calcular_metrica(metrica_id: str, filtros: dict | None = None) -> dict:
    """
    Único ponto que sabe calcular qualquer métrica — é isso que a tool
    `consultar_metrica` chama. Retorna sempre um dict JSON-serializável com
    o valor bruto (nunca formatado como string livre — quem decide o texto
    final é o modelo, em cima deste número real) e o universo considerado.
    """
    filtros = filtros or {}
    definicao = METRICAS.get(metrica_id)
    if not definicao:
        return {"erro": f"Métrica desconhecida: {metrica_id}"}

    df = filtrar(definicao["aba"], filtros)
    if len(df) == 0:
        return {"erro": "Sem dados para essa combinação de filtros.", "universo": descrever_universo(definicao["aba"], filtros, df)}

    df_calculo = definicao["filtro_linha"](df) if "filtro_linha" in definicao else df

    valor = definicao["calcular"](df_calculo)
    if valor is None:
        return {"erro": "Sem amostra suficiente para essa métrica com esses filtros."}

    resultado = {
        "metrica": metrica_id,
        "rotulo": definicao["rotulo"],
        "formato": definicao["formato"],
        "universo": descrever_universo(definicao["aba"], filtros, df),
    }

    if metrica_id == "nps":
        resultado.update(valor)  # já é um dict {score, nota_media, respondidas, convites}
    else:
        escalado = valor * 100 if definicao.get("escala100") else valor
        resultado["valor"] = round(escalado, 4) if isinstance(escalado, float) else escalado

        if "leitura_alternativa" in definicao:
            alt = definicao["leitura_alternativa"]["calcular"](df_calculo)
            if alt is not None:
                alt_escalado = alt * 100 if definicao.get("escala100") else alt
                resultado["leitura_alternativa"] = {
                    "rotulo": definicao["leitura_alternativa"]["rotulo"],
                    "valor": round(alt_escalado, 4),
                }

    return resultado


# Categorias que dá pra comparar de uma vez (mesmo shape de plano/porte/
# segmento — os únicos valores de categoria fixos e enumeráveis da base).
# É função, e não constante de módulo, porque `segmento` é derivado da
# planilha: como constante, forçava a leitura do arquivo já no import.
def categorias_validas() -> dict:
    return {"plano": carteira.PLANOS, "porte": carteira.PORTES, "segmento": carteira.SEGMENTOS}


def comparar_metrica_por_categoria(metrica_id: str, categoria: str, filtros: dict | None = None) -> dict:
    """
    Calcula a mesma métrica pra CADA valor de uma categoria (plano, porte ou
    segmento) numa única chamada — pra perguntas tipo 'ticket médio por
    segmento' ou 'compare o SLA entre os planos'. Existe porque perguntas
    "por categoria" via encadeamento manual (listar categorias + chamar
    consultar_metrica uma vez por valor) estouravam MAX_TURNOS_TOOL — a
    tool faz o encadeamento internamente, sem gastar turno de conversa por
    valor de categoria.
    """
    categorias = categorias_validas()
    if categoria not in categorias:
        return {"erro": f"Categoria inválida: '{categoria}'. Use plano, porte ou segmento."}

    filtros = dict(filtros or {})
    filtros.pop("cliente_id", None)
    filtros.pop(categoria, None)  # a categoria é o que vai variar, não um filtro fixo

    if metrica_id not in METRICAS:
        return {"erro": f"Métrica desconhecida: {metrica_id}"}

    comparacao = []
    for valor_categoria in categorias[categoria]:
        resultado = calcular_metrica(metrica_id, {**filtros, categoria: valor_categoria})
        valor = resultado.get("valor", resultado.get("nota_media"))
        if valor is None:
            continue
        rotulo_categoria = (
            PLANO_LABELS.get(valor_categoria, valor_categoria) if categoria == "plano"
            else PORTE_LABELS.get(valor_categoria, valor_categoria) if categoria == "porte"
            else valor_categoria
        )
        comparacao.append({categoria: rotulo_categoria, "valor": valor})

    if not comparacao:
        return {"erro": "Sem amostra suficiente pra comparar essas categorias."}

    comparacao.sort(key=lambda c: c["valor"], reverse=True)
    return {
        "metrica": metrica_id,
        "rotulo": METRICAS[metrica_id]["rotulo"],
        "formato": METRICAS[metrica_id]["formato"],
        "categoria": categoria,
        "comparacao": comparacao,
        "tabela": {"colunas": [categoria, "valor"], "linhas": comparacao},
    }
