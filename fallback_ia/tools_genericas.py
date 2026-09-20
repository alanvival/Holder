"""
As cinco tools genéricas e parametrizáveis que substituem a família de tools
estreitas (uma por pergunta) que crescia sem parar. Nenhuma delas conhece
nome de coluna do pandas diretamente — todas resolvem campo via
`campos.CAMPOS_PERMITIDOS` antes de tocar em qualquer dataframe. Nunca
eval/exec/montagem de query a partir de texto do usuário: o valor recebido é
sempre comparado como dado, nunca executado.

`consultar_metrica` continua em metricas.py (métricas agregadas com fórmula
própria — ticket médio, SLA, NPS, churn etc. — não são "um campo", são um
cálculo sobre vários); as outras tools que só faziam "filtrar campo(s) do
allowlist" (ranking_clientes, contar_clientes, evolucao_metrica,
comparar_por_categoria, o listar_clientes antigo, buscar_registro_cliente)
foram substituídas pelas quatro funções abaixo.
"""
from __future__ import annotations

import datetime as dt

from . import dados
from .campos import CAMPOS_PERMITIDOS, erro_campo_invalido, resolver_campo

_LIMITE_PADRAO = 20
_LIMITE_MAXIMO = 100


# --- Leitura de valor por cliente, resolvendo campo -> dado real -----------

def _valor_estatico(cliente_id: str, aba: str, coluna: str):
    if aba == "clientes":
        c = dados.buscar_cliente(cliente_id)
        return c.get(coluna) if c else None
    if aba == "situacao_clientes":
        s = dados.buscar_situacao(cliente_id)
        return s.get(coluna) if s else None
    return None


def _linha_temporal_mais_recente(cliente_id: str, aba: str, periodo_inicio: str | None, periodo_fim: str | None):
    """Linha mais recente (por mes_ref) dentro do período pedido — se nenhum
    período foi dado, a mais recente disponível no histórico inteiro (regra
    3 do prompt: campo de série temporal sem período usa o mês mais recente
    disponível). Em pesquisas_nps, só conta pesquisa respondida."""
    df = dados.aba(aba)
    sub = df[df["cliente_id"] == cliente_id]
    if periodo_inicio:
        sub = sub[sub["mes_ref"] >= periodo_inicio]
    if periodo_fim:
        sub = sub[sub["mes_ref"] <= periodo_fim]
    if aba == "pesquisas_nps":
        sub = sub[sub["respondeu"] == 1]
    if len(sub) == 0:
        return None
    return sub.sort_values("mes_ref").iloc[-1]


def valor_campo_cliente(cliente_id: str, campo_info, periodo_inicio: str | None = None, periodo_fim: str | None = None):
    """Devolve (valor, mes_ref_usado). mes_ref_usado é None pra campo
    estático (não faz sentido "declarar o mês" de um valor_mensal, por
    exemplo) e o mês real usado quando o campo é série temporal."""
    aba, coluna, _tipo, temporal = campo_info
    if not temporal:
        return _valor_estatico(cliente_id, aba, coluna), None
    linha = _linha_temporal_mais_recente(cliente_id, aba, periodo_inicio, periodo_fim)
    if linha is None:
        return None, None
    valor = linha[coluna]
    if valor != valor:  # NaN
        return None, linha["mes_ref"]
    return valor, linha["mes_ref"]


# --- Operadores dos filtros --------------------------------------------

def _aplica_operador(valor, operador: str, alvo, alvo2=None, tipo: str = "texto") -> bool:
    if valor is None:
        return False
    if tipo == "numero":
        try:
            valor_cmp = float(valor)
            alvo_cmp = float(alvo)
            alvo2_cmp = float(alvo2) if alvo2 is not None else None
        except (TypeError, ValueError):
            return False
    else:
        valor_cmp, alvo_cmp, alvo2_cmp = str(valor), str(alvo), (str(alvo2) if alvo2 is not None else None)

    if operador == "igual":
        return valor_cmp == alvo_cmp
    if operador == "diferente":
        return valor_cmp != alvo_cmp
    if operador == "maior_que":
        return valor_cmp > alvo_cmp
    if operador == "menor_que":
        return valor_cmp < alvo_cmp
    if operador == "contem":
        return str(alvo).lower() in str(valor).lower()
    if operador == "entre":
        return alvo2_cmp is not None and alvo_cmp <= valor_cmp <= alvo2_cmp
    return False


