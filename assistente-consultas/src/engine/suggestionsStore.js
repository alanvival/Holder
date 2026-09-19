import { registrarIntentPersonalizada } from './intentRegistry.js';

// Estrutura de dados sugerida para "sugestões de usuários pendentes de
// análise" (item 2 dos entregáveis). Em produção isso é uma tabela/endpoint
// real; aqui é um store em memória com a mesma forma, pra trocar depois
// sem mexer na UI.
//
// SugestaoPendente = {
//   id: string,
//   perguntaOriginal: string,
//   criadaEm: string (ISO),
//   status: 'pendente' | 'aprovada' | 'rejeitada',
// }

let sugestoes = [];
let nextId = 1;

export function registrarSugestao(perguntaOriginal) {
  const sugestao = {
    id: `sug-${nextId++}`,
    perguntaOriginal,
    criadaEm: new Date().toISOString(),
    status: 'pendente',
  };
  sugestoes = [...sugestoes, sugestao];
  return sugestao;
}

export function listarSugestoesPendentes() {
  return sugestoes.filter((s) => s.status === 'pendente');
}

export function listarTodasSugestoes() {
  return sugestoes;
}

// Aprovar transforma a sugestão numa intenção cadastrada de verdade — usa a
// própria pergunta do usuário como primeiro exemplo de treino. O admin pode
// ajustar rótulo/resposta depois pela tela de administração.
export function aprovarSugestao(id, { respostaTexto } = {}) {
  const sugestao = sugestoes.find((s) => s.id === id);
  if (!sugestao || sugestao.status !== 'pendente') return null;

  const intent = registrarIntentPersonalizada({
    rotulo: sugestao.perguntaOriginal,
    exemplos: [sugestao.perguntaOriginal],
    respostaTexto: respostaTexto ?? 'Consulta cadastrada — resposta ainda não configurada pelo administrador.',
  });

  sugestoes = sugestoes.map((s) => (s.id === id ? { ...s, status: 'aprovada' } : s));
  return intent;
}

export function rejeitarSugestao(id) {
  sugestoes = sugestoes.map((s) => (s.id === id ? { ...s, status: 'rejeitada' } : s));
}
