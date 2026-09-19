from collections import Counter

from app.core.enums import Dimensao, FaixaRisco
from app.repositories.avaliacao_repository import AvaliacaoRepository
from app.repositories.execucao_repository import ExecucaoRepository
from app.schemas.dashboard import ItemFila, ResumoDashboard
from app.services.mapeadores import item_fila

FAIXAS_EM_RISCO = (FaixaRisco.CRITICO, FaixaRisco.ATENCAO)


class DashboardService:
    """Resumo e fila, sempre a partir da última execução de produção.

    Receita em risco do resumo = soma da receita em risco dos clientes em
    CRITICO ou ATENCAO. Por dimensão = quantos clientes têm ao menos um sinal
    disparado naquela dimensão.
    """

    def __init__(self, execucoes: ExecucaoRepository, avaliacoes: AvaliacaoRepository) -> None:
        self._execucoes = execucoes
        self._avaliacoes = avaliacoes

    def resumo(self) -> ResumoDashboard:
        execucao = self._execucoes.ultima_producao()
        if execucao is None:
            return ResumoDashboard(
                mes_referencia=None,
                executado_em=None,
                clientes_ativos=0,
                receita_ativa=0.0,
                receita_em_risco=0.0,
                qtd_na_fila=0,
                por_faixa=dict.fromkeys(FaixaRisco, 0),
                por_dimensao=dict.fromkeys(Dimensao, 0),
            )
        avaliacoes = self._avaliacoes.listar_por_execucao(execucao.id)
        por_faixa = Counter(a.faixa for a in avaliacoes)
        por_dimensao: Counter[Dimensao] = Counter()
        for avaliacao in avaliacoes:
            por_dimensao.update({e.dimensao for e in avaliacao.evidencias})
        return ResumoDashboard(
            mes_referencia=execucao.mes_referencia,
            executado_em=execucao.executado_em,
            clientes_ativos=len(avaliacoes),
            receita_ativa=round(sum(float(a.cliente.valor_mensal) for a in avaliacoes), 2),
            receita_em_risco=round(
                sum(float(a.receita_em_risco) for a in avaliacoes if a.faixa in FAIXAS_EM_RISCO),
                2,
            ),
            qtd_na_fila=sum(1 for a in avaliacoes if a.posicao_fila is not None),
            por_faixa={faixa: por_faixa.get(faixa, 0) for faixa in FaixaRisco},
            por_dimensao={dimensao: por_dimensao.get(dimensao, 0) for dimensao in Dimensao},
        )

    def fila(self, limite: int) -> list[ItemFila]:
        execucao = self._execucoes.ultima_producao()
        if execucao is None:
            return []
        return [item_fila(a) for a in self._avaliacoes.fila(execucao.id, limite)]
