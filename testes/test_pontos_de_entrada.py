"""
Prende os pontos de entrada: eles precisam **executar**, não só importar.

Este arquivo existe por causa de um erro de verificação concreto. O dashboard
ficou quebrado com `ImportError: attempted relative import with no known
parent package` e passou por todas as checagens que eu fazia, porque eu
conferia `HTTP 200` na porta 8501 — e o Streamlit devolve 200 para o shell da
aplicação **mesmo quando o script falha**, renderizando a exceção dentro da
página, no navegador. Checar o código HTTP não testava nada do script.

A causa raiz: `streamlit run arquivo.py` executa o arquivo como script
(`__name__ == "__main__"`, sem pacote), então `from . import x` não resolve.
Já `python -m holder.interfaces.api` tem contexto de pacote e por isso o
import relativo funciona lá.
"""
import ast
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA_DASHBOARD = RAIZ / "holder" / "interfaces" / "dashboard" / "app.py"


def test_entrada_do_dashboard_nao_usa_import_relativo():
    """Rápido, não precisa de infra: o ponto de entrada do Streamlit não pode
    ter import relativo. Os outros módulos do dashboard podem — eles são
    importados como parte do pacote."""
    arvore = ast.parse(ENTRADA_DASHBOARD.read_text(encoding="utf-8"))
    relativos = [
        no for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom) and (no.level or 0) > 0
    ]
    assert not relativos, (
        f"{ENTRADA_DASHBOARD.name} tem import relativo na linha(s) "
        f"{[no.lineno for no in relativos]}. O `streamlit run` executa este "
        "arquivo como script, sem pacote — use import absoluto "
        "(`from holder.interfaces.dashboard import ...`)."
    )


@pytest.mark.sqlserver
@pytest.mark.lento
def test_dashboard_executa_do_inicio_ao_fim():
    """Executa o arquivo exatamente como o `streamlit run` executa — como
    `__main__`, sem pacote — num subprocesso limpo. Fora de uma sessão do
    Streamlit os comandos rodam em "bare mode": não sobem servidor, mas
    percorrem o script inteiro, incluindo as três abas. Qualquer exceção
    derruba o exit code.

    É o único teste que prova que o dashboard roda; os demais provam que as
    partes dele calculam certo."""
    resultado = subprocess.run(
        [sys.executable, "-c",
         "import runpy; runpy.run_path(r'holder/interfaces/dashboard/app.py', run_name='__main__')"],
        cwd=RAIZ, capture_output=True, text=True,
    )
    assert resultado.returncode == 0, (
        f"o dashboard não executou até o fim:\n"
        f"--- stdout ---\n{resultado.stdout[-2000:]}\n"
        f"--- stderr ---\n{resultado.stderr[-2000:]}"
    )


def test_a_api_expoe_as_rotas_esperadas():
    """A API é `python -m holder.interfaces.api`, que tem contexto de pacote —
    o problema do dashboard não se aplica. O que vale conferir aqui é que as
    rotas continuam registradas depois das mudanças de estrutura."""
    from holder.interfaces.api.servidor import app

    rotas = {str(regra.rule) for regra in app.url_map.iter_rules()}
    esperadas = {
        "/api/fallback-ia", "/api/historico", "/api/health", "/api/perguntas",
        "/api/perguntas/<pergunta_id>", "/api/sugestoes",
        "/api/sugestoes/<sugestao_id>/sugerir-resposta",
        "/api/sugestoes/<sugestao_id>/aprovar",
        "/api/sugestoes/<sugestao_id>/rejeitar",
    }
    faltando = esperadas - rotas
    assert not faltando, f"rotas que desapareceram da API: {sorted(faltando)}"


def test_o_dashboard_executa_sem_a_raiz_no_sys_path():
    """O teste acima roda o script com `python -c` e `cwd=RAIZ`, e o `-c`
    coloca o diretório atual no `sys.path`. O `streamlit run` **não** faz
    isso: o `_fix_sys_path` do Streamlit insere só
    `os.path.dirname(main_script_path)` — o diretório do próprio arquivo.

    Resultado: `from holder.dominio...` resolvia em todo teste e em todo
    `python -m streamlit` local, e quebrava com ModuleNotFoundError no
    `streamlit run` puro — que é como o Streamlit Cloud sobe o app.

    Este teste reproduz o ambiente real: `-P` impede o Python de prepender o
    diretório atual, e só o diretório do script entra no caminho, igual ao
    Streamlit."""
    import os

    codigo = (
        "import sys, runpy;"
        f"sys.path.insert(0, r'{ENTRADA_DASHBOARD.parent}');"
        f"runpy.run_path(r'{ENTRADA_DASHBOARD}', run_name='__main__')"
    )
    resultado = subprocess.run(
        [sys.executable, "-P", "-c", codigo],
        cwd=RAIZ, capture_output=True, text=True,
        env={**os.environ, "HOLDER_BANCO": "sqlite"},
    )
    assert resultado.returncode == 0, (
        "o dashboard não executa como o `streamlit run` o executa:\n"
        f"--- stderr ---\n{resultado.stderr[-2000:]}"
    )