def _formatar_valor(valor):
    if valor is None:
        return None
    if hasattr(valor, "item"):  # numpy scalar -> tipo nativo, JSON-serializável
        valor = valor.item()
    return valor


# --- Tool 1: listar_clientes (busca + ranking + contagem + agrupamento) ---

def listar_clientes(
    filtros: list[dict] | None = None,
    ordenar_por: str | None = None,
    direcao: str = "desc",
    periodo_inicio: str | None = None,
    periodo_fim: str | None = None,
    limite: int = _LIMITE_PADRAO,
    retornar: str = "lista",
    agrupar_por: str | None = None,
) -> dict:
    filtros = filtros or []
    infos_filtro = []
    for f in filtros:
        info = resolver_campo(f.get("campo"))
        if not info:
            return erro_campo_invalido(f.get("campo"))
        infos_filtro.append((info, f))

    if ordenar_por and not resolver_campo(ordenar_por):
        return erro_campo_invalido(ordenar_por)
    if retornar == "agrupado":
        if not agrupar_por or not resolver_campo(agrupar_por):
            return erro_campo_invalido(agrupar_por or "")

    candidatos = dados.clientes["cliente_id"].tolist()
    meses_usados: set[str] = set()
    encontrados = []
    for cliente_id in candidatos:
        bate = True
        for info, f in infos_filtro:
            valor, mes = valor_campo_cliente(cliente_id, info, periodo_inicio, periodo_fim)
            if mes:
                meses_usados.add(mes)
            if not _aplica_operador(valor, f["operador"], f["valor"], f.get("valor2"), tipo=info[2]):
                bate = False
                break
        if bate:
            encontrados.append(cliente_id)

    total = len(encontrados)
    periodo_declarado = None
    if not periodo_inicio and not periodo_fim and meses_usados:
        periodo_declarado = f"mês mais recente disponível por cliente (até {max(meses_usados)})"

    if retornar == "contagem":
        return {"total": total, "filtros_aplicados": len(infos_filtro), "periodo_usado": periodo_declarado}

    if retornar == "agrupado":
        info = resolver_campo(agrupar_por)
        contagens: dict = {}
        for cliente_id in encontrados:
            valor, _mes = valor_campo_cliente(cliente_id, info, periodo_inicio, periodo_fim)
            chave = _formatar_valor(valor) if valor is not None else "Sem dado"
            contagens[chave] = contagens.get(chave, 0) + 1
        grupos = sorted(
            [{"valor": k, "total": v} for k, v in contagens.items()],
            key=lambda g: g["total"], reverse=True,
        )
        return {
            "total_encontrado": total,
            "agrupado_por": agrupar_por,
            "grupos": grupos,
            "tabela": {"colunas": [agrupar_por, "total"], "linhas": [{agrupar_por: g["valor"], "total": g["total"]} for g in grupos]},
        }

    # retornar == "lista" (cobre também ranking, quando ordenar_por é dado)
    coluna_extra = ordenar_por
    if coluna_extra:
        info = resolver_campo(coluna_extra)
        pares = []
        for cliente_id in encontrados:
            valor, _mes = valor_campo_cliente(cliente_id, info, periodo_inicio, periodo_fim)
            if valor is not None:
                pares.append((cliente_id, valor))
        pares.sort(key=lambda p: p[1], reverse=(direcao != "asc"))
        ids_ordenados = [p[0] for p in pares]
    else:
        ids_ordenados = sorted(encontrados)

    limite = max(1, min(limite or _LIMITE_PADRAO, _LIMITE_MAXIMO))
    pagina = ids_ordenados[:limite]

    colunas = ["cliente_id"] + ([coluna_extra] if coluna_extra else [])
    linhas_tabela = []
    for cliente_id in pagina:
        linha = {"cliente_id": cliente_id}
        if coluna_extra:
            valor, _mes = valor_campo_cliente(cliente_id, resolver_campo(coluna_extra), periodo_inicio, periodo_fim)
            linha[coluna_extra] = _formatar_valor(valor)
        linhas_tabela.append(linha)

    return {
        "total_encontrado": total,
        "clientes": pagina,
        "tabela": {"colunas": colunas, "linhas": linhas_tabela},
        "truncado": total > limite,
        "periodo_usado": periodo_declarado,
    }


