// Camada de serviço — único ponto de contato entre a UI/hook e a lógica de
// dados. Perguntas cadastradas pelo admin e sugestões dos usuários agora
// persistem de verdade no backend (server.py + fallback_ia/armazenamento.py,
// SQLite) em vez de só em memória no navegador. O catálogo "de sistema"
// (intenções com resolver em código — consulta de registro, métricas)
// continua definido em engine/intentRegistry.js e engine/metricas.js; só o
// que o admin cria em runtime é que precisa de persistência real.
//
// Sempre que o backend não responde (fora do ar, CORS, rede), cada função
// cai de volta pro motor local em memória — o widget nunca quebra por
// causa disso, só perde a persistência entre sessões até o backend voltar.

import { interpretarPergunta } from '../engine/matchIntent.js';
import { tentarRiscoDireto } from '../engine/riscoDireto.js';
import { listarIntents, registrarIntentPersonalizada, desativarIntent } from '../engine/intentRegistry.js';
import {
  registrarSugestao,
  listarTodasSugestoes,
  aprovarSugestao,
  rejeitarSugestao,
} from '../engine/suggestionsStore.js';
import { textResponse, tableResponse, notFoundResponse, timeoutResponse } from '../engine/responseFormat.js';

// Lançado quando o USUÁRIO cancela a pergunta em andamento (botão
// "Cancelar" no indicador de digitando — ver TypingIndicator.jsx) —
// diferente de um timeout de verdade: aqui não faz sentido nenhuma
// mensagem de resposta, só voltar pro estado ocioso sem nada na tela.
export class PerguntaCanceladaError extends Error {}

// Tools cujo resultado é naturalmente tabular — quando o backend devolve um
// bloco `tabela` (colunas + linhas), a UI renderiza como tabela em vez de
// só texto corrido, mesmo a IA continuando a escrever o texto de contexto.
const TOOLS_COM_TABELA = new Set(['listar_clientes', 'comparar_clientes', 'evolucao_temporal', 'consultar_metrica']);

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000/api';

// Um id por sessão de aba, só pro rate limit do fallback de IA agrupar
// chamadas da mesma sessão — não é autenticação nem identifica a pessoa.
const SESSAO_ID = `sessao-${Math.random().toString(36).slice(2)}-${Date.now()}`;

