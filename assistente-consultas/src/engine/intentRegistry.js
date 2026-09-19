// Camada de intenção (item 1 do motor, conforme especificação):
// cada pergunta que o admin cadastra vira um "template de intenção" com
// parâmetros. Aqui está a base inicial cobrindo os 8 exemplos do prompt.
//
// Estrutura de uma intenção — é também a "estrutura de dados sugerida para
// perguntas/intenções cadastradas" pedida no item 2 dos entregáveis:
//   {
//     id: string,                 // chave estável (nunca muda após criada)
//     rotulo: string,              // nome amigável pro admin
//     exemplos: string[],          // frases de treino p/ a similaridade
//     parametros: string[],        // entidades que a intenção espera
//     requerEntidade: (entidades) => boolean,  // valida se achou o necessário
//     resolver: (entidades, hoje) => RespostaPayload,
//     criadaEm: string,            // ISO — quando o admin cadastrou
//     ativa: boolean,
//   }

import {
  pessoas,
  acompanhamentos,
  atividades,
  procedimentos,
  camposCadastrados,
} from '../data/mockDatabase.js';
import { extractPerson, extractPeriod, extractDate } from './entities.js';
import { dateResponse, listResponse, locationResponse, notFoundResponse, formatDatePt } from './responseFormat.js';

function ultimoAcompanhamento(entidades) {
  const { pessoa } = entidades;
  if (!pessoa) return notFoundResponse();
  const registros = acompanhamentos
    .filter((a) => a.pessoaId === pessoa.id)
    .sort((a, b) => (a.data < b.data ? 1 : -1));
  if (registros.length === 0) return notFoundResponse();
  return dateResponse(`O último acompanhamento de ${pessoa.nome} foi realizado em:`, registros[0].data);
}

function atividadesNoPeriodo(entidades) {
  const periodo = entidades.periodo;
  if (!periodo) return notFoundResponse();
  const registros = atividades.filter((a) => a.data >= periodo.start && a.data <= periodo.end);
  if (registros.length === 0) return notFoundResponse();
  return listResponse(
    `Foram encontradas ${registros.length} atividades neste período:`,
    registros.map((a) => ({ label: `${a.tipo} — ${formatDatePt(a.data).slice(0, 5)}` })),
  );
}

function pessoasSemAcompanhamento(entidades) {
  const diasLimite = entidades.diasLimite ?? 30;
  const hoje = entidades.hoje;
  const limite = new Date(hoje);
  limite.setDate(limite.getDate() - diasLimite);

  const semAcompanhamento = pessoas.filter((pessoa) => {
    const registros = acompanhamentos.filter((a) => a.pessoaId === pessoa.id);
    if (registros.length === 0) return true;
    const maisRecente = registros.sort((a, b) => (a.data < b.data ? 1 : -1))[0];
    return new Date(maisRecente.data) < limite;
  });

  if (semAcompanhamento.length === 0) return notFoundResponse();
  return listResponse(
    `${semAcompanhamento.length} pessoa(s) sem acompanhamento há mais de ${diasLimite} dias:`,
    semAcompanhamento.map((p) => ({ label: p.nome })),
  );
}

function ondeCadastrarInformacao(entidades) {
  const termo = entidades.termoLivre?.toLowerCase() ?? '';
  const campo = camposCadastrados.find((c) => termo.includes(c.nome.toLowerCase().split(' ')[0]));
  if (!campo) return notFoundResponse();
  return locationResponse(`A informação "${campo.nome}" está cadastrada em:`, campo.local);
}

function ondeFazerProcedimento(entidades) {
  const termo = entidades.termoLivre?.toLowerCase() ?? '';
  const proc = procedimentos.find((p) => termo.includes(p.nome.toLowerCase().split(' ')[0]));
  if (!proc) return notFoundResponse();
  return locationResponse(`Para "${proc.nome}", acesse:`, proc.local);
}

function oQueFoiRealizadoEmData(entidades) {
  const data = entidades.data;
  if (!data) return notFoundResponse();
  const registros = atividades.filter((a) => a.data === data);
  if (registros.length === 0) return notFoundResponse();
  return listResponse(
    `Atividades realizadas em ${formatDatePt(data)}:`,
    registros.map((a) => ({ label: `${a.tipo} — ${pessoas.find((p) => p.id === a.pessoaId)?.nome ?? ''}` })),
  );
}

function quandoAconteceuEvento(entidades) {
  const { pessoa } = entidades;
  if (!pessoa) return notFoundResponse();
  const registros = [...acompanhamentos, ...atividades]
    .filter((a) => a.pessoaId === pessoa.id)
    .sort((a, b) => (a.data < b.data ? 1 : -1));
  if (registros.length === 0) return notFoundResponse();
  return dateResponse(`O evento mais recente de ${pessoa.nome} aconteceu em:`, registros[0].data);
}

