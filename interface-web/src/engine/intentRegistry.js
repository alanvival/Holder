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
import { dateResponse, listResponse, locationResponse, notFoundResponse, formatDatePt, formatMesPt } from './responseFormat.js';
import {
  extrairClienteId,
  buscarCliente,
  buscarSituacao,
  atendimentosDoCliente,
  ultimoNpsRespondido,
  calcularIndiceAlerta,
  clientesAtivos,
  situacaoClientes,
  clientesEmAlerta,
} from '../data/inovaappsDatabase.js';
import { METRICAS, criarIntentDeMetrica } from './metricas.js';

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

// --- Resolvers da base real do Desafio INOVAAPPS (carteira de clientes) ---

function situacaoEAlertaDoCliente(entidades) {
  const { clienteId } = entidades;
  if (!clienteId) return notFoundResponse();
  const situacao = buscarSituacao(clienteId);
  if (!situacao) return notFoundResponse();

  const itens = [{ label: `Situação: ${situacao.situacao}` }];
  if (situacao.situacao === 'Cancelado' && situacao.mes_cancelamento) {
    itens.push({ label: `Cancelou em: ${formatMesPt(situacao.mes_cancelamento)}` });
  }

  const alerta = calcularIndiceAlerta(clienteId);
  if (alerta) {
    itens.push({ label: `Índice de alerta: ${alerta.nivel} (${formatMesPt(alerta.mesRef)})` });
    if (alerta.sinais.length > 0) {
      itens.push(...alerta.sinais.map((s) => ({ label: `Sinal: ${s}` })));
    }
  }

  return listResponse(`Situação do cliente ${clienteId}:`, itens);
}

function dadosCadastraisCliente(entidades) {
  const { clienteId } = entidades;
  if (!clienteId) return notFoundResponse();
  const cliente = buscarCliente(clienteId);
  if (!cliente) return notFoundResponse();

  return listResponse(`Dados cadastrais do cliente ${clienteId}:`, [
    { label: `Segmento: ${cliente.segmento}` },
    { label: `Porte: ${cliente.porte}` },
    { label: `Plano: ${cliente.plano}` },
    { label: `Valor mensal: R$ ${cliente.valor_mensal.toLocaleString('pt-BR')}` },
    { label: `SLA contratado: ${cliente.sla_contratado_h}h` },
    { label: `Início do contrato: ${formatDatePt(cliente.inicio_contrato)}` },
  ]);
}

function indicadoresRecentesCliente(entidades) {
  const { clienteId } = entidades;
  if (!clienteId) return notFoundResponse();
  const historico = atendimentosDoCliente(clienteId);
  if (historico.length === 0) return notFoundResponse();
  const atual = historico[historico.length - 1];

  return listResponse(`Indicadores do cliente ${clienteId} em ${formatMesPt(atual.mes_ref)}:`, [
    { label: `SLA cumprido: ${atual.pct_sla_cumprido ?? '—'}%` },
    { label: `Uso da plataforma: ${atual.uso_plataforma_pct}%` },
    { label: `Atraso de pagamento: ${atual.dias_atraso_pagamento} dia(s)` },
    { label: `Chamados críticos: ${atual.chamados_criticos}` },
    { label: `Chamados reabertos: ${atual.chamados_reabertos}` },
  ]);
}

function ultimoNpsCliente(entidades) {
  const { clienteId } = entidades;
  if (!clienteId) return notFoundResponse();
  const nps = ultimoNpsRespondido(clienteId);
  if (!nps) return notFoundResponse();
  return listResponse(`Último NPS respondido pelo cliente ${clienteId}:`, [
    { label: `Nota: ${nps.nota_nps}` },
    { label: `Classificação: ${nps.classificacao_nps}` },
    { label: `Mês da pesquisa: ${formatMesPt(nps.mes_ref)}` },
  ]);
}

function contagemCarteira() {
  const total = situacaoClientes.length;
  const cancelados = situacaoClientes.filter((s) => s.situacao === 'Cancelado').length;
  const ativos = clientesAtivos().length;
  return listResponse('Situação geral da carteira:', [
    { label: `Total de clientes: ${total}` },
    { label: `Ativos: ${ativos}` },
    { label: `Cancelados: ${cancelados}` },
  ]);
}

function clientesEmAlertaAlto() {
  const lista = clientesEmAlerta('Alto');
  if (lista.length === 0) return notFoundResponse();
  return listResponse(`${lista.length} cliente(s) ativo(s) com índice de alerta Alto agora:`, lista.map((c) => ({ label: c.clienteId })));
}

