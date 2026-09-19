"""Análise de produção: indicadores → sinais → score → recomendação → fila → grava.

Regras: só clientes ATIVOS são avaliados; o mês de referência padrão é o último
mês da base; tudo é gravado em uma transação; dashboard e fila leem sempre a
última execução PRODUCAO.
"""

import json
import logging
import time
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from app.core.config import Settings
from app.core.enums import SituacaoCliente, TipoExecucao
from app.core.exceptions import RecursoNaoEncontradoError
from app.models import (
    AcaoRecomendada,
    AvaliacaoRisco,
    Cliente,
    ConfiguracaoSinal,
    EvidenciaRisco,
    ExecucaoAnalise,
)
from app.repositories.acao_repository import AcaoRepository
from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.execucao_repository import ExecucaoRepository
from app.repositories.nps_repository import NpsRepository
from app.repositories.sinal_repository import SinalRepository
from app.services.risco.indicadores import calcular_indicadores
from app.services.risco.priorizacao import ItemAvaliado, priorizar
from app.services.risco.recomendacao import recomendar
from app.services.risco.score import LimiaresFaixa, ResultadoScore, calcular_score
from app.services.risco.sinais import DefinicaoSinal, avaliar_sinais

logger = logging.getLogger(__name__)

COLUNAS_ATENDIMENTO = (
    "chamados_abertos",
    "chamados_criticos",
    "chamados_reabertos",
    "chamados_dentro_sla",
    "pct_sla_cumprido",
    "tempo_medio_resolucao_h",
    "reclamacoes_formais",
    "uso_plataforma_pct",
    "dias_atraso_pagamento",
    "reunioes_previstas",
    "reunioes_realizadas",
)


def _num(valor: Any) -> float | None:
    return None if valor is None else float(valor)


def _dec(valor: float, casas: int) -> Decimal:
    return Decimal(f"{valor:.{casas}f}")


def _dec_opcional(valor: float | None, casas: int) -> Decimal | None:
    return None if valor is None else _dec(valor, casas)


