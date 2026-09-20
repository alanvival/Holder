// Perguntas sugeridas na tela inicial do widget — curadas manualmente pra
// dar exemplos do que o Assistente de Consultas PREDITIVO sabe responder
// (tools listar_previsao_risco / detalhar_previsao_cliente, no fallback de
// IA — ver fallback_ia/previsao_risco.py). Diferente do catálogo
// determinístico (engine/intentRegistry.js), essas perguntas não têm um
// "intent" cadastrado — só existem via IA, por isso a lista é fixa aqui em
// vez de derivada do registro de intenções.
const PERGUNTAS_PREDITIVAS = [
  { id: 'sugestao-preditiva-1', texto: 'Quais empresas podem dar problema no futuro?' },
  { id: 'sugestao-preditiva-2', texto: 'Me dá um relatório preditivo dos clientes em risco crítico' },
  { id: 'sugestao-preditiva-3', texto: 'Qual o risco de cancelamento do cliente C071?' },
  { id: 'sugestao-preditiva-4', texto: 'Por que esse cliente tem esse risco de cancelar?' },
];

export function obterPerguntasSugeridas(limite = 4) {
  return PERGUNTAS_PREDITIVAS.slice(0, limite);
}