// Extrator de entidades comum a todas as intenções — roda antes do resolver.
export function extrairEntidades(texto, hoje) {
  return {
    pessoa: extractPerson(texto, pessoas),
    periodo: extractPeriod(texto, hoje),
    data: extractDate(texto, hoje),
    clienteId: extrairClienteId(texto),
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

  // --- Carteira de clientes do Desafio INOVAAPPS (Pulso) ---
  {
    id: 'situacao_alerta_cliente',
    rotulo: 'Situação e índice de alerta de um cliente',
    exemplos: [
      'Qual a situação do cliente C007?',
      'O cliente C030 está em risco?',
      'O cliente C012 cancelou?',
      'Qual o risco do cliente C045 agora?',
    ],
    // Perguntas com essas palavras são sobre o SCORE DE RISCO (% de
    // probabilidade de um modelo treinado, ver
    // holder/aplicacao/assistente/previsao_risco.py) — não o índice de
    // alerta deste intent (calcularIndiceAlerta, baseline do próprio
    // cliente). Sem essa exclusão, o casamento por
    // similaridade de palavras ("qual", "risco", "cliente") capturava
    // "qual o risco DE CANCELAMENTO do cliente X" antes de chegar na IA
    // — bug reportado ao vivo pelo usuário.
    palavrasExcludentes: ['cancelamento', 'cancelar', 'probabilidade', 'previsão', 'previsao', 'prever', 'preditivo', 'preditiva', 'futuro'],
    parametros: ['clienteId'],
    requerEntidade: (e) => Boolean(e.clienteId),
    resolver: situacaoEAlertaDoCliente,
    criadaEm: '2026-09-19',
    ativa: true,
  },
  {
    id: 'dados_cadastrais_cliente',
    rotulo: 'Dados cadastrais de um cliente',
    exemplos: [
      'Quais os dados cadastrais do cliente C007?',
      'Qual o plano do cliente C020?',
      'Qual o valor mensal do cliente C011?',
      'Qual o segmento do cliente C055?',
    ],
    parametros: ['clienteId'],
    requerEntidade: (e) => Boolean(e.clienteId),
    resolver: dadosCadastraisCliente,
    criadaEm: '2026-09-19',
    ativa: true,
  },
  {
    id: 'indicadores_recentes_cliente',
    rotulo: 'Indicadores recentes de um cliente',
    exemplos: [
      'Como está o SLA do cliente C007?',
      'Qual o uso da plataforma do cliente C030 no último mês?',
      'O cliente C012 está com pagamento atrasado?',
      'Quantos chamados críticos o cliente C045 teve?',
    ],
    parametros: ['clienteId'],
    requerEntidade: (e) => Boolean(e.clienteId),
    resolver: indicadoresRecentesCliente,
    criadaEm: '2026-09-19',
    ativa: true,
  },
  {
    id: 'ultimo_nps_cliente',
    rotulo: 'Último NPS de um cliente',
    exemplos: [
      'Qual foi o último NPS do cliente C007?',
      'Qual a nota do cliente C020 na última pesquisa?',
      'O cliente C012 é promotor ou detrator?',
    ],
    parametros: ['clienteId'],
    requerEntidade: (e) => Boolean(e.clienteId),
    resolver: ultimoNpsCliente,
    criadaEm: '2026-09-19',
    ativa: true,
  },
  {
    id: 'contagem_carteira',
    rotulo: 'Quantos clientes ativos/cancelados',
    exemplos: [
      'Quantos clientes cancelaram?',
      'Quantos clientes estão ativos?',
      'Qual o tamanho da carteira?',
    ],
    parametros: [],
    requerEntidade: () => true,
    resolver: contagemCarteira,
    criadaEm: '2026-09-19',
    ativa: true,
  },
  {
    id: 'clientes_risco_alto',
    rotulo: 'Quais clientes estão em risco alto',
    exemplos: [
      'Quais clientes estão em risco alto?',
      'Quem eu deveria ligar primeiro hoje?',
      'Quais clientes ativos estão em risco alto agora?',
    ],
    parametros: [],
    requerEntidade: () => true,
    resolver: clientesEmAlertaAlto,
    criadaEm: '2026-09-19',
    ativa: true,
  },

  // --- Métricas agregadas: cada definição em METRICAS (metricas.js) vira
  // uma intenção aqui via criarIntentDeMetrica — nenhum resolver bespoke,
  // todas passam pelo mesmo resolverMetricaGenerico. ---
  ...METRICAS.map(criarIntentDeMetrica),
];

// ---------------------------------------------------------------------
// Gestão de intenções (item 2 do prompt de continuação): o admin cadastra
// novas perguntas-chave em runtime. Intenções nascidas aqui não têm um
// resolver programado — respondem com o texto-modelo definido pelo admin,
// sem extração dinâmica de entidades. É uma simplificação deliberada: dar
// inteligência real a uma intenção nova (like ultimoAcompanhamento) exige
// código, então isso continua sendo trabalho de dev; o que o admin controla
// aqui é o vocabulário (frases de exemplo) e o texto de resposta.

let proximoIdPersonalizado = 1;

function novoIdPersonalizado() {
  return `intent-admin-${proximoIdPersonalizado++}`;
}

export function registrarIntentPersonalizada({ id, rotulo, exemplos, respostaTexto, ativa = true, criadaEm }) {
  // `id` explícito é usado ao hidratar perguntas que já existem no backend
  // (armazenamento.py) — evita duplicar a mesma pergunta ao registrar de
  // novo em cada fetch/reload. Sem `id`, gera um novo (fluxo 100% local,
  // sem backend).
  if (id && intentRegistry.some((i) => i.id === id)) {
    return intentRegistry.find((i) => i.id === id);
  }
  const intent = {
    id: id ?? novoIdPersonalizado(),
    rotulo,
    exemplos,
    parametros: [],
    requerEntidade: () => true,
    resolver: () => ({ kind: 'text', text: respostaTexto }),
    criadaEm: criadaEm ?? new Date().toISOString(),
    ativa,
    origem: 'admin',
  };
  intentRegistry.push(intent);
  return intent;
}

export function listarIntents() {
  return intentRegistry.map((intent) => ({ ...intent, origem: intent.origem ?? 'sistema' }));
}

export function desativarIntent(id) {
  const intent = intentRegistry.find((i) => i.id === id);
  if (intent) intent.ativa = false;
}
