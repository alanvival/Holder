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
import { listarIntents, registrarIntentPersonalizada, desativarIntent } from '../engine/intentRegistry.js';
import {
  registrarSugestao,
  listarTodasSugestoes,
  aprovarSugestao,
  rejeitarSugestao,
} from '../engine/suggestionsStore.js';
import { textResponse, tableResponse, notFoundResponse } from '../engine/responseFormat.js';

// Tools cujo resultado é naturalmente tabular — quando o backend devolve um
// bloco `tabela` (colunas + linhas), a UI renderiza como tabela em vez de
// só texto corrido, mesmo a IA continuando a escrever o texto de contexto.
const TOOLS_COM_TABELA = new Set(['listar_clientes', 'comparar_clientes', 'evolucao_temporal']);

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000/api';

// Um id por sessão de aba, só pro rate limit do fallback de IA agrupar
// chamadas da mesma sessão — não é autenticação nem identifica a pessoa.
const SESSAO_ID = `sessao-${Math.random().toString(36).slice(2)}-${Date.now()}`;

async function chamarBackend(caminho, opcoes) {
  try {
    const controlador = new AbortController();
    const timeoutId = setTimeout(() => controlador.abort(), 8000);
    const resposta = await fetch(`${BACKEND_URL}${caminho}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controlador.signal,
      ...opcoes,
    });
    clearTimeout(timeoutId);
    const corpo = await resposta.json().catch(() => null);
    return { ok: resposta.ok, status: resposta.status, dados: corpo };
  } catch {
    // Backend fora do ar, CORS não configurado, rede caiu, etc.
    return null;
  }
}

async function tentarFallbackIa(texto) {
  const resultado = await chamarBackend('/fallback-ia', {
    method: 'POST',
    body: JSON.stringify({ pergunta: texto, sessaoId: SESSAO_ID }),
  });
  return resultado?.ok ? resultado.dados : null;
}

/**
 * Envia a pergunta do usuário pro motor de interpretação. Primeiro tenta o
 * catálogo determinístico local (rápido, sem custo); só se ele não
 * reconhecer é que chama o fallback de IA no backend — nunca ao contrário.
 */
export async function consultarPergunta(texto) {
  const resultadoCatalogo = interpretarPergunta(texto);
  if (resultadoCatalogo.payload.kind !== 'not_found') {
    return { ...resultadoCatalogo, origem: 'catalogo' };
  }

  const respostaIa = await tentarFallbackIa(texto);
  if (respostaIa?.encontrado) {
    const tabela = respostaIa.resultado?.tabela;
    const payload = TOOLS_COM_TABELA.has(respostaIa.tool) && tabela?.colunas?.length
      ? tableResponse(respostaIa.resposta, tabela.colunas, tabela.linhas)
      : textResponse(respostaIa.resposta);
    return { payload, intentId: respostaIa.tool ?? null, origem: 'ia' };
  }

  // Fallback não achou tool, deu timeout, ou o backend nem está no ar —
  // sempre cai no mesmo "não encontrei" + sugestão que já existe no widget.
  return { payload: notFoundResponse(), intentId: null, origem: respostaIa ? 'ia' : 'catalogo' };
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
