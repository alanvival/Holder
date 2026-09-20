"""
Carrega a base real do Desafio INOVAAPPS (INOVAAPPS_base_de_dados.xlsx) uma
vez, em memória, pro backend do fallback de IA. É a mesma planilha que
assistente-consultas/scripts/gerar_dados_inovaapps.py converte pro JSON que
o motor de métricas em JavaScript usa — aqui é a versão Python das mesmas
tabelas, pro backend poder executar as tools sem depender do bundle do
front nem duplicar a leitura da planilha em dois lugares incompatíveis.

A leitura acontece na primeira vez que alguém pede uma tabela, não no
import. Antes, importar este módulo — ou qualquer um que dependa dele:
metricas, tools_genericas, tools, ia_fallback — lia a planilha inteira,
o que tornava impossível carregar o domínio sem tocar em disco. O cache
mantém a garantia de antes: a planilha é lida uma única vez por processo, e
as tabelas devolvidas são sempre os mesmos objetos.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PLANILHA = RAIZ / "INOVAAPPS_base_de_dados.xlsx"

# Valores fixos do contrato, não derivados da planilha — ficam acessíveis
# sem provocar leitura de disco.
PLANOS = ["Essencial", "Avancado", "Enterprise"]
PORTES = ["Pequeno", "Medio", "Grande"]

ABAS = ("clientes", "atendimento_mensal", "pesquisas_nps", "situacao_clientes")


@lru_cache(maxsize=1)
def carregar() -> dict:
    """Lê a planilha uma vez por processo e devolve tudo que o resto do
    pacote consome. Chamadas seguintes devolvem exatamente os mesmos
    objetos, sem reler nada."""
    wb = pd.read_excel(PLANILHA, sheet_name=None)

    clientes = wb["clientes"]
    atendimento_mensal = wb["atendimento_mensal"]
    pesquisas_nps = wb["pesquisas_nps"]
    situacao_clientes = wb["situacao_clientes"]

    return {
        "clientes": clientes,
        "atendimento_mensal": atendimento_mensal,
        "pesquisas_nps": pesquisas_nps,
        "situacao_clientes": situacao_clientes,
        "SEGMENTOS": sorted(clientes["segmento"].unique().tolist()),
        "PRIMEIRO_MES_DADOS": atendimento_mensal["mes_ref"].min(),
        "ULTIMO_MES_DADOS": atendimento_mensal["mes_ref"].max(),
        "_clientes_por_id": clientes.set_index("cliente_id"),
        "_situacao_por_id": situacao_clientes.set_index("cliente_id"),
    }


def aba(nome: str):
    """Uma das quatro tabelas da planilha, por nome."""
    if nome not in ABAS:
        raise KeyError(f"Aba desconhecida: {nome!r}. Disponíveis: {', '.join(ABAS)}")
    return carregar()[nome]


def __getattr__(nome):
    """PEP 562: mantém `dados.clientes`, `dados.SEGMENTOS`,
    `dados.ULTIMO_MES_DADOS` etc. funcionando como atributo de módulo, agora
    resolvendo sob demanda. É o que permitiu tornar a carga preguiçosa sem
    mexer nos ~20 pontos de uso espalhados por metricas.py e
    tools_genericas.py."""
    carregado = carregar()
    if nome in carregado:
        return carregado[nome]
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")


def buscar_cliente(cliente_id):
    por_id = carregar()["_clientes_por_id"]
    if cliente_id not in por_id.index:
        return None
    return por_id.loc[cliente_id].to_dict()


def buscar_situacao(cliente_id):
    por_id = carregar()["_situacao_por_id"]
    if cliente_id not in por_id.index:
        return None
    row = por_id.loc[cliente_id].to_dict()
    row["cliente_id"] = cliente_id
    return row


def plano_do_cliente(cliente_id):
    c = buscar_cliente(cliente_id)
    return c["plano"] if c else None


def porte_do_cliente(cliente_id):
    c = buscar_cliente(cliente_id)
    return c["porte"] if c else None


def segmento_do_cliente(cliente_id):
    c = buscar_cliente(cliente_id)
    return c["segmento"] if c else None


def situacao_do_cliente(cliente_id):
    s = buscar_situacao(cliente_id)
    return s["situacao"] if s else None


def cliente_existe(cliente_id):
    return cliente_id in carregar()["_clientes_por_id"].index


def normalizar_cliente_id(cliente_id):
    """A IA (ou o usuário, na hora de digitar pra IA) às vezes troca "0" por
    letra "O" no id (ex: 'CO02' em vez de 'C002') — normaliza pra aceitar
    esse erro de digitação comum em vez de simplesmente não achar o cliente."""
    if not cliente_id or not isinstance(cliente_id, str):
        return cliente_id
    cid = cliente_id.strip().upper()
    if cid.startswith("C") and len(cid) > 1:
        cid = "C" + cid[1:].replace("O", "0")
    return cid