function datasSemAcompanhamento(entidades) {
  const periodo = entidades.periodo;
  if (!periodo) return notFoundResponse();
  const diasComRegistro = new Set(acompanhamentos.map((a) => a.data));
  const inicio = new Date(periodo.start);
  const fim = new Date(periodo.end);
  const semRegistro = [];
  for (let d = new Date(inicio); d <= fim; d.setDate(d.getDate() + 1)) {
    const iso = d.toISOString().slice(0, 10);
    if (!diasComRegistro.has(iso)) semRegistro.push(iso);
  }
  if (semRegistro.length === 0) return notFoundResponse();
  return listResponse(
    `${semRegistro.length} data(s) ficaram sem acompanhamento no período:`,
    semRegistro.slice(0, 8).map((iso) => ({ label: formatDatePt(iso) })),
  );
}

// Extrator de entidades comum a todas as intenções — roda antes do resolver.
export function extrairEntidades(texto, hoje) {
  return {
    pessoa: extractPerson(texto, pessoas),
    periodo: extractPeriod(texto, hoje),
    data: extractDate(texto, hoje),
    termoLivre: texto,
    hoje,
    diasLimite: (() => {
      const match = texto.match(/(\d+)\s*dias?/i);
      return match ? Number(match[1]) : undefined;
    })(),
  };
}

export const intentRegistry = [
  {
    id: 'ultimo_acompanhamento',
    rotulo: 'Último acompanhamento de uma pessoa',
    exemplos: [
      'Qual foi o último acompanhamento de determinada pessoa?',
      'Qual foi o último acompanhamento do João?',
      'Quando foi a última vez que a Maria teve acompanhamento?',
    ],
    parametros: ['pessoa'],
    requerEntidade: (e) => Boolean(e.pessoa),
    resolver: ultimoAcompanhamento,
    criadaEm: '2026-01-10',
    ativa: true,
  },
  {
    id: 'atividades_periodo',
    rotulo: 'Atividades realizadas em um período',
    exemplos: [
      'Quais atividades foram realizadas neste mês?',
      'O que foi feito nos últimos 30 dias?',
      'Quais atividades aconteceram este mês?',
    ],
    parametros: ['periodo'],
    requerEntidade: (e) => Boolean(e.periodo),
    resolver: atividadesNoPeriodo,
    criadaEm: '2026-01-10',
    ativa: true,
  },
  {
    id: 'pessoas_sem_acompanhamento',
    rotulo: 'Quem está sem acompanhamento há um período',
    exemplos: [
      'Quem está sem acompanhamento há determinado período?',
      'Quem está sem acompanhamento há 30 dias?',
      'Quais pessoas não têm acompanhamento recente?',
    ],
    parametros: ['diasLimite?'],
    requerEntidade: () => true,
    resolver: pessoasSemAcompanhamento,
    criadaEm: '2026-01-10',
    ativa: true,
  },
  {
    id: 'onde_cadastrar_informacao',
    rotulo: 'Onde está cadastrada uma informação',
    exemplos: [
      'Onde está cadastrada determinada informação?',
      'Onde fica o telefone de contato?',
      'Onde está cadastrado o convênio?',
    ],
    parametros: ['termoLivre'],
    requerEntidade: () => true,
    resolver: ondeCadastrarInformacao,
    criadaEm: '2026-01-10',
    ativa: true,
  },
  {
    id: 'onde_fazer_procedimento',
    rotulo: 'Onde fazer um procedimento',
    exemplos: [
      'Onde faço determinado procedimento?',
      'Onde faço o cadastro de um novo paciente?',
      'Onde registro um acompanhamento?',
    ],
    parametros: ['termoLivre'],
    requerEntidade: () => true,
    resolver: ondeFazerProcedimento,
    criadaEm: '2026-01-10',
    ativa: true,
  },
  {
    id: 'realizado_em_data',
    rotulo: 'O que foi realizado em um dia específico',
    exemplos: [
      'O que foi realizado em determinado dia?',
      'O que aconteceu no dia 03/09?',
      'O que foi feito hoje?',
    ],
    parametros: ['data'],
    requerEntidade: (e) => Boolean(e.data),
    resolver: oQueFoiRealizadoEmData,
    criadaEm: '2026-01-10',
    ativa: true,
  },
  {
    id: 'quando_aconteceu_evento',
    rotulo: 'Quando aconteceu um evento',
    exemplos: [
      'Quando aconteceu determinado evento?',
      'Quando foi o último evento do João?',
    ],
    parametros: ['pessoa'],
    requerEntidade: (e) => Boolean(e.pessoa),
    resolver: quandoAconteceuEvento,
    criadaEm: '2026-01-10',
    ativa: true,
  },
  {
    id: 'datas_sem_acompanhamento',
    rotulo: 'Quais datas ficaram sem acompanhamento',
    exemplos: [
      'Quais datas ficaram sem acompanhamento?',
      'Quais dias não tiveram acompanhamento este mês?',
    ],
    parametros: ['periodo'],
    requerEntidade: (e) => Boolean(e.periodo),
    resolver: datasSemAcompanhamento,
    criadaEm: '2026-01-10',
    ativa: true,
  },
];
