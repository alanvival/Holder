// Motor genérico de métricas agregadas — segunda família de perguntas do
// Assistente de Consultas, ao lado das intenções de "consulta de registro"
// em intentRegistry.js.
//
// A regra de arquitetura (do prompt de métricas): não implementar cada
// métrica como um `if` novo. Uma métrica é só uma DEFINIÇÃO —
//   { id, rotulo, sinonimos, aba, agregacao, campo(s), formato, ... }
// — resolvida por um único `resolverMetricaGenerico`. Adicionar a métrica
// 15 é acrescentar uma definição em METRICAS, nunca escrever um resolver
// novo. `criarIntentDeMetrica` pluga cada definição no mesmo motor de
// similaridade que já resolve as intenções de registro (intentRegistry.js),
// reaproveitando 100% da extração de cliente_id e do matching por texto.

import {
  clientes,
  atendimentoMensal,
  pesquisasNps,
  situacaoClientes,
  planoDoCliente,
  porteDoCliente,
  segmentoDoCliente,
  situacaoDoCliente,
  PLANOS,
  PORTES,
  SEGMENTOS,
  PLANO_LABELS,
  PORTE_LABELS,
  SEGMENTO_LABELS,
  PRIMEIRO_MES_DADOS,
  ULTIMO_MES_DADOS,
} from '../data/inovaappsDatabase.js';
import {
  metricResponse,
  listResponse,
  notFoundResponse,
  formatMoeda,
  formatHoras,
  formatPercentual,
  formatDias,
  formatNumeroDecimal,
  formatInteiro,
  formatMesPt,
} from './responseFormat.js';

// --- Extração de recortes a partir do texto da pergunta -------------------

function normalizar(texto) {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}

function extrairPlano(texto) {
  const norm = normalizar(texto);
  if (/\bessencial\b/.test(norm)) return 'Essencial';
  if (/\bavan[cç]ado\b/.test(norm)) return 'Avancado';
  if (/\benterprise\b/.test(norm)) return 'Enterprise';
  return null;
}

// "medio"/"grande"/"pequeno" colidem com vocabulário comum ("tempo médio",
// "em média") — só filtra por porte quando a palavra "porte" aparece do
// lado, nunca por substring solta.
function extrairPorte(texto) {
  const norm = normalizar(texto);
  const match = norm.match(/\bporte\s+(pequeno|medio|grande)\b/) || norm.match(/\b(pequeno|medio|grande)\s+porte\b/);
  if (!match) return null;
  const valor = match[1];
  return valor === 'pequeno' ? 'Pequeno' : valor === 'medio' ? 'Medio' : 'Grande';
}

function extrairSegmento(texto) {
  const norm = normalizar(texto);
  const mapa = {
    logistica: 'Logistica',
    saude: 'Saude',
    educacao: 'Educacao',
    industria: 'Industria',
    varejo: 'Varejo',
    servicos: 'Servicos',
  };
  for (const [chave, valor] of Object.entries(mapa)) {
    if (new RegExp(`\\b${chave}\\b`).test(norm)) return valor;
  }
  return null;
}

function extrairSituacao(texto) {
  const norm = normalizar(texto);
  if (/\bcancelad/.test(norm)) return 'Cancelado';
  if (/\bativ/.test(norm)) return 'Ativo';
  return null;
}

function extrairBreakdown(texto) {
  const norm = normalizar(texto);
  if (/\bpor\s+plano\b/.test(norm)) return 'plano';
  if (/\bpor\s+porte\b/.test(norm)) return 'porte';
  if (/\bpor\s+segmento\b/.test(norm)) return 'segmento';
  return null;
}

const NOMES_MES = {
  janeiro: '01', fevereiro: '02', marco: '03', abril: '04', maio: '05', junho: '06',
  julho: '07', agosto: '08', setembro: '09', outubro: '10', novembro: '11', dezembro: '12',
};

