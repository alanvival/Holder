// Valida o motor de métricas (src/engine/metricas.js) contra os valores de
// referência do prompt de métricas — item 4 do "Entregável": "Testes
// verificando os valores de referência listados acima — se algum bater
// diferente, investigar antes de ajustar o número esperado."
//
// Roda com node puro (o projeto é "type": "module", sem precisar de bundler):
//   node scripts/testar-metricas.mjs

import { calcularValorBrutoParaTeste } from '../src/engine/metricas.js';

let falhas = 0;
let total = 0;

function checar(descricao, valorObtido, valorEsperado, tolerancia = 0.05) {
  total += 1;
  const passou =
    valorObtido !== null &&
    valorObtido !== undefined &&
    Math.abs(valorObtido - valorEsperado) <= tolerancia;
  if (passou) {
    console.log(`OK   ${descricao}: ${valorObtido.toFixed(4)} (esperado ${valorEsperado})`);
  } else {
    falhas += 1;
    console.error(`FAIL ${descricao}: obtido ${valorObtido} — esperado ${valorEsperado}`);
  }
}

// 1. Ticket médio
checar('Ticket médio — base completa (80)', calcularValorBrutoParaTeste('ticket_medio'), 12287.05);
checar('Ticket médio — somente ativos (58)', calcularValorBrutoParaTeste('ticket_medio', { situacao: 'Ativo' }), 12206.86);
checar('Ticket médio — Essencial', calcularValorBrutoParaTeste('ticket_medio', { plano: 'Essencial' }), 3299.14);
checar('Ticket médio — Avançado', calcularValorBrutoParaTeste('ticket_medio', { plano: 'Avancado' }), 10629.96);
checar('Ticket médio — Enterprise', calcularValorBrutoParaTeste('ticket_medio', { plano: 'Enterprise' }), 31111.32);

// 2. Tempo médio de resolução
checar('Tempo médio de resolução — ponderado', calcularValorBrutoParaTeste('tempo_medio_resolucao'), 23.21, 0.1);

// 3. Média de reclamações
checar('Média de reclamações — por cliente-mês', calcularValorBrutoParaTeste('media_reclamacoes'), 0.402, 0.005);

// 4. Atraso médio de pagamento
checar('Atraso médio de pagamento — todas as linhas', calcularValorBrutoParaTeste('atraso_medio_pagamento'), 3.18, 0.05);

// 5. SLA cumprido
checar('SLA cumprido — ponderado (chamados_dentro_sla/chamados_abertos)', calcularValorBrutoParaTeste('sla_cumprido'), 75.96, 0.2);

// 6. NPS (retorna um objeto { score, notaMedia, ... }, não um número — checa os dois campos)
{
  const resultado = calcularValorBrutoParaTeste('nps_carteira');
  checar('NPS — score', resultado?.score, -6.8, 0.3);
  checar('NPS — nota média', resultado?.notaMedia, 7.11, 0.05);
  checar('NPS — respondidas', resultado?.respondidas, 338, 0.5);
  checar('NPS — convites', resultado?.convites, 422, 0.5);
}

// 7. Taxa de cancelamento
checar('Taxa de cancelamento — 22/80', calcularValorBrutoParaTeste('taxa_cancelamento'), 27.5, 0.1);

// 8. Uso médio da plataforma
checar('Uso médio da plataforma', calcularValorBrutoParaTeste('uso_medio_plataforma'), 79.81, 0.1);

// 9. Reuniões realizadas
checar('Reuniões realizadas — 849/1104', calcularValorBrutoParaTeste('reunioes_realizadas'), 76.9, 0.1);

// 10. Chamados críticos
checar('Chamados críticos — total', calcularValorBrutoParaTeste('chamados_criticos'), 1016, 0.5);

// 11. Taxa de reabertura
checar('Taxa de reabertura', calcularValorBrutoParaTeste('taxa_reabertura'), 12.23, 0.1);

console.log(`\n${total - falhas}/${total} testes passaram.`);
if (falhas > 0) {
  process.exit(1);
}
