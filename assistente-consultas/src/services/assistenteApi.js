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
import { textResponse, notFoundResponse } from '../engine/responseFormat.js';

// Latência artificial pra simular round-trip de rede em todas as chamadas —
// remove quando isso virar fetch de verdade (a latência real já existe).
const LATENCIA_MOCK_MS = 250;

function comLatencia(valor) {
  return new Promise((resolve) => setTimeout(() => resolve(valor), LATENCIA_MOCK_MS));
}

// Backend do fallback de IA (server.py) — só existe pra guardar a
// ANTHROPIC_API_KEY fora do bundle do front. Roda em processo/porta
// separada do Vite; ver server.py e .env.example na raiz do repo.
const FALLBACK_IA_URL = import.meta.env.VITE_FALLBACK_IA_URL ?? 'http://localhost:8000/api/fallback-ia';

// Um id por sessão de aba, só pro rate limit do backend saber agrupar
// chamadas da mesma sessão — não é autenticação nem identifica a pessoa.
const SESSAO_ID = `sessao-${Math.random().toString(36).slice(2)}-${Date.now()}`;

async function tentarFallbackIa(texto) {
  try {
    const controlador = new AbortController();
    const timeoutId = setTimeout(() => controlador.abort(), 9000);
    const resposta = await fetch(FALLBACK_IA_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pergunta: texto, sessaoId: SESSAO_ID }),
      signal: controlador.signal,
    });
    clearTimeout(timeoutId);
    if (!resposta.ok) return null;
    return await resposta.json();
  } catch {
    // Backend fora do ar, CORS não configurado, rede caiu, etc. — o
    // catálogo local já tratou como "não encontrado"; o front não deve
    // quebrar só porque o fallback opcional não respondeu.
    return null;
  }
}

/**
 * Envia a pergunta do usuário pro motor de interpretação. Primeiro tenta o
 * catálogo determinístico local (rápido, sem custo); só se ele não
 * reconhecer é que chama o fallback de IA no backend — nunca ao contrário.
 * PONTO DE INTEGRAÇÃO: quando o catálogo também virar uma API real, o
 * corpo daqui vira um único fetch pro endpoint de consultas, que decide
 * catálogo-vs-IA do lado do servidor.
 */
export async function consultarPergunta(texto, { empresaAtual } = {}) {
  const resultadoCatalogo = interpretarPergunta(texto);
  if (resultadoCatalogo.payload.kind !== 'not_found') {
    return comLatencia({ ...resultadoCatalogo, origem: 'catalogo' });
  }

  const respostaIa = await tentarFallbackIa(texto);
  if (respostaIa?.encontrado) {
    return { payload: textResponse(respostaIa.resposta), intentId: respostaIa.tool ?? null, origem: 'ia' };
  }

  // Fallback não achou tool, deu timeout, ou o backend nem está no ar —
  // sempre cai no mesmo "não encontrei" + sugestão que já existe no widget.
  return { payload: notFoundResponse(), intentId: null, origem: respostaIa ? 'ia' : 'catalogo' };
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
