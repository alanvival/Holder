"""Importação da planilha INOVAAPPS para as tabelas de origem.

Regras: valida abas/colunas/enums antes de gravar (arquivo ruim não apaga nada),
converte meses 'AAAA-MM' para date(ano, mes, 1), mantém nulos que são informação
(pct_sla_cumprido sem chamado, NPS sem resposta) e é idempotente (substitui tudo).
"""

import io
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.enums import ClassificacaoNPS, Plano, Porte, SituacaoCliente
from app.core.exceptions import ImportacaoInvalidaError
from app.models import AtendimentoMensal, Cliente, PesquisaNps, Situacao
from app.repositories.origem_repository import OrigemRepository
from app.services.catalogo_service import CatalogoService

ABAS_COLUNAS: dict[str, list[str]] = {
    "clientes": [
        "cliente_id",
        "segmento",
        "porte",
        "plano",
        "valor_mensal",
        "sla_contratado_h",
        "inicio_contrato",
    ],
    "atendimento_mensal": [
        "cliente_id",
        "mes_ref",
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
    ],
    "pesquisas_nps": ["cliente_id", "mes_ref", "respondeu", "nota_nps", "classificacao_nps"],
    "situacao_clientes": ["cliente_id", "situacao", "mes_cancelamento"],
}

CONTAGENS_ESPERADAS = {
    "clientes": 80,
    "situacao_clientes": 80,
    "atendimentos_mensais": 1295,
    "pesquisas_nps": 422,
}
CANCELADOS_ESPERADOS = 22


@dataclass
class RelatorioImportacao:
    contagens: dict[str, int]
    avisos: list[str] = field(default_factory=list)


def _nulo(valor: Any) -> bool:
    return valor is None or (not isinstance(valor, str) and bool(pd.isna(valor)))


def _enum(valor: Any, enum_cls: type[Enum], campo: str) -> Any:
    chave = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    chave = chave.strip().upper().replace(" ", "_")
    try:
        return enum_cls(chave)
    except ValueError as erro:
        raise ImportacaoInvalidaError(f"Valor inválido '{valor}' em {campo}") from erro


def _mes(valor: Any, campo: str) -> date | None:
    if _nulo(valor):
        return None
    if isinstance(valor, datetime):
        return date(valor.year, valor.month, 1)
    try:
        ano, mes = str(valor).strip().split("-")[:2]
        return date(int(ano), int(mes), 1)
    except (ValueError, TypeError) as erro:
        raise ImportacaoInvalidaError(f"Mês inválido '{valor}' em {campo}") from erro


def _mes_obrigatorio(valor: Any, campo: str) -> date:
    if _nulo(valor):
        raise ImportacaoInvalidaError(f"Valor vazio em {campo}")
    return _mes(valor, campo)  # type: ignore[return-value]


def _data(valor: Any, campo: str) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    try:
        return date.fromisoformat(str(valor).strip()[:10])
    except ValueError as erro:
        raise ImportacaoInvalidaError(f"Data inválida '{valor}' em {campo}") from erro


def _decimal(valor: Any, campo: str) -> Decimal | None:
    if _nulo(valor):
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError) as erro:
        raise ImportacaoInvalidaError(f"Valor inválido '{valor}' em {campo}") from erro


def _decimal_obrigatorio(valor: Any, campo: str) -> Decimal:
    if _nulo(valor):
        raise ImportacaoInvalidaError(f"Valor vazio em {campo}")
    return _decimal(valor, campo)  # type: ignore[return-value]


def _inteiro(valor: Any, campo: str) -> int:
    if _nulo(valor):
        raise ImportacaoInvalidaError(f"Valor vazio em {campo}")
    try:
        numero = float(valor)
    except (TypeError, ValueError) as erro:
        raise ImportacaoInvalidaError(f"Valor inválido '{valor}' em {campo}") from erro
    if not numero.is_integer():
        raise ImportacaoInvalidaError(f"Valor inválido '{valor}' em {campo}")
    return int(numero)


