"""
Prende a identidade visual: `docs/design-tokens.md` é a fonte da verdade dos
tokens, e cada cópia deles no projeto tem de concordar com ela.

Existem quatro cópias, por motivos diferentes e legítimos:
1. `assistente-consultas/src/styles/tokens.css` — o que as telas consomem;
2. o bloco `[theme]` de `.streamlit/config.toml` — porque `st.dataframe`
   renderiza a grade em canvas, onde CSS de página não alcança;
3. `assistente-consultas/src/utils/exportarPdf.js` — em RGB, porque o jsPDF
   não lê CSS custom properties;
4. as cores de faixa em `app.py` — que hoje **não existem** no
   `design-tokens.md`; entram na fase 8 (cores semânticas) e passam a ser
   conferidas aqui.

A decisão de manter cópias conferidas por teste, em vez de gerar os arquivos
por script, está registrada: os tokens nunca divergiram de fato, então
maquinário de geração resolveria um problema que este repo não tem.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "docs" / "design-tokens.md"
TOKENS_CSS = RAIZ / "assistente-consultas" / "src" / "styles" / "tokens.css"
CONFIG_STREAMLIT = RAIZ / ".streamlit" / "config.toml"
EXPORTAR_PDF = RAIZ / "assistente-consultas" / "src" / "utils" / "exportarPdf.js"

_DECLARACAO = re.compile(r"--(gs-[\w-]+)\s*:\s*([^;]+);")


def _declaracoes(caminho: Path) -> dict[str, str]:
    """Extrai `--gs-nome: valor;` de um arquivo, normalizando espaço em
    branco — o gradiente de marca está em uma linha no .md e quebrado em
    várias no .css, e isso não é divergência."""
    texto = caminho.read_text(encoding="utf-8")
    return {
        nome: re.sub(r"\s+", "", valor).lower()
        for nome, valor in _DECLARACAO.findall(texto)
    }


FONTE_TOKENS = _declaracoes(FONTE)


def test_fonte_da_verdade_tem_os_tokens_esperados():
    """Se esta asserção falhar, o `design-tokens.md` mudou de formato e o
    resto deste arquivo está conferindo menos do que parece."""
    assert len(FONTE_TOKENS) >= 15, (
        f"esperava ao menos 15 tokens em {FONTE.name}, encontrei {len(FONTE_TOKENS)}"
    )
    for obrigatorio in ("gs-blue-accent", "gs-text", "gs-gradient-brand", "gs-font-heading"):
        assert obrigatorio in FONTE_TOKENS, f"token '{obrigatorio}' desapareceu da fonte"


@pytest.mark.parametrize("token", sorted(FONTE_TOKENS))
def test_tokens_css_concorda_com_a_fonte(token):
    declarados = _declaracoes(TOKENS_CSS)
    assert token in declarados, f"'--{token}' existe no design-tokens.md e falta em tokens.css"
    assert declarados[token] == FONTE_TOKENS[token], (
        f"'--{token}': tokens.css tem {declarados[token]}, "
        f"design-tokens.md tem {FONTE_TOKENS[token]}"
    )


def test_tema_do_streamlit_concorda_com_a_fonte():
    texto = CONFIG_STREAMLIT.read_text(encoding="utf-8")

    def valor(chave):
        achado = re.search(rf'^{chave}\s*=\s*"([^"]+)"', texto, re.MULTILINE)
        assert achado, f"chave '{chave}' não encontrada em {CONFIG_STREAMLIT.name}"
        return achado.group(1)

    assert valor("primaryColor").lower() == FONTE_TOKENS["gs-blue-accent"]
    assert valor("backgroundColor").lower() == FONTE_TOKENS["gs-white"]
    assert valor("secondaryBackgroundColor").lower() == FONTE_TOKENS["gs-bg-alt"]
    assert valor("textColor").lower() == FONTE_TOKENS["gs-text"]

    # As fontes vêm do tema nativo (não só do CSS injetado) — conferir que
    # continuam sendo as da marca, não a default do Streamlit.
    assert "Montserrat" in valor("font")
    assert "Space Grotesk" in valor("headingFont")


def test_cores_do_pdf_concordam_com_a_fonte():
    """No exportarPdf.js os tokens estão em RGB, com o hex de origem no
    comentário da linha. Confere que o RGB corresponde ao hex E que o hex é
    de fato um token da marca."""
    texto = EXPORTAR_PDF.read_text(encoding="utf-8")
    linhas = re.findall(
        r"const\s+COR_\w+\s*=\s*\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]\s*;\s*//\s*(#[0-9a-fA-F]{6})",
        texto,
    )
    assert linhas, "nenhuma cor com hex de origem encontrada em exportarPdf.js"

    hex_da_marca = {v for v in FONTE_TOKENS.values() if v.startswith("#")}
    for r, g, b, hexadecimal in linhas:
        esperado = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
        assert esperado == hexadecimal.lower(), (
            f"RGB [{r}, {g}, {b}] não corresponde ao hex {hexadecimal} anotado na linha"
        )
        assert hexadecimal.lower() in hex_da_marca, (
            f"{hexadecimal} não é um token do design-tokens.md"
        )
