from app.core.exceptions import ParametroInvalidoError
from app.repositories.atendimento_repository import AtendimentoRepository
from app.schemas.metrica import PontoMensal, VariavelMetrica

VARIAVEIS_METRICA: dict[str, str] = {
    "chamados_abertos": "Chamados abertos (qtd)",
    "chamados_criticos": "Chamados críticos (qtd)",
    "chamados_reabertos": "Chamados reabertos (qtd)",
    "chamados_dentro_sla": "Chamados dentro do SLA (qtd)",
    "pct_sla_cumprido": "SLA cumprido (%)",
    "tempo_medio_resolucao_h": "Tempo médio de resolução (h)",
    "reclamacoes_formais": "Reclamações formais (qtd)",
    "uso_plataforma_pct": "Uso da plataforma (%)",
    "dias_atraso_pagamento": "Dias de atraso no pagamento",
    "reunioes_previstas": "Reuniões previstas (qtd)",
    "reunioes_realizadas": "Reuniões realizadas (qtd)",
}


class MetricaService:
    """Evolução mensal agregada de toda a carteira (média ou soma, ignorando nulos)."""

    def __init__(self, atendimentos: AtendimentoRepository) -> None:
        self._atendimentos = atendimentos

    def variaveis(self) -> list[VariavelMetrica]:
        return [VariavelMetrica(codigo=c, rotulo=r) for c, r in VARIAVEIS_METRICA.items()]

    def mensal(self, variavel: str, agregacao: str) -> list[PontoMensal]:
        if variavel not in VARIAVEIS_METRICA:
            raise ParametroInvalidoError(
                f"Variável '{variavel}' inválida. Use uma de: {', '.join(VARIAVEIS_METRICA)}"
            )
        return [
            PontoMensal(mes_ref=mes, valor=round(valor, 4))
            for mes, valor in self._atendimentos.agregado_mensal(variavel, agregacao)
        ]
