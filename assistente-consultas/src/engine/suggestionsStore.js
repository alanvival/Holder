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
