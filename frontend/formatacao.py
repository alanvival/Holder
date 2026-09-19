ROTULO_FAIXA = {
    "CRITICO": "Crítico",
    "ATENCAO": "Atenção",
    "MONITORAR": "Monitorar",
    "SAUDAVEL": "Saudável",
}
ROTULO_RESPONSAVEL = {
    "CS": "Customer Success",
    "TECNICO": "Técnico",
    "FINANCEIRO": "Financeiro",
    "EXECUTIVO": "Executivo",
}


def _padrao_br(texto: str) -> str:
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def brl(valor: float | None) -> str:
    if valor is None:
        return "—"
    return "R$ " + _padrao_br(f"{valor:,.2f}")


def percentual(valor: float | None, casas: int = 0) -> str:
    if valor is None:
        return "—"
    return _padrao_br(f"{valor * 100:.{casas}f}") + "%"
