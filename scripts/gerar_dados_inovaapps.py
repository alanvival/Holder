"""
Converte INOVAAPPS_base_de_dados.xlsx em JSON estático consumido pelo
Assistente de Consultas (interface-web/src/data/inovaapps/*.json).

Roda uma vez (ou sempre que a planilha for atualizada); o app não faz
parsing de xlsx em runtime — os JSONs commitados são a fonte de dados.

Uso: python scripts/gerar_dados_inovaapps.py
"""
import json
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parent.parent
PLANILHA = RAIZ / "INOVAAPPS_base_de_dados.xlsx"
DESTINO = RAIZ / "interface-web" / "src" / "data" / "inovaapps"


def linhas_como_dicts(ws):
    linhas = list(ws.iter_rows(values_only=True))
    cabecalho = linhas[0]
    resultado = []
    for linha in linhas[1:]:
        item = {}
        for chave, valor in zip(cabecalho, linha):
            item[chave] = valor
        resultado.append(item)
    return resultado


def escrever_json(nome, dados):
    DESTINO.mkdir(parents=True, exist_ok=True)
    caminho = DESTINO / f"{nome}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"{nome}: {len(dados)} linhas -> {caminho.relative_to(RAIZ)}")


def main():
    wb = openpyxl.load_workbook(PLANILHA, data_only=True)
    escrever_json("clientes", linhas_como_dicts(wb["clientes"]))
    escrever_json("atendimentoMensal", linhas_como_dicts(wb["atendimento_mensal"]))
    escrever_json("pesquisasNps", linhas_como_dicts(wb["pesquisas_nps"]))
    escrever_json("situacaoClientes", linhas_como_dicts(wb["situacao_clientes"]))


if __name__ == "__main__":
    main()