// Período mira sempre mes_ref ("AAAA-MM"), diferente do extractPeriod de
// entities.js (que mira datas de dia). "últimos N meses" é relativo ao fim
// real dos dados (ULTIMO_MES_DADOS = 2026-06), não à data de calendário —
// a base não tem linhas depois disso.
function extrairPeriodo(texto) {
  const norm = normalizar(texto);

  const explicito = texto.match(/\b(0?[1-9]|1[0-2])\/(20\d{2})\b/);
  if (explicito) {
    const ref = `${explicito[2]}-${explicito[1].padStart(2, '0')}`;
    return { start: ref, end: ref, rotulo: formatMesPt(ref) };
  }

  for (const [nome, numero] of Object.entries(NOMES_MES)) {
    if (norm.includes(nome)) {
      const ano = texto.match(/\b(20\d{2})\b/);
      if (!ano) return null; // mês sem ano é ambíguo entre 2025/2026 — não filtra
      const ref = `${ano[1]}-${numero}`;
      return { start: ref, end: ref, rotulo: formatMesPt(ref) };
    }
  }

  const ultimosN = norm.match(/ultimos?\s+(\d+)\s+meses/);
  if (ultimosN) {
    const n = Number(ultimosN[1]);
    const [anoFim, mesFim] = ULTIMO_MES_DADOS.split('-').map(Number);
    const inicio = new Date(anoFim, mesFim - 1 - (n - 1), 1);
    const ref = `${inicio.getFullYear()}-${String(inicio.getMonth() + 1).padStart(2, '0')}`;
    return { start: ref, end: ULTIMO_MES_DADOS, rotulo: `últimos ${n} meses` };
  }

  const anoIsolado = texto.match(/\b(20\d{2})\b/);
  if (anoIsolado) {
    return { start: `${anoIsolado[1]}-01`, end: `${anoIsolado[1]}-12`, rotulo: anoIsolado[1] };
  }

  return null;
}

export function extrairRecortes(texto, clienteId) {
  return {
    clienteId: clienteId ?? null,
    plano: extrairPlano(texto),
    porte: extrairPorte(texto),
    segmento: extrairSegmento(texto),
    situacao: extrairSituacao(texto),
    periodo: extrairPeriodo(texto),
    breakdownPor: extrairBreakdown(texto),
  };
}

// --- Filtragem: aplica os recortes contra a aba de origem da métrica -----

const ABAS = {
  clientes,
  atendimento_mensal: atendimentoMensal,
  pesquisas_nps: pesquisasNps,
  situacao_clientes: situacaoClientes,
};

function atendeRecortesDeCliente(clienteId, recortes) {
  if (recortes.clienteId && clienteId !== recortes.clienteId) return false;
  if (recortes.plano && planoDoCliente(clienteId) !== recortes.plano) return false;
  if (recortes.porte && porteDoCliente(clienteId) !== recortes.porte) return false;
  if (recortes.segmento && segmentoDoCliente(clienteId) !== recortes.segmento) return false;
  if (recortes.situacao && situacaoDoCliente(clienteId) !== recortes.situacao) return false;
  return true;
}

function abaTemPeriodo(aba) {
  return aba === 'atendimento_mensal' || aba === 'pesquisas_nps';
}

function filtrarLinhas(aba, recortes) {
  const base = ABAS[aba];
  return base.filter((linha) => {
    if (!atendeRecortesDeCliente(linha.cliente_id, recortes)) return false;
    if (recortes.periodo && abaTemPeriodo(aba)) {
      if (linha.mes_ref < recortes.periodo.start || linha.mes_ref > recortes.periodo.end) return false;
    }
    return true;
  });
}

function clientesDistintos(linhas) {
  return new Set(linhas.map((l) => l.cliente_id)).size;
}