class AnaliseService:
    VERSAO_MODELO = "mvp-regras-1"

    def __init__(
        self,
        clientes: ClienteRepository,
        atendimentos: AtendimentoRepository,
        nps: NpsRepository,
        sinais: SinalRepository,
        acoes: AcaoRepository,
        execucoes: ExecucaoRepository,
        settings: Settings,
    ) -> None:
        self._clientes = clientes
        self._atendimentos = atendimentos
        self._nps = nps
        self._sinais = sinais
        self._acoes = acoes
        self._execucoes = execucoes
        self._settings = settings

    def executar(
        self, mes_referencia: date | None = None, usuario_id: int | None = None
    ) -> ExecucaoAnalise:
        inicio = time.perf_counter()
        mes = mes_referencia or self._atendimentos.ultimo_mes()
        if mes is None:
            raise RecursoNaoEncontradoError(
                "Não há dados para analisar. Importe a planilha primeiro."
            )
        clientes = self._clientes.listar_todos()
        ativos = [
            c
            for c in clientes
            if c.situacao is not None and c.situacao.situacao == SituacaoCliente.ATIVO
        ]
        indicadores = calcular_indicadores(
            self._df_atendimentos(), self._df_pesquisas(), self._df_clientes(clientes), mes
        )
        por_cliente = self._agrupar(indicadores)
        definicoes = [self._definicao(sinal) for sinal in self._sinais.listar_ativos()]
        limiares = LimiaresFaixa(
            critico=self._settings.limiar_critico,
            atencao=self._settings.limiar_atencao,
            monitorar=self._settings.limiar_monitorar,
        )

        resultados: dict[str, ResultadoScore] = {}
        itens: list[ItemAvaliado] = []
        for cliente in ativos:
            disparos = avaliar_sinais(definicoes, por_cliente.get(cliente.cliente_id, {}))
            resultado = calcular_score(disparos, limiares)
            resultados[cliente.cliente_id] = resultado
            itens.append(
                ItemAvaliado(
                    cliente_id=cliente.cliente_id,
                    valor_mensal=float(cliente.valor_mensal),
                    score=resultado.score,
                    faixa=resultado.faixa,
                )
            )
        priorizados = priorizar(itens, self._settings.capacidade_fila)

        acoes = self._acoes.mapa_por_codigo()
        execucao = ExecucaoAnalise(
            tipo=TipoExecucao.PRODUCAO,
            mes_referencia=mes,
            versao_modelo=self.VERSAO_MODELO,
            parametros_json=json.dumps(
                {
                    "capacidade_fila": self._settings.capacidade_fila,
                    "limiares": {
                        "critico": limiares.critico,
                        "atencao": limiares.atencao,
                        "monitorar": limiares.monitorar,
                    },
                    "sinais_ativos": [d.codigo for d in definicoes],
                }
            ),
            executado_por_usuario_id=usuario_id,
            qtd_clientes_avaliados=len(itens),
        )
        for item in priorizados:
            execucao.avaliacoes.append(
                self._avaliacao(item, resultados[item.cliente_id], mes, acoes)
            )
        self._execucoes.gravar(execucao)
        logger.info(
            "Análise %s concluída: mes=%s clientes=%d fila=%d tempo=%.2fs",
            self.VERSAO_MODELO,
            mes,
            len(itens),
            execucao.qtd_na_fila,
            time.perf_counter() - inicio,
        )
        return execucao

    def _df_atendimentos(self) -> pd.DataFrame:
        linhas = [
            {
                "cliente_id": a.cliente_id,
                "mes_ref": a.mes_ref,
                **{coluna: _num(getattr(a, coluna)) for coluna in COLUNAS_ATENDIMENTO},
            }
            for a in self._atendimentos.listar_todos()
        ]
        return pd.DataFrame(linhas, columns=["cliente_id", "mes_ref", *COLUNAS_ATENDIMENTO])

    def _df_pesquisas(self) -> pd.DataFrame:
        linhas = [
            {
                "cliente_id": p.cliente_id,
                "mes_ref": p.mes_ref,
                "respondeu": bool(p.respondeu),
                "nota_nps": _num(p.nota_nps),
            }
            for p in self._nps.listar_todos()
        ]
        return pd.DataFrame(linhas, columns=["cliente_id", "mes_ref", "respondeu", "nota_nps"])

    @staticmethod
    def _df_clientes(clientes: list[Cliente]) -> pd.DataFrame:
        linhas = [
            {"cliente_id": c.cliente_id, "sla_contratado_h": c.sla_contratado_h} for c in clientes
        ]
        return pd.DataFrame(linhas, columns=["cliente_id", "sla_contratado_h"])

    @staticmethod
    def _agrupar(indicadores: pd.DataFrame) -> dict[str, dict[str, dict[str, Any]]]:
        por_cliente: dict[str, dict[str, dict[str, Any]]] = {}
        for linha in indicadores.to_dict("records"):
            por_cliente.setdefault(linha["cliente_id"], {})[linha["variavel"]] = linha
        return por_cliente

    @staticmethod
    def _definicao(sinal: ConfiguracaoSinal) -> DefinicaoSinal:
        return DefinicaoSinal(
            id=sinal.id,
            codigo=sinal.codigo,
            dimensao=sinal.dimensao,
            variavel=sinal.variavel,
            tipo_regra=sinal.tipo_regra,
            sentido_piora=sinal.sentido_piora,
            limiar=float(sinal.limiar),
            persistencia_min_meses=sinal.persistencia_min_meses,
            peso=float(sinal.peso),
            template_evidencia=sinal.template_evidencia,
            metrica=sinal.metrica,
        )

    @staticmethod
    def _avaliacao(
        item: ItemAvaliado,
        resultado: ResultadoScore,
        mes: date,
        acoes: dict[str, AcaoRecomendada],
    ) -> AvaliacaoRisco:
        codigo_acao = recomendar(resultado.evidencias)
        acao = acoes.get(codigo_acao) if codigo_acao else None
        avaliacao = AvaliacaoRisco(
            cliente_id=item.cliente_id,
            mes_referencia=mes,
            score_risco=_dec(item.score, 4),
            faixa=item.faixa,
            qtd_dimensoes_afetadas=resultado.qtd_dimensoes_afetadas,
            receita_em_risco=_dec(item.receita_em_risco, 2),
            posicao_fila=item.posicao_fila,
            acao_recomendada_id=acao.id if acao else None,
        )
        avaliacao.evidencias = [
            EvidenciaRisco(
                configuracao_sinal_id=e.disparo.sinal.id,
                dimensao=e.disparo.sinal.dimensao,
                valor_observado=_dec(e.disparo.valor_observado, 4),
                linha_base=_dec_opcional(e.disparo.linha_base, 4),
                variacao_pct=_dec_opcional(e.disparo.variacao_pct, 4),
                meses_persistencia=e.disparo.meses_persistencia,
                contribuicao=_dec(e.contribuicao, 4),
                texto=e.disparo.texto[:300],
            )
            for e in resultado.evidencias
        ]
        return avaliacao
