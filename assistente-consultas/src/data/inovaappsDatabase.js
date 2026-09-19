// Base de dados real do Desafio INOVAAPPS 2026 (planilha
// INOVAAPPS_base_de_dados.xlsx, convertida para JSON por
// scripts/gerar_dados_inovaapps.py). Substitui/complementa a base mock
// genérica em mockDatabase.js para as perguntas relacionadas à carteira de
// clientes do desafio Pulso.

import clientesRaw from './inovaapps/clientes.json';
import atendimentoMensalRaw from './inovaapps/atendimentoMensal.json';
import pesquisasNpsRaw from './inovaapps/pesquisasNps.json';
import situacaoClientesRaw from './inovaapps/situacaoClientes.json';

export const clientes = clientesRaw;
export const atendimentoMensal = atendimentoMensalRaw;
export const pesquisasNps = pesquisasNpsRaw;
export const situacaoClientes = situacaoClientesRaw;

const clientesPorId = new Map(clientes.map((c) => [c.cliente_id, c]));
const situacaoPorId = new Map(situacaoClientes.map((s) => [s.cliente_id, s]));

export function buscarCliente(clienteId) {
  return clientesPorId.get(clienteId) ?? null;
}

export function buscarSituacao(clienteId) {
  return situacaoPorId.get(clienteId) ?? null;
}

export function atendimentosDoCliente(clienteId) {
  return atendimentoMensal
    .filter((a) => a.cliente_id === clienteId)
    .sort((a, b) => (a.mes_ref < b.mes_ref ? -1 : 1));
}

export function atendimentoDoMes(clienteId, mesRef) {
  return atendimentoMensal.find((a) => a.cliente_id === clienteId && a.mes_ref === mesRef) ?? null;
}

export function npsDoCliente(clienteId) {
  return pesquisasNps
    .filter((n) => n.cliente_id === clienteId)
    .sort((a, b) => (a.mes_ref < b.mes_ref ? -1 : 1));
}

export function ultimoNpsRespondido(clienteId) {
  const respostas = npsDoCliente(clienteId).filter((n) => n.respondeu === 1);
  return respostas.length > 0 ? respostas[respostas.length - 1] : null;
}

// Reconhece um cliente_id (C001..C080) em qualquer lugar do texto,
// case-insensitive e tolerante a espaço entre a letra e o número
// ("cliente c 7", "cliente C7" -> C007).
export function extrairClienteId(texto) {
  const match = texto.match(/\bC\s?0*?(\d{1,3})\b/i);
  if (!match) return null;
  const numero = match[1].padStart(3, '0');
  const id = `C${numero}`;
  return clientesPorId.has(id) ? id : null;
}

// --- Cálculo de risco (mesma lógica de "linha de base do próprio cliente"
// descrita no PDF do desafio Pulso: compara o mês mais recente com a média
// histórica do próprio cliente, não com a carteira) ---------------------

const SINAIS_RISCO_CACHE = new Map();

function media(valores) {
  const validos = valores.filter((v) => v !== null && v !== undefined);
  if (validos.length === 0) return null;
  return validos.reduce((soma, v) => soma + v, 0) / validos.length;
}

/**
 * Calcula quantos dos sinais de risco monitorados pioraram no mês mais
 * recente do cliente em relação à média dos meses anteriores dele mesmo.
 * Retorna null se o cliente não tem histórico suficiente (menos de 2 meses).
 */
export function calcularRisco(clienteId) {
  if (SINAIS_RISCO_CACHE.has(clienteId)) return SINAIS_RISCO_CACHE.get(clienteId);

  const historico = atendimentosDoCliente(clienteId);
  if (historico.length < 2) {
    SINAIS_RISCO_CACHE.set(clienteId, null);
    return null;
  }

  const atual = historico[historico.length - 1];
  const anteriores = historico.slice(0, -1);

  const baselineSla = media(anteriores.map((a) => a.pct_sla_cumprido));
  const baselineUso = media(anteriores.map((a) => a.uso_plataforma_pct));
  const baselineAtraso = media(anteriores.map((a) => a.dias_atraso_pagamento));

  const sinais = [];
  if (baselineSla !== null && atual.pct_sla_cumprido !== null && atual.pct_sla_cumprido < baselineSla - 10) {
    sinais.push('Queda no SLA cumprido');
  }
  if (baselineUso !== null && atual.uso_plataforma_pct < baselineUso - 10) {
    sinais.push('Queda no uso da plataforma');
  }
  if (baselineAtraso !== null && atual.dias_atraso_pagamento > baselineAtraso + 3) {
    sinais.push('Atraso de pagamento crescente');
  }
  if (atual.chamados_criticos >= 2) {
    sinais.push('Mais chamados críticos');
  }
  if (atual.chamados_reabertos >= 2) {
    sinais.push('Mais chamados reabertos');
  }
  if (atual.reunioes_previstas === 1 && atual.reunioes_realizadas === 0) {
    sinais.push('Reunião prevista não realizada');
  }
  if (atual.reclamacoes_formais >= 1) {
    sinais.push('Reclamação formal recente');
  }
  const ultimoNps = ultimoNpsRespondido(clienteId);
  if (ultimoNps && ultimoNps.classificacao_nps === 'Detrator') {
    sinais.push('NPS detrator');
  }

  let nivel = 'Baixo';
  if (sinais.length >= 4) nivel = 'Alto';
  else if (sinais.length >= 2) nivel = 'Médio';

  const resultado = { nivel, sinais, mesRef: atual.mes_ref };
  SINAIS_RISCO_CACHE.set(clienteId, resultado);
  return resultado;
}

export function clientesAtivos() {
  return situacaoClientes.filter((s) => s.situacao === 'Ativo').map((s) => s.cliente_id);
}

export function clientesComRisco(nivel) {
  return clientesAtivos()
    .map((id) => ({ clienteId: id, risco: calcularRisco(id) }))
    .filter((c) => c.risco && c.risco.nivel === nivel);
}