class ImportacaoService:
    def __init__(self, repo: OrigemRepository, catalogo: CatalogoService) -> None:
        self._repo = repo
        self._catalogo = catalogo

    def importar(self, origem: str | Path | bytes) -> RelatorioImportacao:
        abas = self._ler(origem)
        clientes = [self._cliente(linha) for linha in abas["clientes"].to_dict("records")]
        situacoes = [
            self._situacao(linha) for linha in abas["situacao_clientes"].to_dict("records")
        ]
        atendimentos = [
            self._atendimento(linha) for linha in abas["atendimento_mensal"].to_dict("records")
        ]
        pesquisas = [self._pesquisa(linha) for linha in abas["pesquisas_nps"].to_dict("records")]
        self._validar_chaves(clientes, situacoes, atendimentos, pesquisas)

        self._repo.substituir_tudo(clientes, situacoes, atendimentos, pesquisas)
        self._catalogo.garantir_seeds()

        contagens = {
            "clientes": len(clientes),
            "situacao_clientes": len(situacoes),
            "atendimentos_mensais": len(atendimentos),
            "pesquisas_nps": len(pesquisas),
        }
        cancelados = sum(1 for s in situacoes if s.situacao == SituacaoCliente.CANCELADO)
        return RelatorioImportacao(contagens, self._avisos(contagens, cancelados))

    def _ler(self, origem: str | Path | bytes) -> dict[str, pd.DataFrame]:
        fonte = io.BytesIO(origem) if isinstance(origem, bytes) else origem
        try:
            abas = pd.read_excel(fonte, sheet_name=None)
        except Exception as erro:
            raise ImportacaoInvalidaError(
                "Não foi possível ler o arquivo: envie uma planilha .xlsx válida"
            ) from erro
        for aba, colunas in ABAS_COLUNAS.items():
            if aba not in abas:
                raise ImportacaoInvalidaError(f"Aba '{aba}' não encontrada no arquivo")
            faltando = [coluna for coluna in colunas if coluna not in abas[aba].columns]
            if faltando:
                raise ImportacaoInvalidaError(f"Aba '{aba}' sem as colunas: {', '.join(faltando)}")
        return abas

    @staticmethod
    def _cliente(linha: dict[str, Any]) -> Cliente:
        return Cliente(
            cliente_id=str(linha["cliente_id"]).strip(),
            segmento=str(linha["segmento"]).strip(),
            porte=_enum(linha["porte"], Porte, "clientes.porte"),
            plano=_enum(linha["plano"], Plano, "clientes.plano"),
            valor_mensal=_decimal_obrigatorio(linha["valor_mensal"], "clientes.valor_mensal"),
            sla_contratado_h=_inteiro(linha["sla_contratado_h"], "clientes.sla_contratado_h"),
            inicio_contrato=_data(linha["inicio_contrato"], "clientes.inicio_contrato"),
        )

    @staticmethod
    def _situacao(linha: dict[str, Any]) -> Situacao:
        return Situacao(
            cliente_id=str(linha["cliente_id"]).strip(),
            situacao=_enum(linha["situacao"], SituacaoCliente, "situacao_clientes.situacao"),
            mes_cancelamento=_mes(linha["mes_cancelamento"], "situacao_clientes.mes_cancelamento"),
        )

    @staticmethod
    def _atendimento(linha: dict[str, Any]) -> AtendimentoMensal:
        inteiros = {
            coluna: _inteiro(linha[coluna], f"atendimento_mensal.{coluna}")
            for coluna in (
                "chamados_abertos",
                "chamados_criticos",
                "chamados_reabertos",
                "chamados_dentro_sla",
                "reclamacoes_formais",
                "dias_atraso_pagamento",
                "reunioes_previstas",
                "reunioes_realizadas",
            )
        }
        return AtendimentoMensal(
            cliente_id=str(linha["cliente_id"]).strip(),
            mes_ref=_mes_obrigatorio(linha["mes_ref"], "atendimento_mensal.mes_ref"),
            pct_sla_cumprido=_decimal(
                linha["pct_sla_cumprido"], "atendimento_mensal.pct_sla_cumprido"
            ),
            tempo_medio_resolucao_h=_decimal_obrigatorio(
                linha["tempo_medio_resolucao_h"], "atendimento_mensal.tempo_medio_resolucao_h"
            ),
            uso_plataforma_pct=_decimal_obrigatorio(
                linha["uso_plataforma_pct"], "atendimento_mensal.uso_plataforma_pct"
            ),
            **inteiros,
        )

    @staticmethod
    def _pesquisa(linha: dict[str, Any]) -> PesquisaNps:
        return PesquisaNps(
            cliente_id=str(linha["cliente_id"]).strip(),
            mes_ref=_mes_obrigatorio(linha["mes_ref"], "pesquisas_nps.mes_ref"),
            respondeu=bool(_inteiro(linha["respondeu"], "pesquisas_nps.respondeu")),
            nota_nps=None
            if _nulo(linha["nota_nps"])
            else _inteiro(linha["nota_nps"], "pesquisas_nps.nota_nps"),
            classificacao_nps=_enum(
                linha["classificacao_nps"], ClassificacaoNPS, "pesquisas_nps.classificacao_nps"
            ),
        )

    @staticmethod
    def _validar_chaves(
        clientes: list[Cliente],
        situacoes: list[Situacao],
        atendimentos: list[AtendimentoMensal],
        pesquisas: list[PesquisaNps],
    ) -> None:
        ids = [c.cliente_id for c in clientes]
        if len(ids) != len(set(ids)):
            raise ImportacaoInvalidaError("Aba 'clientes' tem cliente_id duplicado")
        conhecidos = set(ids)
        for aba, chaves in (
            ("situacao_clientes", [(s.cliente_id,) for s in situacoes]),
            ("atendimento_mensal", [(a.cliente_id, a.mes_ref) for a in atendimentos]),
            ("pesquisas_nps", [(p.cliente_id, p.mes_ref) for p in pesquisas]),
        ):
            if len(chaves) != len(set(chaves)):
                raise ImportacaoInvalidaError(f"Aba '{aba}' tem linhas duplicadas")
            desconhecidos = {chave[0] for chave in chaves} - conhecidos
            if desconhecidos:
                raise ImportacaoInvalidaError(
                    f"Aba '{aba}' cita clientes inexistentes: {', '.join(sorted(desconhecidos))}"
                )

        sem_situacao = conhecidos - {s.cliente_id for s in situacoes}
        if sem_situacao:
            raise ImportacaoInvalidaError(
                "Aba 'situacao_clientes' sem situação para: " + ", ".join(sorted(sem_situacao))
            )

    @staticmethod
    def _avisos(contagens: dict[str, int], cancelados: int) -> list[str]:
        avisos = [
            f"{tabela}: esperado {esperado}, importado {contagens[tabela]}"
            for tabela, esperado in CONTAGENS_ESPERADAS.items()
            if contagens[tabela] != esperado
        ]
        if cancelados != CANCELADOS_ESPERADOS:
            avisos.append(f"cancelados: esperado {CANCELADOS_ESPERADOS}, importado {cancelados}")
        return avisos