// `sinalExterno` é opcional — quando presente (só usado pelo fallback de
// IA, a única chamada longa o bastante pra alguém querer cancelar), um
// abort dele derruba a mesma requisição que o timeout interno derrubaria,
// e a função sabe distinguir os dois casos (usuário cancelou vs. só
// demorou demais) pra quem chamou decidir o que mostrar.
async function chamarBackend(caminho, opcoes, timeoutMs = 8000, sinalExterno) {
  const controlador = new AbortController();
  const timeoutId = setTimeout(() => controlador.abort(), timeoutMs);
  const propagarCancelamento = () => controlador.abort();
  sinalExterno?.addEventListener('abort', propagarCancelamento);
  try {
    const resposta = await fetch(`${BACKEND_URL}${caminho}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controlador.signal,
      ...opcoes,
    });
    const corpo = await resposta.json().catch(() => null);
    return { ok: resposta.ok, status: resposta.status, dados: corpo };
  } catch {
    if (sinalExterno?.aborted) throw new PerguntaCanceladaError();
    // Backend fora do ar, CORS não configurado, rede caiu, ou o timeout
    // interno (timeoutMs) estourou — quem chamou trata como "sem resposta".
    return null;
  } finally {
    clearTimeout(timeoutId);
    sinalExterno?.removeEventListener('abort', propagarCancelamento);
  }
}

// O fallback de IA pode legitimamente demorar mais que uma chamada normal
// de CRUD: o backend tem seu próprio guardrail de até TIMEOUT_SEGUNDOS (20s,
// ver fallback_ia/guardrails.py) POR chamada ao modelo, e perguntas que
// encadeiam tools (ex: comparação indireta) fazem várias chamadas antes de
// responder. Esse teto chegou a subir até 100s enquanto o backend usava
// gpt-oss-120b (reasoning model — respostas de 40 a 223s ao vivo pra
// perguntas de 1 tool só). Trocado pra gpt-oss-20b (mesma família, ~6x
// menor) depois de confirmar respostas de ~18s pro mesmo caso — 45s ainda
// dá margem pra 2 chamadas mais lentas sem deixar o usuário esperando
// indefinidamente se o backend realmente travar.
const TIMEOUT_FALLBACK_IA_MS = 45000;

async function tentarFallbackIa(texto, historico, sinal) {
  const resultado = await chamarBackend('/fallback-ia', {
    method: 'POST',
    body: JSON.stringify({ pergunta: texto, sessaoId: SESSAO_ID, historico }),
  }, TIMEOUT_FALLBACK_IA_MS, sinal);
  return resultado?.ok ? resultado.dados : null;
}

// Log fire-and-forget: nunca atrasa nem quebra a resposta ao usuário por
// causa de falha no registro (histórico é conveniência de auditoria, não
// parte crítica do fluxo). Cobre catálogo E IA no mesmo lugar, pra nada
// ficar de fora do painel de Administração.
function registrarHistorico({ pergunta, resposta, origem, tool, sucesso }) {
  chamarBackend('/historico', {
    method: 'POST',
    body: JSON.stringify({ pergunta, resposta, origem, tool, sucesso }),
  }).catch(() => {});
}

/**
 * Envia a pergunta do usuário pro motor de interpretação, em 3 níveis, do
 * mais rápido/barato pro mais lento: catálogo determinístico local (sem
 * rede) -> atalho de risco (rota fixa no backend, sem Groq) -> fallback de
 * IA (Groq, com tool use — só quando os dois primeiros não reconhecem).
 */
export async function consultarPergunta(texto, { historico, sinal } = {}) {
  const resultadoCatalogo = interpretarPergunta(texto);
  if (resultadoCatalogo.payload.kind !== 'not_found') {
    registrarHistorico({ pergunta: texto, resposta: resultadoCatalogo.payload.text ?? null, origem: 'catalogo', tool: resultadoCatalogo.intentId ?? null, sucesso: true });
    return { ...resultadoCatalogo, origem: 'catalogo' };
  }

  const risco = await tentarRiscoDireto(texto);
  if (risco) {
    const payload = tableResponse(risco.texto, risco.colunas, risco.linhas, risco.contexto);
    registrarHistorico({ pergunta: texto, resposta: risco.texto, origem: 'catalogo', tool: 'risco_direto', sucesso: true });
    return { payload, intentId: 'risco_direto', origem: 'catalogo' };
  }

  const respostaIa = await tentarFallbackIa(texto, historico, sinal);
  if (respostaIa?.encontrado) {
    const tabela = respostaIa.resultado?.tabela;
    const payload = TOOLS_COM_TABELA.has(respostaIa.tool) && tabela?.colunas?.length
      ? tableResponse(respostaIa.resposta, tabela.colunas, tabela.linhas)
      : textResponse(respostaIa.resposta);
    registrarHistorico({ pergunta: texto, resposta: respostaIa.resposta, origem: 'ia', tool: respostaIa.tool ?? null, sucesso: true });
    return { payload, intentId: respostaIa.tool ?? null, origem: 'ia' };
  }

  // `respostaIa` é null em dois casos BEM diferentes, que agora viram
  // mensagens diferentes: (a) a chamada nem completou — timeout do front,
  // rede caiu, backend fora do ar — não é "não encontrei", é "não deu
  // tempo/não rolou", com botão de tentar de novo; (b) a chamada completou
  // e a própria IA decidiu que nenhuma tool respondia a pergunta —
  // "não encontrei" de verdade, com o prompt de sugestão pro catálogo.
  if (!respostaIa) {
    registrarHistorico({ pergunta: texto, resposta: null, origem: 'ia', tool: null, sucesso: false });
    return { payload: timeoutResponse(), intentId: null, origem: 'ia' };
  }

  registrarHistorico({ pergunta: texto, resposta: null, origem: 'ia', tool: null, sucesso: false });
  return { payload: notFoundResponse(), intentId: null, origem: 'ia' };
}

// Injeta uma pergunta vinda do backend no motor local de matching, usando o
// MESMO id do backend — assim um refetch (ex: reabrir a tela de admin) não
// duplica a intenção já registrada nesta sessão.
function hidratarLocal(pergunta) {
  if (!pergunta.ativa) return; // inativa não deve casar com novas perguntas
  registrarIntentPersonalizada({
    id: pergunta.id,
    rotulo: pergunta.rotulo,
    exemplos: pergunta.exemplos,
    respostaTexto: pergunta.respostaTexto,
    ativa: pergunta.ativa,
    criadaEm: pergunta.criadaEm,
  });
}

/**
 * Busca as perguntas cadastradas pelo admin no backend e sincroniza no
 * motor local de matching, pra ficarem respondíveis nesta sessão mesmo que
 * o usuário nunca abra a tela de Administração. Chamado uma vez ao montar
 * o widget (ver useAssistant.js) — idempotente, seguro de repetir.
 */
export async function hidratarCatalogoAdmin() {
  const resultado = await chamarBackend('/perguntas');
  if (!resultado?.ok) return;
  resultado.dados.forEach(hidratarLocal);
}

export async function listarPerguntasCadastradas() {
  await hidratarCatalogoAdmin();
  return listarIntents();
}

export async function cadastrarPergunta({ rotulo, exemplos, respostaTexto }) {
  const resultado = await chamarBackend('/perguntas', {
    method: 'POST',
    body: JSON.stringify({ rotulo, exemplos, respostaTexto }),
  });
  if (resultado?.ok) {
    hidratarLocal(resultado.dados);
    return resultado.dados;
  }
  // Backend indisponível — cadastra só localmente (não sobrevive a um
  // refresh, mas mantém o widget usável offline/em demo).
  return registrarIntentPersonalizada({ rotulo, exemplos, respostaTexto });
}

export async function desativarPergunta(id) {
  await chamarBackend(`/perguntas/${id}`, { method: 'PATCH', body: JSON.stringify({ ativa: false }) });
  desativarIntent(id); // efeito local sempre, backend ou não
  return { id, ativa: false };
}

export async function registrarSugestaoUsuario(perguntaOriginal) {
  const resultado = await chamarBackend('/sugestoes', {
    method: 'POST',
    body: JSON.stringify({ perguntaOriginal }),
  });
  if (resultado?.ok) return resultado.dados;
  return registrarSugestao(perguntaOriginal);
}

export async function listarSugestoes() {
  const resultado = await chamarBackend('/sugestoes');
  if (resultado?.ok) return resultado.dados;
  return listarTodasSugestoes();
}

/**
 * Pede pra IA sugerir um texto de resposta pra essa sugestão (mesmo motor
 * de tool use do fallback — nunca inventa número, só formata em cima do
 * dado real). Usado ao expandir "Aprovar" no painel de admin, pra
 * pré-preencher o campo em vez de deixar em branco pro admin digitar do
 * zero. Retorna null se a IA não achou nada (ou o backend/chave não estão
 * configurados) — a tela trata isso deixando o campo em branco, como hoje.
 */
export async function sugerirRespostaIa(sugestaoId) {
  const resultado = await chamarBackend(`/sugestoes/${sugestaoId}/sugerir-resposta`, { method: 'POST' });
  if (resultado?.ok && resultado.dados?.encontrado) return resultado.dados.resposta;
  return null;
}

export async function aprovarSugestaoUsuario(id, opcoes) {
  const resultado = await chamarBackend(`/sugestoes/${id}/aprovar`, {
    method: 'POST',
    body: JSON.stringify({ respostaTexto: opcoes?.respostaTexto }),
  });
  if (resultado?.ok) {
    hidratarLocal(resultado.dados);
    return resultado.dados;
  }
  // Sugestão não existe no backend (ex: foi criada localmente enquanto o
  // backend estava fora do ar) — tenta resolver no store local.
  return aprovarSugestao(id, opcoes);
}

export async function rejeitarSugestaoUsuario(id) {
  const resultado = await chamarBackend(`/sugestoes/${id}/rejeitar`, { method: 'POST' });
  if (resultado?.ok) return resultado.dados;
  rejeitarSugestao(id);
  return { id, status: 'rejeitada' };
}

/**
 * Histórico de conversas (catálogo + IA) já respondidas — pro painel de
 * Administração revisar o que os usuários vêm perguntando. Sem fallback
 * local (diferente do resto deste arquivo): é só leitura de auditoria, não
 * faz sentido reconstruir isso em memória se o backend estiver fora do ar.
 */
export async function listarHistorico(limite = 100) {
  const resultado = await chamarBackend(`/historico?limite=${limite}`);
  return resultado?.ok ? resultado.dados : [];
}
