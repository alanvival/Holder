from decimal import Decimal

from app.models import AcaoRecomendada, ConfiguracaoSinal
from app.repositories.acao_repository import AcaoRepository
from app.repositories.sinal_repository import SinalRepository
from app.services.catalogo_seed import ACOES_SEED, PESO_INICIAL, SINAIS_SEED


class CatalogoService:
    """Catálogo de sinais e playbook de ações. Garante o seed sem duplicar."""

    def __init__(
        self, sinais: SinalRepository, acoes: AcaoRepository, persistencia_padrao: int
    ) -> None:
        self._sinais = sinais
        self._acoes = acoes
        self._persistencia_padrao = persistencia_padrao

    def garantir_seeds(self) -> None:
        existentes = self._sinais.listar_codigos()
        self._sinais.adicionar_todos(
            [
                ConfiguracaoSinal(
                    **{**seed, "limiar": Decimal(str(seed["limiar"]))},
                    peso=Decimal(str(PESO_INICIAL)),
                    persistencia_min_meses=self._persistencia_padrao,
                    ativo=True,
                )
                for seed in SINAIS_SEED
                if seed["codigo"] not in existentes
            ]
        )
        acoes_existentes = self._acoes.listar_codigos()
        self._acoes.adicionar_todos(
            [
                AcaoRecomendada(**seed)
                for seed in ACOES_SEED
                if seed["codigo"] not in acoes_existentes
            ]
        )

    def listar_sinais(self) -> list[ConfiguracaoSinal]:
        return self._sinais.listar()

    def listar_acoes(self) -> list[AcaoRecomendada]:
        return self._acoes.listar()