# --- Tool 2: buscar_campo_cliente ------------------------------------------

def buscar_campo_cliente(cliente_id: str, campos: list[str], periodo_inicio: str | None = None, periodo_fim: str | None = None) -> dict:
    cliente_id = dados.normalizar_cliente_id(cliente_id)
    if not dados.cliente_existe(cliente_id):
        return {"erro": f"Cliente {cliente_id} não encontrado na base."}

    resultado: dict = {"cliente_id": cliente_id}
    meses_usados = {}
    for campo in campos:
        info = resolver_campo(campo)
        if not info:
            return erro_campo_invalido(campo)
        valor, mes = valor_campo_cliente(cliente_id, info, periodo_inicio, periodo_fim)
        resultado[campo] = _formatar_valor(valor)
        if mes:
            meses_usados[campo] = mes

    if meses_usados and not periodo_inicio and not periodo_fim:
        resultado["periodo_usado"] = "mês mais recente disponível: " + ", ".join(f"{c}={m}" for c, m in meses_usados.items())
    return resultado


# --- Tool 3: comparar_clientes ----------------------------------------------

def _coletar_campos(cliente_id: str, campos: list[str], periodo_inicio: str | None, periodo_fim: str | None) -> dict:
    linha = {"cliente_id": cliente_id}
    for campo in campos:
        info = resolver_campo(campo)
        valor, _mes = valor_campo_cliente(cliente_id, info, periodo_inicio, periodo_fim)
        linha[campo] = _formatar_valor(valor)
    return linha


def comparar_clientes(
    cliente_ids: list[str],
    campos: list[str],
    periodo_inicio: str | None = None,
    periodo_fim: str | None = None,
    periodo_comparacao: dict | None = None,
) -> dict:
    for campo in campos:
        if not resolver_campo(campo):
            return erro_campo_invalido(campo)

    cliente_ids = [dados.normalizar_cliente_id(c) for c in cliente_ids]
    inexistentes = [c for c in cliente_ids if not dados.cliente_existe(c)]
    if inexistentes:
        return {"erro": f"Cliente(s) não encontrado(s) na base: {', '.join(inexistentes)}."}

    if periodo_comparacao:
        linhas = []
        for cliente_id in cliente_ids:
            principal = _coletar_campos(cliente_id, campos, periodo_inicio, periodo_fim)
            comparado = _coletar_campos(cliente_id, campos, periodo_comparacao.get("periodo_inicio"), periodo_comparacao.get("periodo_fim"))
            linhas.append({
                "cliente_id": cliente_id,
                "periodo_principal": {"inicio": periodo_inicio, "fim": periodo_fim, **{k: v for k, v in principal.items() if k != "cliente_id"}},
                "periodo_comparacao": {
                    "inicio": periodo_comparacao.get("periodo_inicio"),
                    "fim": periodo_comparacao.get("periodo_fim"),
                    **{k: v for k, v in comparado.items() if k != "cliente_id"},
                },
            })
        colunas = ["cliente_id"] + [f"{c} (período principal)" for c in campos] + [f"{c} (período de comparação)" for c in campos]
        linhas_tabela = [
            {
                "cliente_id": l["cliente_id"],
                **{f"{c} (período principal)": l["periodo_principal"][c] for c in campos},
                **{f"{c} (período de comparação)": l["periodo_comparacao"][c] for c in campos},
            }
            for l in linhas
        ]
        return {
            "modo": "entre_periodos",
            "clientes": linhas,
            "tabela": {"colunas": colunas, "linhas": linhas_tabela},
        }

    linhas = [_coletar_campos(cliente_id, campos, periodo_inicio, periodo_fim) for cliente_id in cliente_ids]
    return {
        "modo": "entre_clientes",
        "clientes": linhas,
        "tabela": {"colunas": ["cliente_id"] + campos, "linhas": linhas},
    }