// "Toda resposta agregada declara o universo considerado" (regra 4 do
// prompt) — nunca um número solto.
function descreverUniverso(recortes, linhas, aba) {
  const partes = [`${clientesDistintos(linhas)} cliente(s)`];
  if (recortes.plano) partes.push(`plano ${PLANO_LABELS[recortes.plano]}`);
  if (recortes.porte) partes.push(`porte ${PORTE_LABELS[recortes.porte]}`);
  if (recortes.segmento) partes.push(`segmento ${SEGMENTO_LABELS[recortes.segmento]}`);
  if (recortes.situacao) partes.push(recortes.situacao === 'Ativo' ? 'ativos' : 'cancelados');
  if (recortes.clienteId) partes.push(`cliente ${recortes.clienteId}`);

  let descricao = `Considerando ${partes.join(', ')}`;
  if (abaTemPeriodo(aba)) {
    descricao += recortes.periodo
      ? `, ${recortes.periodo.rotulo}`
      : `, de ${formatMesPt(PRIMEIRO_MES_DADOS)} a ${formatMesPt(ULTIMO_MES_DADOS)}`;
  }
  return `${descricao}.`;
}

function escopoRotulo(recortes) {
  return recortes.clienteId ? `do cliente ${recortes.clienteId}` : 'da carteira';
}

// --- Agregação genérica: uma métrica declara `agregacao` e o dispatcher
// abaixo faz a conta. Novas formas de calcular (se um dia precisar) entram
// aqui uma vez só, não por métrica. ----------------------------------------

function agregar(def, linhasBrutas) {
  const linhas = def.filtroLinha ? linhasBrutas.filter(def.filtroLinha) : linhasBrutas;

  switch (def.agregacao) {
    case 'media': {
      const valores = linhas.map((r) => r[def.campo]).filter((v) => v !== null && v !== undefined);
      if (valores.length === 0) return null;
      return valores.reduce((s, v) => s + v, 0) / valores.length;
    }
    case 'media_ponderada': {
      let numerador = 0;
      let denominador = 0;
      for (const r of linhas) {
        const peso = r[def.campoPeso];
        const valor = r[def.campo];
        if (!peso || valor === null || valor === undefined) continue;
        numerador += valor * peso;
        denominador += peso;
      }
      return denominador === 0 ? null : numerador / denominador;
    }
    case 'razao_soma': {
      let numerador = 0;
      let denominador = 0;
      for (const r of linhas) {
        numerador += r[def.campoNumerador] ?? 0;
        denominador += r[def.campoDenominador] ?? 0;
      }
      return denominador === 0 ? null : numerador / denominador;
    }
    case 'proporcao_linhas': {
      if (linhas.length === 0) return null;
      return linhas.filter(def.predicado).length / linhas.length;
    }
    case 'soma': {
      const valores = linhas.map((r) => r[def.campo]).filter((v) => v !== null && v !== undefined);
      return valores.reduce((s, v) => s + v, 0);
    }
    default:
      return null;
  }
}

// NPS é genuinamente diferente (score = %promotores − %detratores sobre
// quem respondeu; nota média excluindo quem não respondeu) — é a única
// métrica com cálculo bespoke, mas ainda entra no registro como as outras.
function calcularNps(linhas) {
  const respondidas = linhas.filter((n) => n.respondeu === 1);
  if (respondidas.length === 0) return null;
  const promotores = respondidas.filter((n) => n.classificacao_nps === 'Promotor').length;
  const detratores = respondidas.filter((n) => n.classificacao_nps === 'Detrator').length;
  return {
    score: ((promotores - detratores) / respondidas.length) * 100,
    notaMedia: respondidas.reduce((s, n) => s + n.nota_nps, 0) / respondidas.length,
    respondidas: respondidas.length,
    convites: linhas.length,
  };
}

function formatarValor(formato, valor) {
  switch (formato) {
    case 'moeda': return formatMoeda(valor);
    case 'horas': return formatHoras(valor);
    case 'percentual': return formatPercentual(valor);
    case 'dias': return formatDias(valor);
    case 'numero': return formatNumeroDecimal(valor);
    case 'inteiro': return formatInteiro(valor);
    default: return String(valor);
  }
}

function labelCategoria(dimensao, valor) {
  if (dimensao === 'plano') return PLANO_LABELS[valor];
  if (dimensao === 'porte') return PORTE_LABELS[valor];
  return SEGMENTO_LABELS[valor];
}

