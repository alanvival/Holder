import { intentRegistry } from '../engine/intentRegistry.js';

// Perguntas sugeridas vêm da base de intenções cadastradas (não hardcoded
// na UI) — conforme exigido na especificação. Mistura intenções do início
// e do fim do registro pra sempre mostrar variedade (hoje: exemplos do
// domínio genérico + da carteira real do desafio INOVAAPPS).
export function obterPerguntasSugeridas(limite = 4) {
  const ativas = intentRegistry.filter((intencao) => intencao.ativa);
  const metade = Math.ceil(limite / 2);
  const selecionadas = [...ativas.slice(0, metade), ...ativas.slice(-metade)];
  const semDuplicadas = [...new Map(selecionadas.map((i) => [i.id, i])).values()];
  return semDuplicadas.slice(0, limite).map((intencao) => ({ id: intencao.id, texto: intencao.exemplos[0] }));
}
