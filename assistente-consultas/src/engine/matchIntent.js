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

  for (const intencao of intentRegistry) {
    if (!intencao.ativa) continue;
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
