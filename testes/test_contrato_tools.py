"""
Contrato dos nomes de tool.

O nome de uma tool aparece em quatro lugares e **nenhuma linguagem checa**
que eles concordam: no schema exposto ao modelo de IA, no despachante que a
executa, dentro do texto de outras descrições (quando uma tool recomenda
outra como reserva) e nas chaves de follow-up do front.

Este arquivo existe porque a renomeação da fase 8 deixou duas dessas quatro
desatualizadas, e as duas falhavam em silêncio:

- a descrição de `listar_previsao_risco` mandava o modelo usar
  `prever_risco_cancelamento` quando o banco estivesse fora do ar — uma tool
  que havia deixado de existir. O modelo emitiria o nome antigo e receberia
  "Tool desconhecida" em vez da resposta de reserva.
- o `followUpQuestions.js` é indexado por nome de tool; as chaves antigas
  viraram letra morta e aquelas duas tools passaram a cair no follow-up
  genérico, sem erro nenhum na tela.
"""
import re
from pathlib import Path

import pytest

from holder.aplicacao.assistente.tools import TOOLS, executar_tool

RAIZ = Path(__file__).resolve().parent.parent
FOLLOW_UPS_JS = RAIZ / "interface-web" / "src" / "data" / "followUpQuestions.js"

NOMES = {t["name"] for t in TOOLS}

# Intents que resolvem SEM passar pela IA (atalho determinístico no front —
# ver interface-web/src/engine/riscoDireto.js) e por isso não têm tool
# correspondente no schema, mas são `intentId` válidos e legítimos pra
# indexar follow-up. Listados explicitamente pra que o teste continue
# pegando chave digitada errada, que é o bug que ele existe pra evitar.
INTENTS_SEM_IA = {"risco_direto"}


def test_ha_tools_registradas():
    assert len(NOMES) == len(TOOLS), "nome de tool duplicado no schema"
    assert len(NOMES) >= 10


@pytest.mark.parametrize("tool", TOOLS, ids=[t["name"] for t in TOOLS])
def test_toda_tool_do_schema_e_executavel(tool):
    """O despachante precisa conhecer todo nome que o schema anuncia. Uma
    tool anunciada e não despachada devolve "Tool desconhecida" só quando o
    modelo a escolhe — em produção, na frente de quem estiver olhando."""
    resultado = executar_tool(tool["name"], {})
    assert not (
        isinstance(resultado, dict)
        and str(resultado.get("erro", "")).startswith("Tool desconhecida")
    ), f"'{tool['name']}' está no schema mas o despachante não a conhece"


def test_toda_tool_citada_numa_descricao_existe():
    """Descrições recomendam tools umas às outras ('se isto falhar, use
    aquela'). Um nome morto aí faz o modelo emitir uma chamada inválida."""
    mortos = {}
    for tool in TOOLS:
        descricao = tool["description"]
        # Candidatos: palavras em snake_case com jeito de nome de tool.
        citados = set(re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,4}\b", descricao))
        for citado in citados:
            if citado in NOMES:
                continue
            # Só reclama de algo que PARECE nome de tool: verbo de ação no
            # começo. Sem isso, qualquer campo snake_case citado no texto
            # (cliente_id, taxa_disparo_por_sinal) daria falso positivo.
            if citado.split("_")[0] in ("listar", "detalhar", "prever", "consultar",
                                        "analisar", "buscar", "comparar", "avaliar",
                                        "clientes", "evolucao"):
                mortos.setdefault(tool["name"], []).append(citado)

    assert not mortos, (
        "descrição de tool cita nome(s) de tool que não existem mais: "
        f"{mortos}. Tools reais: {sorted(NOMES)}"
    )


def test_chaves_de_follow_up_do_front_sao_tools_reais():
    """O front mostra sugestões de "continuar a conversa" indexadas por nome
    de tool. Chave que não casa com tool nenhuma não dá erro — só deixa de
    aparecer."""
    js = FOLLOW_UPS_JS.read_text(encoding="utf-8")
    bloco = js[js.index("FOLLOW_UPS_POR_TOOL = {"):js.index("const FOLLOW_UPS_GENERICO_IA")]
    chaves = set(re.findall(r"^\s{2}([a-z_][a-z0-9_]*):\s*\[", bloco, re.MULTILINE))

    assert chaves, "não consegui extrair as chaves de FOLLOW_UPS_POR_TOOL"
    orfas = chaves - NOMES - INTENTS_SEM_IA
    assert not orfas, (
        f"chaves de follow-up que não são tools nem intents determinísticos: "
        f"{sorted(orfas)}. Tools reais: {sorted(NOMES)}. "
        f"Intents sem IA: {sorted(INTENTS_SEM_IA)}"
    )
