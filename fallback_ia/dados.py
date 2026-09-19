"""
Carrega a base real do Desafio INOVAAPPS (INOVAAPPS_base_de_dados.xlsx) uma
vez, em memória, pro backend do fallback de IA. É a mesma planilha que
assistente-consultas/scripts/gerar_dados_inovaapps.py converte pro JSON que
o motor de métricas em JavaScript usa — aqui é a versão Python das mesmas
tabelas, pro backend poder executar as tools sem depender do bundle do
front nem duplicar a leitura da planilha em dois lugares incompatíveis.
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PLANILHA = RAIZ / "INOVAAPPS_base_de_dados.xlsx"

_wb = pd.read_excel(PLANILHA, sheet_name=None)

clientes = _wb["clientes"]
atendimento_mensal = _wb["atendimento_mensal"]
pesquisas_nps = _wb["pesquisas_nps"]
situacao_clientes = _wb["situacao_clientes"]

PLANOS = ["Essencial", "Avancado", "Enterprise"]
PORTES = ["Pequeno", "Medio", "Grande"]
SEGMENTOS = sorted(clientes["segmento"].unique().tolist())

PRIMEIRO_MES_DADOS = atendimento_mensal["mes_ref"].min()
ULTIMO_MES_DADOS = atendimento_mensal["mes_ref"].max()

_clientes_por_id = clientes.set_index("cliente_id")
_situacao_por_id = situacao_clientes.set_index("cliente_id")


def buscar_cliente(cliente_id):
    if cliente_id not in _clientes_por_id.index:
        return None
    return _clientes_por_id.loc[cliente_id].to_dict()


def buscar_situacao(cliente_id):
    if cliente_id not in _situacao_por_id.index:
        return None
    row = _situacao_por_id.loc[cliente_id].to_dict()
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
    return cliente_id in _clientes_por_id.index


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
