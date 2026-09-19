"""Enums de domínio. O valor é igual ao nome e é o que vai para o banco."""

from enum import StrEnum


class Porte(StrEnum):
    PEQUENO = "PEQUENO"
    MEDIO = "MEDIO"
    GRANDE = "GRANDE"


class Plano(StrEnum):
    ESSENCIAL = "ESSENCIAL"
    AVANCADO = "AVANCADO"
    ENTERPRISE = "ENTERPRISE"


class SituacaoCliente(StrEnum):
    ATIVO = "ATIVO"
    CANCELADO = "CANCELADO"


class ClassificacaoNPS(StrEnum):
    PROMOTOR = "PROMOTOR"
    NEUTRO = "NEUTRO"
    DETRATOR = "DETRATOR"
    SEM_RESPOSTA = "SEM_RESPOSTA"


class Dimensao(StrEnum):
    ATENDIMENTO = "ATENDIMENTO"
    SLA = "SLA"
    ENGAJAMENTO = "ENGAJAMENTO"
    FINANCEIRO = "FINANCEIRO"
    SATISFACAO = "SATISFACAO"


class TipoRegra(StrEnum):
    NIVEL = "NIVEL"
    TENDENCIA = "TENDENCIA"
    EVENTO = "EVENTO"


class SentidoPiora(StrEnum):
    AUMENTO = "AUMENTO"
    QUEDA = "QUEDA"


class FaixaRisco(StrEnum):
    CRITICO = "CRITICO"
    ATENCAO = "ATENCAO"
    MONITORAR = "MONITORAR"
    SAUDAVEL = "SAUDAVEL"


class TipoExecucao(StrEnum):
    PRODUCAO = "PRODUCAO"
    CALIBRACAO = "CALIBRACAO"
    BACKTEST = "BACKTEST"


class Responsavel(StrEnum):
    CS = "CS"
    TECNICO = "TECNICO"
    FINANCEIRO = "FINANCEIRO"
    EXECUTIVO = "EXECUTIVO"
