// Camada de serviço — único ponto de contato entre a UI/hook e a lógica de
// dados. Hoje tudo aqui é síncrono/mock por baixo (engine/), mas a
// assinatura de cada função já é async e recebe { empresaAtual, usuarioAtual }
// como toda chamada real de backend vai precisar. Quando o backend existir,
// TROCAR SÓ O CORPO destas funções por fetch/await pro endpoint — nada fora
// deste arquivo deveria precisar mudar.

import { interpretarPergunta } from '../engine/matchIntent.js';
import { listarIntents, registrarIntentPersonalizada, desativarIntent } from '../engine/intentRegistry.js';
import {
  registrarSugestao,
  listarTodasSugestoes,
  aprovarSugestao,
  rejeitarSugestao,
} from '../engine/suggestionsStore.js';

// Latência artificial pra simular round-trip de rede em todas as chamadas —
// remove quando isso virar fetch de verdade (a latência real já existe).
const LATENCIA_MOCK_MS = 250;

function comLatencia(valor) {
  return new Promise((resolve) => setTimeout(() => resolve(valor), LATENCIA_MOCK_MS));
}

/**
 * Envia a pergunta do usuário pro motor de interpretação.
 * PONTO DE INTEGRAÇÃO: em produção isso vira
 *   POST /api/{empresaId}/assistente/consultas  { texto, usuarioId }
 * mantendo a mesma assinatura (texto, tenant) => Promise<{ payload, intentId, score }>.
 */
export async function consultarPergunta(texto, { empresaAtual } = {}) {
  const resultado = interpretarPergunta(texto);
  return comLatencia(resultado);
}

/**
 * PONTO DE INTEGRAÇÃO: GET /api/{empresaId}/assistente/intencoes
 */
export async function listarPerguntasCadastradas({ empresaAtual } = {}) {
  return comLatencia(listarIntents());
}

/**
 * PONTO DE INTEGRAÇÃO: POST /api/{empresaId}/assistente/intencoes
 */
export async function cadastrarPergunta({ rotulo, exemplos, respostaTexto }, { empresaAtual, usuarioAtual } = {}) {
  const intent = registrarIntentPersonalizada({ rotulo, exemplos, respostaTexto });
  return comLatencia(intent);
}

/**
 * PONTO DE INTEGRAÇÃO: PATCH /api/{empresaId}/assistente/intencoes/{id} { ativa: false }
 */
export async function desativarPergunta(id, { empresaAtual } = {}) {
  desativarIntent(id);
  return comLatencia({ id, ativa: false });
}

/**
 * PONTO DE INTEGRAÇÃO: POST /api/{empresaId}/assistente/sugestoes
 */
export async function registrarSugestaoUsuario(perguntaOriginal, { empresaAtual, usuarioAtual } = {}) {
  const sugestao = registrarSugestao(perguntaOriginal);
  return comLatencia(sugestao);
}

/**
 * PONTO DE INTEGRAÇÃO: GET /api/{empresaId}/assistente/sugestoes
 */
export async function listarSugestoes({ empresaAtual } = {}) {
  return comLatencia(listarTodasSugestoes());
}

/**
 * PONTO DE INTEGRAÇÃO: POST /api/{empresaId}/assistente/sugestoes/{id}/aprovar
 */
export async function aprovarSugestaoUsuario(id, opcoes, { empresaAtual } = {}) {
  const intent = aprovarSugestao(id, opcoes);
  return comLatencia(intent);
}

/**
 * PONTO DE INTEGRAÇÃO: POST /api/{empresaId}/assistente/sugestoes/{id}/rejeitar
 */
export async function rejeitarSugestaoUsuario(id, { empresaAtual } = {}) {
  rejeitarSugestao(id);
  return comLatencia({ id, status: 'rejeitada' });
}