function categoriasDe(dimensao) {
  if (dimensao === 'plano') return PLANOS;
  if (dimensao === 'porte') return PORTES;
  return SEGMENTOS;
}

// --- Definições de métrica --------------------------------------------
// { id, rotulo, sinonimos, aba, agregacao, formato, ...específicos }
// `escala100`: agregações razao_soma/proporcao_linhas devolvem fração
// 0..1 — métricas percentuais baseadas nelas precisam de *100 antes de
// formatar; médias de campos que já são 0-100 (pct_sla_cumprido,
// uso_plataforma_pct) não.

export const METRICAS = [
  {
    id: 'ticket_medio',
    rotulo: 'Ticket médio',
    sinonimos: [
      'Qual o ticket médio da carteira?',
      'Qual o ticket médio dos clientes?',
      'Qual o valor médio dos contratos?',
      'Qual o ticket médio por plano?',
    ],
    aba: 'clientes',
    agregacao: 'media',
    campo: 'valor_mensal',
    formato: 'moeda',
  },
  {
    id: 'tempo_medio_resolucao',
    rotulo: 'Tempo médio de resolução',
    sinonimos: [
      'Qual o tempo médio de resolução dos chamados?',
      'Quanto tempo leva pra resolver um chamado em média?',
      'Qual o tempo médio de resolução da carteira?',
    ],
    aba: 'atendimento_mensal',
    agregacao: 'media_ponderada',
    campo: 'tempo_medio_resolucao_h',
    campoPeso: 'chamados_abertos',
    // Linhas sem chamado (chamados_abertos = 0) carregam um valor residual
    // de tempo que não representa nada real — excluir antes de agregar.
    filtroLinha: (r) => r.chamados_abertos > 0,
    formato: 'horas',
    leituraAlternativa: { agregacao: 'media', rotulo: 'média simples (sem ponderar pelo volume de chamados)' },
  },
  {
    id: 'media_reclamacoes',
    rotulo: 'Média de reclamações',
    sinonimos: [
      'Qual a média de reclamações por mês?',
      'Quantas reclamações formais em média os clientes fazem?',
      'Qual a média de reclamações da carteira?',
    ],
    aba: 'atendimento_mensal',
    agregacao: 'media',
    campo: 'reclamacoes_formais',
    formato: 'numero',
    contextoExtra: (linhas) => {
      const total = linhas.reduce((s, r) => s + (r.reclamacoes_formais ?? 0), 0);
      const comAlguma = linhas.filter((r) => r.reclamacoes_formais > 0).length;
      return `Total no período: ${formatInteiro(total)} reclamação(ões), em ${comAlguma} de ${linhas.length} meses.`;
    },
  },
  {
    id: 'atraso_medio_pagamento',
    rotulo: 'Atraso médio de pagamento',
    sinonimos: [
      'Qual o atraso médio de pagamento?',
      'Em média quantos dias os clientes atrasam o pagamento?',
      'Qual o atraso médio de pagamento da carteira?',
    ],
    aba: 'atendimento_mensal',
    agregacao: 'media',
    campo: 'dias_atraso_pagamento',
    formato: 'dias',
    contextoExtra: (linhas) => {
      const comAtraso = linhas.filter((r) => r.dias_atraso_pagamento > 0);
      const pct = linhas.length > 0 ? (comAtraso.length / linhas.length) * 100 : 0;
      const mediaComAtraso = comAtraso.length > 0
        ? comAtraso.reduce((s, r) => s + r.dias_atraso_pagamento, 0) / comAtraso.length
        : null;
      let texto = `${comAtraso.length} de ${linhas.length} meses com algum atraso (${formatPercentual(pct)})`;
      if (mediaComAtraso !== null) texto += `, média de ${formatDias(mediaComAtraso)} nesses meses`;
      return `${texto}. O campo é o maior atraso do mês, não um acumulado.`;
    },
  },
  {
    id: 'sla_cumprido',
    rotulo: 'SLA cumprido',
    sinonimos: [
      'Qual o SLA cumprido da carteira?',
      'Qual o percentual de SLA cumprido?',
      'Qual a taxa de SLA da carteira?',
    ],
    aba: 'atendimento_mensal',
    agregacao: 'razao_soma',
    campoNumerador: 'chamados_dentro_sla',
    campoDenominador: 'chamados_abertos',
    filtroLinha: (r) => r.chamados_abertos > 0,
    escala100: true,
    formato: 'percentual',
    leituraAlternativa: { agregacao: 'media', campo: 'pct_sla_cumprido', rotulo: 'média simples do percentual mensal já calculado' },
  },
  {
    id: 'taxa_cancelamento',
    rotulo: 'Taxa de cancelamento (churn)',
    sinonimos: [
      'Qual a taxa de cancelamento?',
      'Qual o churn da carteira?',
      'Quantos por cento dos clientes cancelaram?',
    ],
    aba: 'situacao_clientes',
    agregacao: 'proporcao_linhas',
    predicado: (r) => r.situacao === 'Cancelado',
    escala100: true,
    formato: 'percentual',
  },
  {
    id: 'uso_medio_plataforma',
    rotulo: 'Uso médio da plataforma',
    sinonimos: [
      'Qual o uso médio da plataforma?',
      'Qual o percentual médio de uso da plataforma?',
    ],
    aba: 'atendimento_mensal',
    agregacao: 'media',
    campo: 'uso_plataforma_pct',
    formato: 'percentual',
  },
  {
    id: 'reunioes_realizadas',
    rotulo: 'Reuniões realizadas',
    sinonimos: [
      'Qual o percentual de reuniões realizadas?',
      'Quantas reuniões previstas foram realizadas?',
    ],
    aba: 'atendimento_mensal',
    agregacao: 'razao_soma',
    campoNumerador: 'reunioes_realizadas',
    campoDenominador: 'reunioes_previstas',
    escala100: true,
    formato: 'percentual',
  },
  {
    id: 'chamados_criticos',
    rotulo: 'Chamados críticos',
    sinonimos: [
      'Quantos chamados críticos no total?',
      'Qual a média de chamados críticos por cliente?',
    ],
    aba: 'atendimento_mensal',
    agregacao: 'soma',
    campo: 'chamados_criticos',
    formato: 'inteiro',
    contextoExtra: (linhas) => {
      const total = linhas.reduce((s, r) => s + (r.chamados_criticos ?? 0), 0);
      const media = linhas.length > 0 ? total / linhas.length : 0;
      return `Média de ${formatNumeroDecimal(media)} por cliente-mês.`;
    },
  },
  {
    id: 'taxa_reabertura',
    rotulo: 'Taxa de reabertura',
    sinonimos: [
      'Qual a taxa de reabertura de chamados?',
      'Qual o percentual de chamados reabertos?',
    ],
    aba: 'atendimento_mensal',
    agregacao: 'razao_soma',
    campoNumerador: 'chamados_reabertos',
    campoDenominador: 'chamados_abertos',
    filtroLinha: (r) => r.chamados_abertos > 0,
    escala100: true,
    formato: 'percentual',
  },
  {
    id: 'nps_carteira',
    rotulo: 'NPS',
    sinonimos: [
      'Qual o NPS da carteira?',
      'Qual o score de NPS?',
      'Qual a nota média de NPS?',
    ],
    aba: 'pesquisas_nps',
    agregacao: 'nps',
    formato: 'nps',
  },
];

