// Sugestões de "continuar a conversa" mostradas depois de uma resposta da
// IA — texto curado por tool (nunca inventa dado, só sugere a PERGUNTA
// seguinte, quem responde de verdade continua sendo a mesma tool real).
// Curadoria manual (não gerada pela IA) porque é conteúdo de UI estável,
// não informação dos dados — gerar isso via IA a cada resposta custaria
// uma chamada extra sem necessidade.
const FOLLOW_UPS_POR_TOOL = {
  listar_previsao_risco: [
    'Detalhe o risco do primeiro cliente dessa lista',
    'Quais estão na faixa "Em risco"?',
    'O que mais influencia o risco desses clientes?',
  ],
  detalhar_previsao_cliente: [
    'Como esse risco evoluiu nos últimos meses?',
    'Quais outras empresas estão em risco parecido?',
    'O que a empresa deve fazer agora com esse cliente?',
  ],
  clientes_com_strikes: [
    'Me dá a probabilidade real desse cliente (relatório preditivo)',
    'Quais outros clientes têm alertas parecidos?',
  ],
  clientes_em_alerta: [
    'Qual desses tem a maior probabilidade real de cancelar?',
    'O que mais influencia o cancelamento na carteira?',
  ],
  analisar_fatores_churn: [
    'Quais empresas podem dar problema no futuro?',
    'Detalhe o risco de um cliente específico',
  ],
};

const FOLLOW_UPS_GENERICO_IA = [
  'Quais empresas podem dar problema no futuro?',
  'Me dá um relatório preditivo dos clientes em risco crítico',
];

export function obterFollowUps(intentId) {
  return FOLLOW_UPS_POR_TOOL[intentId] ?? FOLLOW_UPS_GENERICO_IA;
}
