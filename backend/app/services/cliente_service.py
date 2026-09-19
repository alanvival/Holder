from app.core.enums import FaixaRisco, Plano, Porte, SituacaoCliente
from app.core.exceptions import RecursoNaoEncontradoError
from app.models import Cliente
from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.avaliacao_repository import AvaliacaoRepository
from app.repositories.cliente_repository import ClienteRepository, FiltroClientes
from app.repositories.execucao_repository import ExecucaoRepository
from app.repositories.nps_repository import NpsRepository
from app.schemas.cliente import (
    AtendimentoMes,
    ClienteDetalhe,
    ClienteResumo,
    HistoricoCliente,
    NpsMes,
)
from app.schemas.comum import Pagina
from app.services.mapeadores import avaliacao_response, cliente_resumo


class ClienteService:
    """Consultas de clientes combinadas com a última avaliação de risco de produção."""

    def __init__(
        self,
        clientes: ClienteRepository,
        atendimentos: AtendimentoRepository,
        nps: NpsRepository,
        execucoes: ExecucaoRepository,
        avaliacoes: AvaliacaoRepository,
    ) -> None:
        self._clientes = clientes
        self._atendimentos = atendimentos
        self._nps = nps
        self._execucoes = execucoes
        self._avaliacoes = avaliacoes

    def listar(
        self,
        *,
        situacao: SituacaoCliente | None = None,
        faixa: FaixaRisco | None = None,
        plano: Plano | None = None,
        porte: Porte | None = None,
        segmento: str | None = None,
        busca: str | None = None,
        ordenar: str = "cliente_id",
        pagina: int = 1,
        tamanho: int = 20,
    ) -> Pagina[ClienteResumo]:
        execucao = self._execucoes.ultima_producao()
        filtro = FiltroClientes(situacao, faixa, plano, porte, segmento, busca)
        linhas, total = self._clientes.buscar(
            execucao.id if execucao else None, filtro, ordenar, (pagina - 1) * tamanho, tamanho
        )
        return Pagina[ClienteResumo](
            itens=[cliente_resumo(cliente, avaliacao) for cliente, avaliacao in linhas],
            total=total,
            pagina=pagina,
            tamanho=tamanho,
        )

    def detalhe(self, cliente_id: str) -> ClienteDetalhe:
        cliente = self._obter(cliente_id)
        execucao = self._execucoes.ultima_producao()
        avaliacao = (
            self._avaliacoes.obter_por_cliente(execucao.id, cliente.cliente_id)
            if execucao
            else None
        )
        return ClienteDetalhe(
            **cliente_resumo(cliente, avaliacao).model_dump(),
            avaliacao=avaliacao_response(avaliacao) if avaliacao else None,
        )

    def historico(self, cliente_id: str) -> HistoricoCliente:
        cliente = self._obter(cliente_id)
        return HistoricoCliente(
            cliente_id=cliente.cliente_id,
            atendimento=[
                AtendimentoMes.model_validate(a)
                for a in self._atendimentos.listar_por_cliente(cliente.cliente_id)
            ],
            nps=[
                NpsMes.model_validate(p) for p in self._nps.listar_por_cliente(cliente.cliente_id)
            ],
        )

    def _obter(self, cliente_id: str) -> Cliente:
        codigo = cliente_id.strip().upper()
        cliente = self._clientes.obter(codigo)
        if cliente is None:
            raise RecursoNaoEncontradoError(f"Cliente {codigo} não encontrado")
        return cliente