const METRICAS_POR_ID = new Map(METRICAS.map((m) => [m.id, m]));

// --- Resolvedor genérico — o único ponto que sabe calcular qualquer
// métrica do registro acima. -----------------------------------------

export function resolverMetricaGenerico(metricaId, texto, clienteIdExtraido) {
  const def = METRICAS_POR_ID.get(metricaId);
  if (!def) return notFoundResponse();

  const recortes = extrairRecortes(texto, clienteIdExtraido);

  // "por plano/porte/segmento" sem valor específico = pedido de breakdown:
  // uma linha por categoria, em vez de um único número.
  if (recortes.breakdownPor && !recortes[recortes.breakdownPor]) {
    const dimensao = recortes.breakdownPor;
    const itens = [];
    for (const categoria of categoriasDe(dimensao)) {
      const recortesCategoria = { ...recortes, [dimensao]: categoria, breakdownPor: null };
      const linhas = filtrarLinhas(def.aba, recortesCategoria);
      if (linhas.length === 0) continue;
      const valorBruto = def.agregacao === 'nps' ? calcularNps(linhas)?.notaMedia ?? null : agregar(def, linhas);
      if (valorBruto === null) continue;
      const valor = def.escala100 ? valorBruto * 100 : valorBruto;
      itens.push({ label: `${labelCategoria(dimensao, categoria)}: ${formatarValor(def.formato, valor)}` });
    }
    if (itens.length === 0) return notFoundResponse();
    return listResponse(`${def.rotulo} por ${dimensao}:`, itens);
  }

  const linhas = filtrarLinhas(def.aba, recortes);
  if (linhas.length === 0) return notFoundResponse();

  if (def.agregacao === 'nps') {
    const resultado = calcularNps(linhas);
    if (!resultado) return notFoundResponse();
    let contexto = descreverUniverso(recortes, linhas, def.aba);
    contexto += ` ${resultado.respondidas} de ${resultado.convites} convites respondidos.`;
    const scoreTexto = formatNumeroDecimal(resultado.score, 1);
    return metricResponse(
      `${def.rotulo} ${escopoRotulo(recortes)}:`,
      `${scoreTexto} (nota média ${formatNumeroDecimal(resultado.notaMedia)})`,
      contexto,
    );
  }

  const valorBruto = agregar(def, linhas);
  if (valorBruto === null) return notFoundResponse();
  const valor = def.escala100 ? valorBruto * 100 : valorBruto;
  const destaque = formatarValor(def.formato, valor);

  let contexto = descreverUniverso(recortes, linhas, def.aba);

  if (def.leituraAlternativa) {
    const defAlternativa = { ...def, ...def.leituraAlternativa };
    const valorAltBruto = agregar(defAlternativa, linhas);
    if (valorAltBruto !== null) {
      const valorAlt = def.escala100 ? valorAltBruto * 100 : valorAltBruto;
      contexto += ` Usei a leitura ponderada (padrão); a ${def.leituraAlternativa.rotulo} dá ${formatarValor(def.formato, valorAlt)}.`;
    }
  }

  if (def.contextoExtra) {
    contexto += ` ${def.contextoExtra(linhas)}`;
  }

  return metricResponse(`${def.rotulo} ${escopoRotulo(recortes)}:`, destaque, contexto);
}

