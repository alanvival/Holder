import { intentRegistry } from '../engine/intentRegistry.js';

// Perguntas sugeridas vêm da base de intenções cadastradas (não hardcoded
// na UI) — conforme exigido na especificação. Pega o primeiro exemplo de
// cada intenção ativa como chip de sugestão.
export function obterPerguntasSugeridas(limite = 4) {
  return intentRegistry
    .filter((intencao) => intencao.ativa)
    .slice(0, limite)
    .map((intencao) => ({ id: intencao.id, texto: intencao.exemplos[0] }));
}
