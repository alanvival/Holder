import { intentRegistry, extrairEntidades } from './intentRegistry.js';
import { bestSimilarityAgainstPatterns } from './similarity.js';
import { notFoundResponse } from './responseFormat.js';
import { hojeFixo } from '../data/mockDatabase.js';

// Abaixo desse score, tratamos como "não encontrado" em vez de arriscar
// resolver a intenção errada — silêncio correto é melhor que resposta errada.
const SIMILARITY_THRESHOLD = 0.28;

/**
 * Interpreta a pergunta do usuário e devolve uma resposta estruturada.
 * Nunca gera texto livre: ou casa com uma intenção cadastrada e resolve
 * contra os dados reais, ou devolve notFoundResponse().
 */
export function interpretarPergunta(textoUsuario, { hoje = hojeFixo() } = {}) {
  const entidades = extrairEntidades(textoUsuario, hoje);

  let melhorIntencao = null;
  let melhorScore = 0;

  const textoLower = textoUsuario.toLowerCase();

  for (const intencao of intentRegistry) {
    if (!intencao.ativa) continue;
    // Intents podem declarar palavras que NUNCA devem casar com elas (ex:
    // "situacao_risco_cliente" não deve capturar perguntas sobre
    // probabilidade/predição, que são do modelo estatístico via IA, não
    // do diagnóstico heurístico deste intent) — checado antes da
    // similaridade, não depois, pra nem competir pelo melhor score.
    if (intencao.palavrasExcludentes?.some((palavra) => textoLower.includes(palavra))) continue;
    const score = bestSimilarityAgainstPatterns(textoUsuario, intencao.exemplos);
    if (score > melhorScore) {
      melhorScore = score;
      melhorIntencao = intencao;
    }
  }

  if (!melhorIntencao || melhorScore < SIMILARITY_THRESHOLD) {
    return { payload: notFoundResponse(), intentId: null, score: melhorScore };
  }

  if (!melhorIntencao.requerEntidade(entidades)) {
    return { payload: notFoundResponse(), intentId: melhorIntencao.id, score: melhorScore };
  }

  const payload = melhorIntencao.resolver(entidades, hoje);
  return { payload, intentId: melhorIntencao.id, score: melhorScore };
}