// Hook de baixo nível pra testes (scripts/testar-metricas.mjs): calcula o
// valor bruto (sem formatação) a partir de recortes já estruturados, sem
// precisar fabricar frases em português pra cada caso de teste.
export function calcularValorBrutoParaTeste(metricaId, recortesParciais = {}) {
  const def = METRICAS_POR_ID.get(metricaId);
  if (!def) return null;
  const recortes = { clienteId: null, plano: null, porte: null, segmento: null, situacao: null, periodo: null, breakdownPor: null, ...recortesParciais };
  const linhas = filtrarLinhas(def.aba, recortes);
  if (linhas.length === 0) return null;
  if (def.agregacao === 'nps') return calcularNps(linhas);
  const valorBruto = agregar(def, linhas);
  if (valorBruto === null) return null;
  return def.escala100 ? valorBruto * 100 : valorBruto;
}

// Pluga cada definição de métrica no mesmo motor de intenções (similaridade
// + extração de cliente_id) que já resolve as perguntas de registro —
// cadastrar a métrica 15 não exige tocar em mais nada além de METRICAS.
export function criarIntentDeMetrica(def) {
  return {
    id: def.id,
    rotulo: def.rotulo,
    exemplos: def.sinonimos,
    parametros: ['clienteId?', 'recortes?'],
    requerEntidade: () => true,
    resolver: (entidades) => resolverMetricaGenerico(def.id, entidades.termoLivre, entidades.clienteId),
    criadaEm: '2026-09-19',
    ativa: true,
  };
}