# --- Tool 4: evolucao_temporal ----------------------------------------------

def evolucao_temporal(
    campo: str,
    cliente_id: str | None = None,
    filtros: list[dict] | None = None,
    periodo_inicio: str | None = None,
    periodo_fim: str | None = None,
) -> dict:
    info = resolver_campo(campo)
    if not info:
        return erro_campo_invalido(campo)
    aba, coluna, tipo, temporal = info
    if not temporal:
        return {"erro": f"Campo '{campo}' não é uma série temporal — não tem evolução mês a mês."}
    if tipo != "numero" and campo != "classificacao_nps":
        return {"erro": f"Campo '{campo}' não é numérico — não dá pra ver evolução como série de valores."}

    df = dados.aba(aba)

    if cliente_id:
        cliente_id = dados.normalizar_cliente_id(cliente_id)
        if not dados.cliente_existe(cliente_id):
            return {"erro": f"Cliente {cliente_id} não encontrado na base."}
        sub = df[df["cliente_id"] == cliente_id]
        descricao_universo = f"Cliente {cliente_id}."
    else:
        candidatos = set(dados.clientes["cliente_id"])
        for f in (filtros or []):
            f_info = resolver_campo(f.get("campo"))
            if not f_info:
                return erro_campo_invalido(f.get("campo"))
            candidatos = {
                cid for cid in candidatos
                if _aplica_operador(valor_campo_cliente(cid, f_info, periodo_inicio, periodo_fim)[0], f["operador"], f["valor"], f.get("valor2"), tipo=f_info[2])
            }
        sub = df[df["cliente_id"].isin(candidatos)]
        descricao_universo = f"Agregado sobre {len(candidatos)} cliente(s) que batem com os filtros."

    if aba == "pesquisas_nps":
        sub = sub[sub["respondeu"] == 1]
    if periodo_inicio:
        sub = sub[sub["mes_ref"] >= periodo_inicio]
    if periodo_fim:
        sub = sub[sub["mes_ref"] <= periodo_fim]

    if len(sub) == 0:
        return {"erro": "Sem dados para essa combinação de filtros/período.", "universo": descricao_universo}

    if campo == "classificacao_nps":
        serie = []
        for mes_ref, grupo in sub.groupby("mes_ref"):
            contagens = grupo["classificacao_nps"].value_counts().to_dict()
            serie.append({"mes_ref": mes_ref, **contagens})
    else:
        serie = []
        for mes_ref, grupo in sub.groupby("mes_ref"):
            valores = grupo[coluna].dropna()
            if len(valores) == 0:
                continue
            serie.append({"mes_ref": mes_ref, "valor": round(float(valores.mean()), 4)})

    serie.sort(key=lambda s: s["mes_ref"])
    if not serie:
        return {"erro": "Sem amostra suficiente pra montar a série.", "universo": descricao_universo}

    # Só "tabela" (não também "serie" com os mesmos dados) — payload menor
    # pro modelo processar: uma série de vários meses duplicada em dois
    # formatos foi a causa observada de timeout com o gpt-oss (reasoning
    # model gasta mais tempo "pensando" sobre payloads maiores).
    return {
        "campo": campo,
        "universo": descricao_universo,
        "tabela": {"colunas": list(serie[0].keys()), "linhas": serie},
    }
